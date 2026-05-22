from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.db.models import ReadinessScore, Workspace
from app.errors import error_response

router = APIRouter()


class UpdateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


def _ws_dict(ws: Workspace, readiness_pct: float) -> dict:
    return {
        "id": ws.id,
        "name": ws.name,
        "financial_year": ws.financial_year,
        "status": ws.status,
        "readiness_pct": readiness_pct,
    }


@router.get("/workspaces")
async def list_workspaces(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(select(Workspace))
    workspaces = rows.scalars().all()

    items = []
    for ws in workspaces:
        score_row = await db.execute(
            select(ReadinessScore)
            .where(ReadinessScore.workspace_id == ws.id)
            .order_by(ReadinessScore.calculated_at.desc())
            .limit(1)
        )
        score = score_row.scalar_one_or_none()
        items.append(_ws_dict(ws, score.percentage if score else 0.0))

    return {"data": {"items": items}, "status": "ok"}


@router.patch("/workspaces/{target_id}")
async def update_workspace(
    target_id: str,
    body: UpdateWorkspaceRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if target_id != workspace_id:
        raise HTTPException(
            status_code=403,
            detail=error_response("forbidden", "Cannot modify another workspace.", retryable=False),
        )
    ws = await db.get(Workspace, target_id)
    if not ws:
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "Workspace not found.", retryable=False),
        )
    ws.name = body.name
    await db.commit()
    return {"data": _ws_dict(ws, 0.0), "status": "ok"}
