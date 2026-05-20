from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import events as events_repo
from app.repositories import profiles as profile_repo
from app.repositories import readiness as readiness_repo
from app.repositories import skills as skills_repo
from app.skills.base import EvidenceRequirement, MissingEvidence


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class SkillBreakdown:
    skill_id: str
    percentage: int
    achieved_weight: float
    total_weight: float


@dataclass
class ReviewSummaryItem:
    event_id: str
    category: str
    description: str
    status: str


@dataclass
class ReadinessScore:
    percentage: int
    breakdown: list[SkillBreakdown] = field(default_factory=list)
    missing_items: list[MissingEvidence] = field(default_factory=list)
    review_items: list[ReviewSummaryItem] = field(default_factory=list)
    agent_items: list[ReviewSummaryItem] = field(default_factory=list)
    is_stale: bool = False
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_fy_end_date(financial_year: str) -> date:
    # "2024-25" → date(2025, 6, 30)
    end_year = int(financial_year.split("-")[1]) + 2000
    return date(end_year, 6, 30)


def _eval_condition(condition: str, profile) -> bool:
    return bool(getattr(profile, condition, False))


def _evaluate_requirement(req: EvidenceRequirement, events: list) -> str:
    if not req.covers_category:
        return "missing"
    relevant = [e for e in events if e.category == req.covers_category]
    if any(e.status == "confirmed" for e in relevant):
        return "confirmed"
    if any(e.status in ("needs_user_review", "needs_agent_review", "high_risk")
           for e in relevant):
        return "needs_review"
    return "missing"


# ── ReadinessEngine ───────────────────────────────────────────────────────────

class ReadinessEngine:
    def __init__(self, registry=None) -> None:
        if registry is None:
            from app.skills.registry import get_registry
            registry = get_registry()
        self._registry = registry

    async def calculate(
        self, workspace_id: str, db: AsyncSession
    ) -> ReadinessScore:
        profile = await profile_repo.get_by_workspace(db, workspace_id)
        financial_year = profile.financial_year if profile else "2024-25"
        locked = await skills_repo.get_locked_skills(db, workspace_id)
        events = await events_repo.get_by_workspace(db, workspace_id)

        fy_end = _get_fy_end_date(financial_year)
        is_fy_active = datetime.now(timezone.utc).date() < fy_end

        total_weight: float = 0
        achieved_weight: float = 0
        breakdowns: list[SkillBreakdown] = []
        all_missing: list[MissingEvidence] = []

        for lock in locked:
            skill = self._registry.get(lock["skill_id"])
            if skill is None:
                continue

            requirements = skill.get_evidence_requirements(profile)
            skill_total: float = 0
            skill_achieved: float = 0
            skill_missing: list[MissingEvidence] = []

            for req in requirements:
                if is_fy_active and req.available_after_fy:
                    continue
                if req.condition and not _eval_condition(req.condition, profile):
                    continue

                skill_total += req.weight
                status = _evaluate_requirement(req, events)

                if status == "confirmed":
                    skill_achieved += req.weight
                elif status == "needs_review":
                    skill_achieved += req.weight * 0.5
                else:
                    skill_missing.append(
                        MissingEvidence(
                            requirement_id=req.id,
                            display=req.display,
                            weight=req.weight,
                            skill_id=skill.skill_id,
                            available_after_fy=req.available_after_fy,
                        )
                    )

            total_weight += skill_total
            achieved_weight += skill_achieved
            all_missing.extend(skill_missing)

            skill_pct = (
                round(skill_achieved / skill_total * 100) if skill_total > 0 else 0
            )
            breakdowns.append(
                SkillBreakdown(
                    skill_id=skill.skill_id,
                    percentage=skill_pct,
                    achieved_weight=skill_achieved,
                    total_weight=skill_total,
                )
            )

        percentage = (
            round(achieved_weight / total_weight * 100) if total_weight > 0 else 0
        )

        review_items = [
            ReviewSummaryItem(
                event_id=e.id,
                category=e.category,
                description=e.description or "",
                status=e.status,
            )
            for e in events if e.status == "needs_user_review"
        ]
        agent_items = [
            ReviewSummaryItem(
                event_id=e.id,
                category=e.category,
                description=e.description or "",
                status=e.status,
            )
            for e in events if e.status == "needs_agent_review"
        ]

        score = ReadinessScore(
            percentage=percentage,
            breakdown=breakdowns,
            missing_items=all_missing,
            review_items=review_items,
            agent_items=agent_items,
            is_stale=False,
            calculated_at=datetime.now(timezone.utc),
        )

        # Persist
        await readiness_repo.save_score(
            db,
            workspace_id=workspace_id,
            financial_year=financial_year,
            percentage=percentage,
            breakdown=[
                {"skill_id": b.skill_id, "percentage": b.percentage,
                 "achieved_weight": b.achieved_weight, "total_weight": b.total_weight}
                for b in breakdowns
            ],
            missing_items=[
                {"requirement_id": m.requirement_id, "display": m.display,
                 "weight": m.weight, "skill_id": m.skill_id,
                 "available_after_fy": m.available_after_fy}
                for m in all_missing
            ],
            review_items=[
                {"event_id": r.event_id, "category": r.category,
                 "description": r.description, "status": r.status}
                for r in review_items
            ],
            agent_items=[
                {"event_id": a.event_id, "category": a.category,
                 "description": a.description, "status": a.status}
                for a in agent_items
            ],
        )
        return score

    async def recalculate(self, workspace_id: str) -> ReadinessScore:
        from app.db.base import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            return await self.calculate(workspace_id, db)

    async def get_missing_items(
        self, workspace_id: str, db: AsyncSession
    ) -> list[MissingEvidence]:
        score = await self.calculate(workspace_id, db)
        return score.missing_items

    async def mark_stale(self, workspace_id: str, db: AsyncSession) -> None:
        await readiness_repo.mark_stale(db, workspace_id)
