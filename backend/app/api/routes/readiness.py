from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.db.models import EvidenceObligation, TaxProfile, Workspace
from app.engines.readiness import ReadinessEngine, _get_fy_end_date
from app.repositories import readiness as readiness_repo
from app.repositories import profiles as profile_repo

router = APIRouter()

_engine = ReadinessEngine()


def _score_to_dict(score) -> dict:
    return {
        "percentage": score.percentage,
        "breakdown": [
            {
                "skill_id": b.skill_id,
                "percentage": b.percentage,
                "achieved_weight": b.achieved_weight,
                "total_weight": b.total_weight,
            }
            for b in score.breakdown
        ],
        "missing_items_count": len(score.missing_items),
        "review_items_count": len(score.review_items),
        "agent_items_count": len(score.agent_items),
        "is_stale": score.is_stale,
        "calculated_at": score.calculated_at.isoformat(),
    }


async def _resolve_financial_year(workspace_id: str, db: AsyncSession) -> str:
    profile = await db.scalar(select(TaxProfile).where(TaxProfile.workspace_id == workspace_id))
    if profile:
        return profile.financial_year
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    return workspace.financial_year if workspace else "2024-25"


async def _evidence_obligation_summary(workspace_id: str, db: AsyncSession) -> dict:
    financial_year = await _resolve_financial_year(workspace_id, db)
    obligations = (
        await db.execute(
            select(EvidenceObligation).where(
                EvidenceObligation.workspace_id == workspace_id,
                EvidenceObligation.financial_year == financial_year,
            )
        )
    ).scalars().all()

    required = [o for o in obligations if o.required_level == "required"]
    recommended = [o for o in obligations if o.required_level == "recommended"]

    def _count(items, status: str) -> int:
        return sum(1 for i in items if i.status == status)

    blocking = [
        {
            "id": o.id,
            "obligation_key": o.obligation_key,
            "label": o.label,
            "category": o.category,
            "required_level": o.required_level,
            "status": o.status,
            "reason": o.reason,
        }
        for o in required
        if o.status in {"missing", "partially_matched"}
    ]

    return {
        "total_obligations": len(obligations),
        "required_missing": _count(required, "missing"),
        "required_partially_matched": _count(required, "partially_matched"),
        "required_matched": _count(required, "matched"),
        "recommended_missing": _count(recommended, "missing"),
        "recommended_partially_matched": _count(recommended, "partially_matched"),
        "recommended_matched": _count(recommended, "matched"),
        "blocking_evidence_obligations": blocking,
    }


# ── GET /readiness ────────────────────────────────────────────────────────────

@router.get("/readiness")
async def get_readiness(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    evidence_summary = await _evidence_obligation_summary(workspace_id, db)
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    freshness = {
        "evidence_reconciled_at": (
            workspace.evidence_reconciled_at.isoformat()
            if workspace and workspace.evidence_reconciled_at
            else None
        ),
        "evidence_reconcile_status": workspace.evidence_reconcile_status if workspace else "idle",
        "evidence_reconcile_meta": workspace.evidence_reconcile_meta if workspace else None,
    }
    existing = await readiness_repo.get_score(db, workspace_id)
    if not existing:
        return {
            "data": {
                "percentage": 0,
                "breakdown": [],
                "missing_items_count": 0,
                "review_items_count": 0,
                "agent_items_count": 0,
                "is_stale": True,
                "calculated_at": None,
                "evidence_obligation_summary": evidence_summary,
                "evidence_freshness": freshness,
            }
        }
    return {
        "data": {
            "percentage": int(existing.percentage),
            "breakdown": existing.breakdown or [],
            "missing_items_count": len(existing.missing_items or []),
            "review_items_count": len(existing.review_items or []),
            "agent_items_count": len(existing.agent_items or []),
            "is_stale": existing.is_stale,
            "calculated_at": (
                existing.calculated_at.isoformat() if existing.calculated_at else None
            ),
            "evidence_obligation_summary": evidence_summary,
            "evidence_freshness": freshness,
        }
    }


# ── POST /readiness/recalculate ───────────────────────────────────────────────

@router.post("/readiness/recalculate")
async def recalculate_readiness(
    background_tasks: BackgroundTasks,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    await readiness_repo.mark_stale(db, workspace_id)
    background_tasks.add_task(_engine.recalculate, workspace_id)
    return {"data": {"status": "recalculating"}}


# ── GET /readiness/missing ────────────────────────────────────────────────────

@router.get("/readiness/missing")
async def get_missing_items(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await profile_repo.get_by_workspace(db, workspace_id)
    financial_year = profile.financial_year if profile else "2024-25"

    fy_end = _get_fy_end_date(financial_year)
    fy_ended = datetime.now(timezone.utc).date() >= fy_end

    missing = await _engine.get_missing_items(workspace_id, db)

    available_now = []
    available_after_fy = []
    for item in missing:
        if item.available_after_fy and not fy_ended:
            available_after_fy.append({
                "requirement_id": item.requirement_id,
                "display": item.display,
                "weight": item.weight,
                "skill_id": item.skill_id,
                "how_to_get": item.how_to_get,
            })
        else:
            available_now.append({
                "requirement_id": item.requirement_id,
                "display": item.display,
                "weight": item.weight,
                "skill_id": item.skill_id,
                "how_to_get": item.how_to_get,
            })

    return {
        "data": {
            "available_now": available_now,
            "available_after_fy": available_after_fy,
        }
    }
