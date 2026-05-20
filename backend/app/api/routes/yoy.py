from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.engines.yoy import YoYEngine
from app.errors import error_response

router = APIRouter()

_engine = YoYEngine()


class ActionRequest(BaseModel):
    action: str


def _suggestion_dict(s) -> dict:
    return {
        "id": s.id,
        "workspace_id": s.workspace_id,
        "source_workspace_id": s.source_workspace_id,
        "financial_year": s.financial_year,
        "category": s.category,
        "description": s.description,
        "amount_last_year": s.amount_last_year,
        "frequency": s.frequency,
        "status": s.status,
        "actioned_at": s.actioned_at.isoformat() if s.actioned_at else None,
    }


# ── GET /yoy/suggestions ──────────────────────────────────────────────────────

@router.get("/yoy/suggestions")
async def get_suggestions(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    from app.repositories import yoy as yoy_repo
    suggestions = await yoy_repo.get_pending(db, workspace_id)
    return {"data": [_suggestion_dict(s) for s in suggestions]}


# ── POST /yoy/{id}/action ─────────────────────────────────────────────────────

@router.post("/yoy/{suggestion_id}/action")
async def take_action(
    suggestion_id: str,
    body: ActionRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    try:
        updated = await _engine.process_action(suggestion_id, body.action, db)
    except (ValueError, Exception) as e:
        raise HTTPException(
            status_code=422,
            detail=error_response("action_failed", str(e), retryable=False),
        )
    return {"data": _suggestion_dict(updated)}
