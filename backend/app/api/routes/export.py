from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timedelta, timezone

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.db.models import Workspace
from app.engines.export import ExportEngine
from app.errors import error_response
from app.services.export_eligibility import ExportEligibilityService

router = APIRouter()

_engine = ExportEngine()
_eligibility_service = ExportEligibilityService()


class GenerateRequest(BaseModel):
    password: str


def _record_dict(r) -> dict:
    return {
        "id": r.id,
        "workspace_id": r.workspace_id,
        "financial_year": r.financial_year,
        "readiness_pct": r.readiness_pct,
        "confirmed_count": r.confirmed_count,
        "review_count": r.review_count,
        "agent_count": r.agent_count,
        "missing_count": r.missing_count,
        "status": r.status,
        "file_size_bytes": r.file_size_bytes,
        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


_SAFE_INTERRUPTED_MESSAGE = "Export interrupted (server restart or worker shutdown). Please generate again."
_GENERIC_FAILED_MESSAGE = "Export failed. Please generate again."


# ── GET /export/eligibility ───────────────────────────────────────────────────

@router.get("/export/eligibility")
async def get_eligibility(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await _engine.check_eligibility(workspace_id, db)
    ws = await db.get(Workspace, workspace_id)
    preview = None
    if ws:
        preview_obj = await _eligibility_service.build_preview(
            workspace_id=workspace_id,
            financial_year=ws.financial_year,
            db=db,
        )
        preview = {
            "evidence_required_total": preview_obj.evidence_required_total,
            "evidence_required_blocking_total": preview_obj.evidence_required_blocking_total,
            "evidence_required_missing_total": preview_obj.evidence_required_missing_total,
            "evidence_required_partial_total": preview_obj.evidence_required_partial_total,
            "blocking_evidence_obligations": preview_obj.blocking_evidence_obligations,
            "would_block_export": preview_obj.would_block_export,
        }
    evidence_export_status = {
        "would_block_export": bool(preview["would_block_export"]) if preview else False,
        "blocking_required_count": int(preview["evidence_required_blocking_total"]) if preview else 0,
        "missing_required_count": int(preview["evidence_required_missing_total"]) if preview else 0,
        "partial_required_count": int(preview["evidence_required_partial_total"]) if preview else 0,
        "blocking_evidence_obligations": preview["blocking_evidence_obligations"] if preview else [],
        "mode": "soft_block",
        "message": (
            "Evidence requirements are currently satisfied."
            if not (preview and preview["would_block_export"])
            else (
                "Export is allowed for now, but required evidence is incomplete and may block export "
                "in a future hardening milestone."
            )
        ),
    }
    return {
        "data": {
            "can_export": result.can_export,
            "blocking_reasons": result.blocking_reasons,
            "warnings": result.warnings,
            "eligibility_preview": preview,
            "evidence_export_status": evidence_export_status,
        }
    }


# ── POST /export/generate ─────────────────────────────────────────────────────

@router.post("/export/generate")
async def generate_export(
    body: GenerateRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    eligibility = await _engine.check_eligibility(workspace_id, db)
    if not eligibility.can_export:
        raise HTTPException(
            status_code=422,
            detail=error_response(
                "export_blocked",
                " ".join(eligibility.blocking_reasons),
                retryable=False,
            ),
        )

    record = await _engine.generate(workspace_id, body.password, db)
    return {
        "data": {
            "export_id": record.id,
            "status": record.status,
            "warnings": eligibility.warnings,
        }
    }


# ── GET /export/{id}/status ───────────────────────────────────────────────────

@router.get("/export/{export_id}/status")
async def get_export_status(
    export_id: str,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    from app.repositories import exports as exports_repo

    record = await exports_repo.get_by_id(db, export_id)
    if record is None or record.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail=error_response("export_not_found", "Export not found.", retryable=False),
        )

    if record.status == "generating":
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=600)
        created = record.created_at.replace(tzinfo=None) if record.created_at else None
        if created and created <= cutoff:
            record = await exports_repo.update_status(db, export_id, "failed")

    data = _record_dict(record)

    if record.status == "failed":
        from app.repositories import jobs as jobs_repo

        job = await jobs_repo.get_export_job_by_export_id(db, workspace_id, export_id)
        if job and job.error == _SAFE_INTERRUPTED_MESSAGE:
            data["error_message"] = _SAFE_INTERRUPTED_MESSAGE
        else:
            data["error_message"] = _GENERIC_FAILED_MESSAGE

    return {"data": data}


# ── GET /export/{id}/download ─────────────────────────────────────────────────

@router.get("/export/{export_id}/download")
async def download_export(
    export_id: str,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    try:
        data, filename = await _engine.get_download(export_id, workspace_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=error_response("export_not_available", str(e), retryable=False),
        )

    return StreamingResponse(
        iter([data]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(data)),
        },
    )


# ── GET /export/history ───────────────────────────────────────────────────────

@router.get("/export/history")
async def get_export_history(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    records = await _engine.get_history(workspace_id, db)
    return {"data": [_record_dict(r) for r in records]}
