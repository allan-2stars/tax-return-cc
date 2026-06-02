from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.db.models import AuditLog
from app.errors import error_response
from app.services.recovery import (
    ENCRYPTION_MODE_SERVER_DERIVED,
    RecoveryPreviewError,
    RecoveryService,
)

router = APIRouter()


class VerifyBackupRequest(BaseModel):
    backup_id: str


class CreateBackupRequest(BaseModel):
    encryption_mode: str = ENCRYPTION_MODE_SERVER_DERIVED
    recovery_key: str | None = None


class VerifyRecoveryKeyRequest(BaseModel):
    recovery_key: str = Field(..., min_length=8)


class PreviewRestoreRequest(BaseModel):
    backup_id: str
    recovery_key: str | None = None


@router.post("/recovery/backups")
async def create_backup(
    body: CreateBackupRequest | None = None,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    service = RecoveryService()
    payload = body or CreateBackupRequest()
    try:
        result = await service.create_backup(
            workspace_id=workspace_id,
            db=db,
            encryption_mode=payload.encryption_mode,
            recovery_key=payload.recovery_key,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=error_response("backup_failed", str(e), retryable=False),
        )

    return {
        "data": {
            "backup_id": result.backup_id,
            "status": result.status,
            "created_at": result.created_at,
            "filename": result.filename,
            "path": result.path,
            "manifest_summary": result.manifest_summary,
            "verification": result.verification,
        }
    }


@router.post("/recovery/backups/verify")
async def verify_backup(
    body: VerifyBackupRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    service = RecoveryService()
    try:
        result = service.verify_backup_file(workspace_id=workspace_id, backup_id=body.backup_id, db=db)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=error_response("backup_not_found", "Backup artifact not found.", retryable=False),
        )

    if not result.ok:
        raise HTTPException(
            status_code=422,
            detail=error_response(
                result.verification.get("error_code", "backup_invalid"),
                result.verification.get("message", "Backup verification failed."),
                retryable=False,
            ),
        )

    return {
        "data": {
            "backup_id": result.backup_id,
            "status": result.status,
            "manifest_summary": result.manifest_summary,
            "verification": result.verification,
        }
    }


@router.post("/recovery/key/verify")
async def verify_recovery_key(
    body: VerifyRecoveryKeyRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    service = RecoveryService()
    window_start = datetime.now(timezone.utc) - timedelta(minutes=5)
    failure_count = (
        await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.workspace_id == workspace_id,
                AuditLog.action == "recovery_key_verify_failure",
                AuditLog.created_at >= window_start,
            )
        )
    ).scalar_one()
    if int(failure_count or 0) >= 5:
        raise HTTPException(
            status_code=429,
            detail=error_response(
                "too_many_attempts",
                "Too many failed verification attempts. Please try again later.",
                retryable=True,
            ),
        )

    verified = await service.verify_recovery_key(
        workspace_id=workspace_id,
        recovery_key=body.recovery_key,
        db=db,
    )
    await service.log_recovery_key_verification(
        db=db,
        workspace_id=workspace_id,
        success=verified,
    )

    if not verified:
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "invalid_recovery_key",
                "Recovery key verification failed.",
                retryable=False,
            ),
        )
    return {
        "data": {
            "status": "ok",
            "verified": True,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
    }


@router.post("/recovery/restore/preview")
async def preview_restore(
    body: PreviewRestoreRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    service = RecoveryService()
    try:
        result = await service.preview_backup(
            workspace_id=workspace_id,
            backup_id=body.backup_id,
            db=db,
            recovery_key=body.recovery_key,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=error_response("backup_not_found", "Backup artifact not found.", retryable=False),
        )
    except RecoveryPreviewError as e:
        raise HTTPException(
            status_code=422,
            detail=error_response(e.error_code, e.message, retryable=False),
        )

    return {
        "data": {
            "status": result.status,
            "preview_id": result.preview_id,
            "backup_id": result.backup_id,
            "workspace_id": result.workspace_id,
            "financial_year": result.financial_year,
            "created_at": result.created_at,
            "encryption_mode": result.encryption_mode,
            "record_counts": result.record_counts,
            "included_sections": result.included_sections,
            "compatibility": result.compatibility,
            "blockers": result.blockers,
            "warnings": result.warnings,
            "can_restore": result.can_restore,
        }
    }
