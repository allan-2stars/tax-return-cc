import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import math
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, ReviewItem, TaxEvent
from app.repositories import events as events_repo
from app.repositories import interview as interview_repo
from app.repositories import review as review_repo


class UserAction(str, Enum):
    CONFIRMED = "confirmed"
    AMENDED   = "amended"
    FLAGGED   = "flagged"
    SKIPPED   = "skipped"


@dataclass
class ReviewQueue:
    agent_required: list[ReviewItem] = field(default_factory=list)
    high_risk:      list[ReviewItem] = field(default_factory=list)
    needs_review:   list[ReviewItem] = field(default_factory=list)
    confirmed:      list[ReviewItem] = field(default_factory=list)
    total:          int = 0
    pending:        int = 0


# ── helpers ───────────────────────────────────────────────────────────────────

def _sort_items(items: list[ReviewItem]) -> list[ReviewItem]:
    return sorted(items, key=lambda x: (
        x.questions_complete,       # False(0) = incomplete → first; True(1) = complete → later
        x.risk_level != "high",     # False(0) = high → first; True(1) = not high → later
        -(x.amount or 0),           # higher amount → more negative → first
        -x.created_at.timestamp(),  # newer → more negative → first
    ))


class _SkillRef:
    """Minimal ref carrying skill_id for check_activation_delta."""
    def __init__(self, skill_id: str) -> None:
        self.skill_id = skill_id


async def _write_audit(
    db: AsyncSession,
    workspace_id: str,
    action: str,
    tax_event_id: str | None = None,
    actor: str = "user",
    note: str | None = None,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    log = AuditLog(
        workspace_id=workspace_id,
        tax_event_id=tax_event_id,
        action=action,
        actor=actor,
        note=note,
        field=field,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(log)
    await db.commit()


# ── ReviewEngine ──────────────────────────────────────────────────────────────

class ReviewEngine:
    def __init__(
        self,
        registry=None,
        ai_adapter=None,
        readiness_engine=None,
    ) -> None:
        if registry is None:
            from app.skills.registry import get_registry
            registry = get_registry()
        self._registry = registry
        self._ai_adapter = ai_adapter
        if readiness_engine is None:
            from app.engines.readiness import ReadinessEngine
            readiness_engine = ReadinessEngine()
        self._readiness_engine = readiness_engine

    # ── create ────────────────────────────────────────────────────────────────

    async def create_review_item(
        self, event: TaxEvent, db: AsyncSession
    ) -> ReviewItem:
        item = await review_repo.create(db, event)

        # Attach inline questions from the owning skill
        skill = self._registry.get_owner(event.category)
        if skill:
            rqs = skill.get_review_questions(event)
            if rqs:
                item.inline_questions = [
                    {"id": rq.id, "ask": rq.ask, "type": rq.type, "options": rq.options}
                    for rq in rqs
                ]
                item.questions_complete = False
            else:
                item.inline_questions = []
                item.questions_complete = True
        else:
            item.inline_questions = []
            item.questions_complete = True

        await db.commit()
        await db.refresh(item)
        return item

    async def create_manual_event(
        self,
        workspace_id: str,
        financial_year: str,
        event_type: str,
        category: str,
        description: str,
        amount: float,
        date: str,
        frequency: str,
        note: str | None,
        periods: list[dict] | None,
        db: AsyncSession,
        metadata: dict | None = None,
        review_status: str | None = None,
        possible_duplicate: bool = False,
    ) -> list[TaxEvent]:
        """Create TaxEvent(s) + ReviewItem(s) for a manual entry."""
        import uuid as _uuid

        self._validate_manual_event(
            description=description,
            amount=amount,
            date_value=date,
            frequency=frequency,
            note=note,
            periods=periods,
            metadata=metadata,
        )

        _status = review_status or "needs_user_review"
        _risk = "high" if review_status == "needs_agent_review" else "low"

        group_id = str(_uuid.uuid4()) if frequency == "monthly" and periods else None

        if frequency == "monthly" and periods:
            total_amount = sum(p["months"] * p["amount_per_month"] for p in periods)
            n = len(periods)
            group_display = (
                f"{description} · {n} period{'s' if n != 1 else ''} · ${total_amount:.2f} total"
            )
            created_events = []
            for idx, period in enumerate(periods):
                period_amount = period["months"] * period["amount_per_month"]
                event = await events_repo.create_event(
                    db,
                    workspace_id=workspace_id,
                    financial_year=financial_year,
                    event_type=event_type,
                    category=category,
                    description=description,
                    amount=period_amount,
                    date=date,
                    source="manual_entry",
                    note=note,
                    group_id=group_id,
                    group_display=group_display,
                    is_recurring=True,
                    recurrence_index=idx,
                    event_metadata=metadata,
                    status=_status,
                    risk_level=_risk,
                    possible_duplicate=possible_duplicate,
                )
                created_events.append(event)
        else:
            event = await events_repo.create_event(
                db,
                workspace_id=workspace_id,
                financial_year=financial_year,
                event_type=event_type,
                category=category,
                description=description,
                amount=amount,
                date=date,
                source="manual_entry",
                note=note,
                group_id=None,
                group_display=None,
                is_recurring=False,
                recurrence_index=None,
                event_metadata=metadata,
                status=_status,
                risk_level=_risk,
                possible_duplicate=possible_duplicate,
            )
            created_events = [event]

        for event in created_events:
            await self.create_review_item(event, db)

        asyncio.create_task(self._readiness_engine.recalculate(workspace_id))

        return created_events

    @staticmethod
    def _is_finite_number(value) -> bool:
        try:
            num = float(value)
        except (TypeError, ValueError):
            return False
        return math.isfinite(num)

    @staticmethod
    def _parse_iso_date(value: str, field: str) -> date:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
        except Exception as exc:
            raise ValueError(f"{field} must be a valid ISO date (YYYY-MM-DD).") from exc
        if parsed > datetime.now(timezone.utc).date():
            raise ValueError(f"{field} cannot be in the future.")
        return parsed

    def _require_max_text(self, value: str | None, max_len: int, field: str) -> None:
        if value is not None and len(value) > max_len:
            raise ValueError(f"{field} must be at most {max_len} characters.")

    def _require_finite(self, value, field: str) -> float:
        if not self._is_finite_number(value):
            raise ValueError(f"{field} must be a finite number.")
        return float(value)

    def _require_non_negative(self, value, field: str) -> float:
        num = self._require_finite(value, field)
        if num < 0:
            raise ValueError(f"{field} must be greater than or equal to 0.")
        if num > 999_999_999:
            raise ValueError(f"{field} must be less than or equal to 999999999.")
        return num

    def _require_positive(self, value, field: str) -> float:
        num = self._require_finite(value, field)
        if num <= 0:
            raise ValueError(f"{field} must be greater than 0.")
        if num > 999_999_999:
            raise ValueError(f"{field} must be less than or equal to 999999999.")
        return num

    def _require_short_text_field(self, metadata: dict | None, field: str, required: bool = False) -> str:
        value = (metadata or {}).get(field)
        if required and (value is None or str(value).strip() == ""):
            raise ValueError(f"{field} is required.")
        if value is None:
            return ""
        text = str(value).strip()
        if len(text) > 100:
            raise ValueError(f"{field} must be at most 100 characters.")
        return text

    def _validate_manual_event(
        self,
        description: str,
        amount: float,
        date_value: str,
        frequency: str,
        note: str | None,
        periods: list[dict] | None,
        metadata: dict | None,
    ) -> None:
        self._require_max_text(description, 500, "Description")
        self._require_max_text(note, 5000, "Note")
        self._parse_iso_date(date_value, "date")

        if frequency == "monthly" and periods:
            for idx, period in enumerate(periods):
                self._require_positive(period.get("months"), f"periods[{idx}].months")
                self._require_positive(period.get("amount_per_month"), f"periods[{idx}].amount_per_month")
        else:
            self._require_positive(amount, "amount")

        meta = metadata or {}
        for key, raw_value in meta.items():
            if isinstance(raw_value, str) and len(raw_value) > 100:
                raise ValueError(f"{key} must be at most 100 characters.")
            if isinstance(raw_value, (int, float)):
                self._require_non_negative(raw_value, key)

        investment_sub_type = meta.get("investment_sub_type")
        if investment_sub_type == "shares":
            self._validate_shares_metadata(meta)
        elif investment_sub_type == "crypto":
            self._validate_crypto_metadata(meta)
        elif investment_sub_type == "bank_interest":
            self._validate_bank_interest_metadata(meta)
        elif investment_sub_type == "foreign_income":
            self._validate_foreign_income_metadata(meta)

    def _validate_shares_metadata(self, metadata: dict) -> None:
        tx_type = self._require_short_text_field(metadata, "transaction_type", required=True).lower()

        stock_code = self._require_short_text_field(metadata, "stock_code", required=True).upper()
        if not re.fullmatch(r"[A-Z0-9]{1,10}", stock_code):
            raise ValueError("Stock code must match ^[A-Z0-9]{1,10}$.")

        if tx_type in {"buy", "sell"}:
            self._require_positive(metadata.get("units"), "units")
            self._require_non_negative(metadata.get("brokerage_fee", 0), "brokerage_fee")
            purchase_date = self._parse_iso_date(str(metadata.get("purchase_date", "")), "purchase_date")
            if tx_type == "buy":
                self._require_positive(metadata.get("price_per_unit"), "price_per_unit")
            if tx_type == "sell":
                self._require_positive(metadata.get("sale_price_per_unit"), "sale_price_per_unit")
                self._require_positive(metadata.get("purchase_price_per_unit"), "purchase_price_per_unit")
                sale_date = self._parse_iso_date(str(metadata.get("sale_date", "")), "sale_date")
                if purchase_date > sale_date:
                    raise ValueError("purchase_date must be on or before sale_date.")

        if tx_type == "dividend":
            self._require_positive(metadata.get("dividend_amount"), "dividend_amount")
            self._require_non_negative(metadata.get("franking_credits", 0), "franking_credits")
            self._parse_iso_date(str(metadata.get("payment_date", "")), "payment_date")

    def _validate_crypto_metadata(self, metadata: dict) -> None:
        tx_type = self._require_short_text_field(metadata, "transaction_type", required=True).lower()
        coin = self._require_short_text_field(metadata, "coin", required=True).upper()
        if not re.fullmatch(r"[A-Z0-9]{1,10}", coin):
            raise ValueError("Coin/token must match ^[A-Z0-9]{1,10}$.")

        if tx_type in {"buy", "sell"}:
            self._require_positive(metadata.get("amount_units"), "amount_units")
            self._require_non_negative(metadata.get("transaction_fee", 0), "transaction_fee")
            purchase_date = self._parse_iso_date(str(metadata.get("purchase_date", "")), "purchase_date")
            if tx_type == "buy":
                self._require_positive(metadata.get("purchase_price"), "purchase_price")
            if tx_type == "sell":
                self._require_positive(metadata.get("sale_price"), "sale_price")
                self._require_positive(metadata.get("purchase_price"), "purchase_price")
                sale_date = self._parse_iso_date(str(metadata.get("sale_date", "")), "sale_date")
                if purchase_date > sale_date:
                    raise ValueError("purchase_date must be on or before sale_date.")

        if tx_type == "staking":
            self._require_positive(metadata.get("income_amount"), "income_amount")
            self._parse_iso_date(str(metadata.get("income_date", "")), "income_date")

    def _validate_bank_interest_metadata(self, metadata: dict) -> None:
        self._require_short_text_field(metadata, "bank_name", required=True)
        self._require_short_text_field(metadata, "account_type", required=True)
        self._require_positive(metadata.get("interest_amount"), "interest_amount")

    def _validate_foreign_income_metadata(self, metadata: dict) -> None:
        self._require_short_text_field(metadata, "country", required=True)
        currency = self._require_short_text_field(metadata, "currency", required=True).upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("Currency code must match ^[A-Z]{3}$.")
        self._require_positive(metadata.get("foreign_amount"), "foreign_amount")
        self._require_positive(metadata.get("exchange_rate"), "exchange_rate")
        if metadata.get("foreign_tax_paid") is not None:
            self._require_non_negative(metadata.get("foreign_tax_paid"), "foreign_tax_paid")
        self._parse_iso_date(str(metadata.get("income_date", "")), "income_date")

    # ── queue ─────────────────────────────────────────────────────────────────

    async def get_queue(
        self, workspace_id: str, db: AsyncSession
    ) -> ReviewQueue:
        items = await review_repo.get_queue(db, workspace_id)
        sorted_items = _sort_items(items)

        agent_required = [i for i in sorted_items if i.status == "needs_agent_review"]
        high_risk = [
            i for i in sorted_items
            if (i.risk_level == "high" or not i.questions_complete)
            and i.status not in ("needs_agent_review", "confirmed")
        ]
        needs_review = [
            i for i in sorted_items
            if i.status not in ("needs_agent_review", "confirmed")
            and i.risk_level != "high"
            and i.questions_complete
        ]
        confirmed = [i for i in sorted_items if i.status == "confirmed"]

        pending = len(agent_required) + len(high_risk) + len(needs_review)
        return ReviewQueue(
            agent_required=agent_required,
            high_risk=high_risk,
            needs_review=needs_review,
            confirmed=confirmed,
            total=len(items),
            pending=pending,
        )

    # ── get item ──────────────────────────────────────────────────────────────

    async def get_item(
        self, item_id: str, db: AsyncSession
    ) -> ReviewItem | None:
        return await review_repo.get_by_id(db, item_id)

    # ── process action ────────────────────────────────────────────────────────

    async def process_action(
        self,
        item_id: str,
        action: UserAction,
        payload: dict,
        db: AsyncSession,
    ) -> ReviewItem:
        item = await review_repo.get_by_id(db, item_id)
        if item is None:
            raise ValueError(f"ReviewItem {item_id!r} not found")

        event: TaxEvent | None = None
        if item.tax_event_id:
            event = await events_repo.get_by_id(db, item.tax_event_id)

        now = datetime.now(timezone.utc)
        created_at = (
            item.created_at.replace(tzinfo=timezone.utc)
            if item.created_at.tzinfo is None
            else item.created_at
        )

        if action == UserAction.CONFIRMED:
            item.status = "confirmed"
            item.user_action = "confirmed"
            item.reviewed_at = now
            # Duration measured from item creation, not from when user opened the card.
            # Over-counts time spent on other tasks. Acceptable for MVP analytics.
            item.review_duration_seconds = int((now - created_at).total_seconds())
            if event:
                event.status = "confirmed"
                event.review_status = "user_confirmed"
            await _write_audit(db, item.workspace_id, "confirmed", item.tax_event_id)

        elif action == UserAction.AMENDED:
            old_amount = item.amount
            new_amount = payload.get("amount")
            new_category = payload.get("category")
            note = payload.get("note")

            if new_amount is not None:
                item.amended_amount = float(new_amount)
            if new_category is not None:
                item.amended_category = new_category
            item.user_note = note
            item.status = "confirmed"
            item.user_action = "amended"
            item.reviewed_at = now
            item.review_duration_seconds = int((now - created_at).total_seconds())

            if event and new_amount is not None:
                history = list(event.correction_history or [])
                history.append({
                    "field": "amount",
                    "old_value": str(old_amount),
                    "new_value": str(new_amount),
                    "corrected_at": now.isoformat(),
                })
                event.correction_history = history
                event.status = "confirmed"
                event.review_status = "user_confirmed"

            await _write_audit(
                db, item.workspace_id, "amended", item.tax_event_id,
                field="amount",
                old_value=str(old_amount),
                new_value=str(new_amount),
                note=note,
            )

        elif action == UserAction.FLAGGED:
            item.status = "needs_agent_review"
            item.user_note = payload.get("note")
            if event:
                event.status = "needs_agent_review"
            await _write_audit(
                db, item.workspace_id, "flagged", item.tax_event_id,
                note=payload.get("note"),
            )

        elif action == UserAction.SKIPPED:
            item.skipped_until = now + timedelta(days=1)
            item.user_action = "skipped"
            await _write_audit(db, item.workspace_id, "skipped", item.tax_event_id)

        item = await review_repo.update(db, item)
        asyncio.create_task(self._readiness_engine.recalculate(item.workspace_id))
        return item

    # ── bulk action ───────────────────────────────────────────────────────────

    async def bulk_action(
        self,
        item_ids: list[str],
        action: UserAction,
        db: AsyncSession,
    ) -> list[ReviewItem]:
        if action != UserAction.CONFIRMED:
            raise ValueError(f"Bulk action only supports CONFIRMED, not {action.value!r}")
        results = []
        for item_id in item_ids:
            result = await self.process_action(item_id, action, {}, db)
            results.append(result)
        return results

    # ── submit inline answer ──────────────────────────────────────────────────

    async def submit_inline_answer(
        self,
        item_id: str,
        question_id: str,
        answer: str,
        event_id: str,
        db: AsyncSession,
    ) -> ReviewItem:
        item = await review_repo.get_by_id(db, item_id)
        if item is None:
            raise ValueError(f"ReviewItem {item_id!r} not found")

        session = await interview_repo.get_active_by_workspace(db, item.workspace_id)
        if session is None:
            raise ValueError("No active interview session for workspace")

        # Save answer to session (single source of truth)
        answers = dict(session.answers or {})
        answers[question_id] = answer
        session.answers = answers
        session = await interview_repo.save(db, session)

        # Check if all inline questions for this item are now answered
        inline_qs = item.inline_questions or []
        all_answered = all(q["id"] in answers for q in inline_qs)
        if all_answered:
            item.questions_complete = True

        # Check for new skill activation
        current_refs = [_SkillRef(sid) for sid in (session.activated_skills or [])]
        new_skills = self._registry.check_activation_delta(answers, current_refs)
        if new_skills:
            activated = list(session.activated_skills or [])
            activated.extend(s.skill_id for s in new_skills)
            session.activated_skills = activated
            from app.repositories import skills as skills_repo
            await skills_repo.lock_activated_skills(db, item.workspace_id, new_skills)
            session = await interview_repo.save(db, session)

        await _write_audit(
            db, item.workspace_id, "inline_answer", item.tax_event_id,
            note=f"{question_id}={answer}",
        )

        item = await review_repo.update(db, item)
        return item

    # ── ask claude ────────────────────────────────────────────────────────────

    async def ask_claude(
        self,
        item_id: str,
        question: str,
        profile,
        db: AsyncSession,
    ) -> str:
        from app.ai.prompts import _DISCLAIMER

        item = await review_repo.get_by_id(db, item_id)
        if item is None:
            raise ValueError(f"ReviewItem {item_id!r} not found")

        if self._ai_adapter is None:
            return _DISCLAIMER

        event_dict = {
            "description": item.title or "",
            "amount": item.amount,
            "date": item.date,
            "category": item.category,
            "ai_reasoning": item.ai_reasoning or "",
        }
        session_dict = {
            "employment_type": getattr(profile, "employment_type", "unknown"),
            "financial_year": getattr(profile, "financial_year", "2024-25"),
        }

        return await self._ai_adapter.ask(question, event_dict, session_dict)
