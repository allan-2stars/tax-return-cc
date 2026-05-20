from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
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


# ── GET /readiness ────────────────────────────────────────────────────────────

@router.get("/readiness")
async def get_readiness(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
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
            })
        else:
            available_now.append({
                "requirement_id": item.requirement_id,
                "display": item.display,
                "weight": item.weight,
                "skill_id": item.skill_id,
            })

    return {
        "data": {
            "available_now": available_now,
            "available_after_fy": available_after_fy,
        }
    }
