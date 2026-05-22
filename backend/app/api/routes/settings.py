import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.config import settings
from app.db.base import get_db
from app.db.models import AuditLog, Document, TaxEvent

router = APIRouter()

_DISCLAIMER = (
    "This tool helps organise your tax information and prepare a review package. "
    "It does not provide final tax advice and does not replace review by "
    "a registered tax agent."
)


@router.get("/settings/ai-usage")
async def get_ai_usage(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    today = datetime.now(timezone.utc)
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    rows = await db.execute(
        select(
            AuditLog.ai_operation,
            func.count(AuditLog.id).label("calls"),
            func.sum(AuditLog.cost_usd).label("total_cost"),
        )
        .where(
            AuditLog.workspace_id == workspace_id,
            AuditLog.ai_operation.isnot(None),
            AuditLog.created_at >= month_start,
        )
        .group_by(AuditLog.ai_operation)
    )
    items = [
        {
            "operation": r.ai_operation,
            "calls": r.calls,
            "cost_usd": round(r.total_cost or 0.0, 4),
        }
        for r in rows.all()
    ]
    total_cost = round(sum(i["cost_usd"] for i in items), 4)
    return {
        "data": {
            "ai_provider": settings.AI_PROVIDER,
            "items": items,
            "total_cost_usd": total_cost,
        },
        "status": "ok",
    }


@router.get("/settings/storage-usage")
async def get_storage_usage(workspace_id: str = Depends(require_auth)):
    def _dir_bytes(path: str) -> int:
        total = 0
        try:
            for dirpath, _, filenames in os.walk(path):
                for fname in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, fname))
                    except OSError:
                        pass
        except OSError:
            pass
        return total

    safe_ws = os.path.basename(workspace_id)
    documents_bytes = _dir_bytes(os.path.join(settings.STORAGE_PATH, safe_ws))
    exports_bytes = _dir_bytes(os.path.join(settings.EXPORT_PATH, safe_ws))

    db_bytes = 0
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:////", "/")
    try:
        db_bytes = os.path.getsize(db_path)
    except OSError:
        pass

    return {
        "data": {
            "documents_bytes": documents_bytes,
            "exports_bytes": exports_bytes,
            "db_bytes": db_bytes,
        },
        "status": "ok",
    }


@router.get("/settings/diagnostic-log")
async def get_diagnostic_log(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    from app.skills.registry import get_registry

    doc_count = (
        await db.execute(
            select(func.count(Document.id)).where(Document.workspace_id == workspace_id)
        )
    ).scalar() or 0

    event_count = (
        await db.execute(
            select(func.count(TaxEvent.id)).where(TaxEvent.workspace_id == workspace_id)
        )
    ).scalar() or 0

    registry = get_registry()
    skills = [
        {"skill_id": s.skill_id, "version": getattr(s, "version", "unknown")}
        for s in registry._skills.values()
    ]

    payload = {
        "document_count": doc_count,
        "event_count": event_count,
        "active_skills": skills,
        "ai_provider": settings.AI_PROVIDER,
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="diagnostic.json"'},
    )


@router.get("/settings/about")
async def get_about(workspace_id: str = Depends(require_auth)):
    from app.skills.registry import get_registry

    registry = get_registry()
    skills = [
        {
            "skill_id": s.skill_id,
            "version": getattr(s, "version", "unknown"),
            "display_name": getattr(s, "display_name", s.skill_id),
        }
        for s in registry._skills.values()
    ]
    return {
        "data": {
            "active_skills": skills,
            "disclaimer": _DISCLAIMER,
        },
        "status": "ok",
    }
