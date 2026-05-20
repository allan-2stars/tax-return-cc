import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

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
