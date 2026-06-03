from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import AuditLog
from app.errors import AppError
from app.services.recovery import RecoveryService


RECOVERY_GUARD_POLICY_WINDOW_HOURS = 24


@dataclass
class BackupSafetyStatus:
    status: str
    last_backup_at: str | None
    last_verified_at: str | None
    requires_backup_before_dangerous_action: bool
    policy_window_hours: int

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "last_backup_at": self.last_backup_at,
            "last_verified_at": self.last_verified_at,
            "requires_backup_before_dangerous_action": self.requires_backup_before_dangerous_action,
            "policy_window_hours": self.policy_window_hours,
        }


class RecoveryGuardError(AppError):
    def __init__(self, status: BackupSafetyStatus) -> None:
        super().__init__(
            error_code="recent_backup_required",
            message="Create and verify a workspace backup before continuing.",
            action="create_backup",
            retryable=False,
        )
        self.status = status


class RecoveryPolicyService:
    def __init__(
        self,
        backup_path: str | None = None,
        policy_window_hours: int = RECOVERY_GUARD_POLICY_WINDOW_HOURS,
    ) -> None:
        self._backup_path = backup_path or settings.BACKUP_PATH
        self._policy_window_hours = policy_window_hours

    def get_backup_safety_status(self, workspace_id: str) -> BackupSafetyStatus:
        workspace_dir = Path(self._backup_path) / workspace_id
        if not workspace_dir.exists():
            return self._status("missing", None, None)

        backup_files = sorted(workspace_dir.glob("*.trb"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backup_files:
            return self._status("missing", None, None)

        service = RecoveryService(backup_path=self._backup_path)
        latest_verified_at: datetime | None = None
        latest_backup_at: datetime | None = None
        for path in backup_files:
            backup_id = path.stem
            try:
                verify = service.verify_backup_file(workspace_id=workspace_id, backup_id=backup_id)
            except Exception:
                continue
            if not verify.ok:
                continue
            created_at = self._parse_datetime((verify.manifest_summary or {}).get("created_at"))
            if created_at is None:
                created_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            latest_backup_at = max(latest_backup_at, created_at) if latest_backup_at else created_at
            latest_verified_at = max(latest_verified_at, created_at) if latest_verified_at else created_at

        if latest_verified_at is None:
            latest_file_time = datetime.fromtimestamp(backup_files[0].stat().st_mtime, timezone.utc)
            return self._status("failed", latest_file_time.isoformat(), None)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._policy_window_hours)
        status = "healthy" if latest_verified_at >= cutoff else "stale"
        return self._status(
            status,
            latest_backup_at.isoformat() if latest_backup_at else None,
            latest_verified_at.isoformat(),
        )

    async def require_recent_backup_or_raise(
        self,
        *,
        db: AsyncSession,
        workspace_id: str,
        operation: str,
    ) -> BackupSafetyStatus:
        status = self.get_backup_safety_status(workspace_id)
        await self._audit(db=db, workspace_id=workspace_id, action="recovery_guard_checked", operation=operation)
        if status.requires_backup_before_dangerous_action:
            await self._audit(db=db, workspace_id=workspace_id, action="recovery_guard_blocked", operation=operation)
            raise RecoveryGuardError(status)
        await self._audit(db=db, workspace_id=workspace_id, action="recovery_guard_passed", operation=operation)
        return status

    def _status(self, status: str, last_backup_at: str | None, last_verified_at: str | None) -> BackupSafetyStatus:
        return BackupSafetyStatus(
            status=status,
            last_backup_at=last_backup_at,
            last_verified_at=last_verified_at,
            requires_backup_before_dangerous_action=status != "healthy",
            policy_window_hours=self._policy_window_hours,
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    async def _audit(*, db: AsyncSession, workspace_id: str, action: str, operation: str) -> None:
        db.add(
            AuditLog(
                workspace_id=workspace_id,
                action=action,
                actor="system",
                note=f"operation={operation}",
            )
        )
        await db.commit()
