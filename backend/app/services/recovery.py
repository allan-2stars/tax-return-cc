from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import bcrypt
import pyzipper
from sqlalchemy import DateTime, delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import (
    AuditLog,
    Document,
    EvidenceMatch,
    EvidenceObligation,
    InterviewSession,
    ReviewItem,
    TaxEvent,
    TaxProfile,
    Workspace,
    WorkspaceSecurity,
)
from app.security import normalize_recovery_key
from app.storage import get_storage_backend
from app.services.recovery_compatibility import evaluate_restore_compatibility


BACKUP_FORMAT_VERSION = "2026.1"
ENCRYPTION_MODE_SERVER_DERIVED = "server_derived"
ENCRYPTION_MODE_RECOVERY_KEY_DERIVED = "recovery_key_derived"
REQUIRED_MANIFEST_FIELDS = {
    "backup_format_version",
    "backup_id",
    "workspace_id",
    "financial_year",
    "created_at",
    "app_version",
    "db_schema_version",
    "evidence_rule_version_distribution",
    "included_sections",
    "record_counts",
    "checksum_metadata",
    "encryption_mode",
}
REQUIRED_SECTIONS = {
    "workspace",
    "tax_profiles",
    "interview_sessions",
    "tax_events",
    "review_items",
    "evidence_obligations",
    "evidence_matches",
    "documents_metadata",
}


@dataclass
class BackupResult:
    backup_id: str
    status: str
    created_at: str
    filename: str
    path: str
    manifest_summary: dict
    verification: dict


@dataclass
class VerifyResult:
    ok: bool
    status: str
    backup_id: str
    verification: dict
    manifest_summary: dict | None = None


@dataclass
class PreviewResult:
    status: str
    preview_id: str
    backup_id: str
    workspace_id: str
    financial_year: str | None
    created_at: str | None
    encryption_mode: str | None
    record_counts: dict
    included_sections: list[str]
    compatibility: dict
    blockers: list[str]
    warnings: list[str]
    can_restore: bool


class RecoveryPreviewError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(message)


@dataclass
class RestoreResult:
    status: str
    restored_workspace_id: str
    checkpoint_id: str
    rollback_performed: bool
    verification_result: dict
    post_restore_reconcile: dict
    warnings: list[str]
    errors: list[str]


class RecoveryRestoreError(Exception):
    def __init__(self, error_code: str, message: str, result: RestoreResult | None = None) -> None:
        self.error_code = error_code
        self.message = message
        self.result = result
        super().__init__(message)


class RecoveryService:
    def __init__(self, backup_path: str | None = None) -> None:
        self._backup_path = backup_path or settings.BACKUP_PATH

    async def create_backup(
        self,
        workspace_id: str,
        db: AsyncSession,
        *,
        encryption_mode: str = ENCRYPTION_MODE_SERVER_DERIVED,
        recovery_key: str | None = None,
    ) -> BackupResult:
        workspace = await db.get(Workspace, workspace_id)
        if workspace is None:
            raise ValueError("Workspace not found.")
        if encryption_mode not in {ENCRYPTION_MODE_SERVER_DERIVED, ENCRYPTION_MODE_RECOVERY_KEY_DERIVED}:
            raise ValueError("Unsupported encryption mode.")

        password_bytes = await self._password_bytes_for_backup(
            workspace_id=workspace_id,
            db=db,
            encryption_mode=encryption_mode,
            recovery_key=recovery_key,
        )

        backup_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        workspace_dir = Path(self._backup_path) / workspace_id
        workspace_dir.mkdir(parents=True, exist_ok=True)
        final_path = workspace_dir / f"{backup_id}.trb"

        temp_fd, temp_path = tempfile.mkstemp(prefix=f"{backup_id}-", suffix=".tmp", dir=workspace_dir)
        os.close(temp_fd)
        temp_path_obj = Path(temp_path)

        try:
            bundle = await self._collect_bundle(
                workspace,
                db,
                created_at,
                backup_id,
                encryption_mode=encryption_mode,
            )
            self._write_encrypted_bundle(temp_path_obj, bundle, password_bytes)
            os.replace(temp_path_obj, final_path)
            verify = self.verify_backup_file(
                workspace_id=workspace_id,
                backup_id=backup_id,
                db=db,
                recovery_key=recovery_key if encryption_mode == ENCRYPTION_MODE_RECOVERY_KEY_DERIVED else None,
            )
            if not verify.ok:
                raise ValueError("Backup verification failed after creation.")
            return BackupResult(
                backup_id=backup_id,
                status="ok",
                created_at=created_at,
                filename=final_path.name,
                path=str(final_path),
                manifest_summary=verify.manifest_summary or {},
                verification=verify.verification,
            )
        finally:
            if temp_path_obj.exists():
                temp_path_obj.unlink(missing_ok=True)

    async def preview_backup(
        self,
        *,
        workspace_id: str,
        backup_id: str,
        db: AsyncSession,
        recovery_key: str | None = None,
    ) -> PreviewResult:
        path = Path(self._backup_path) / workspace_id / f"{backup_id}.trb"
        if not path.exists():
            raise FileNotFoundError("Backup artifact not found.")

        try:
            with pyzipper.AESZipFile(
                str(path),
                "r",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as zf:
                try:
                    manifest = self._read_manifest_with_fallback_passwords(
                        zf=zf,
                        workspace_id=workspace_id,
                        recovery_key=recovery_key,
                    )
                except RuntimeError:
                    raise RecoveryPreviewError("decrypt_failed", "Unable to decrypt backup artifact.")
                except Exception:
                    raise RecoveryPreviewError("manifest_missing_or_invalid", "Manifest missing or invalid.")

                integrity_error = self._validate_checksum_entries(zf=zf, manifest=manifest)
                if integrity_error is not None:
                    raise RecoveryPreviewError(integrity_error["error_code"], integrity_error["message"])

                workspace_payload = self._read_workspace_section(
                    zf=zf,
                    manifest=manifest,
                    workspace_id=workspace_id,
                    recovery_key=recovery_key,
                )
        except RecoveryPreviewError:
            raise
        except Exception:
            raise RecoveryPreviewError("backup_invalid", "Backup artifact is invalid or corrupted.")

        missing_fields = sorted(list(REQUIRED_MANIFEST_FIELDS - set(manifest.keys())))
        compatibility = evaluate_restore_compatibility(manifest)
        blockers = list(compatibility.blockers)
        warnings = list(compatibility.warnings)
        if missing_fields:
            blockers.append(f"Backup metadata is missing required fields: {', '.join(missing_fields)}.")
        missing_sections = sorted(list(REQUIRED_SECTIONS - set(manifest.get("included_sections") or [])))
        if missing_sections:
            blockers.append(f"Required backup sections are missing: {', '.join(missing_sections)}.")

        existing_workspace = await db.get(Workspace, manifest.get("workspace_id"))
        if existing_workspace is not None:
            blockers.append("A workspace with the same id already exists in this deployment.")

        backup_workspace_name = None
        if isinstance(workspace_payload, dict):
            backup_workspace_name = workspace_payload.get("name")
        if backup_workspace_name and manifest.get("financial_year"):
            same_name_fy = (
                await db.execute(
                    select(Workspace).where(
                        Workspace.name == backup_workspace_name,
                        Workspace.financial_year == manifest.get("financial_year"),
                    )
                )
            ).scalar_one_or_none()
            if same_name_fy is not None:
                warnings.append("A workspace with the same name and financial year already exists.")

        return PreviewResult(
            status="ok",
            preview_id=str(uuid4()),
            backup_id=str(manifest.get("backup_id") or backup_id),
            workspace_id=str(manifest.get("workspace_id") or workspace_id),
            financial_year=manifest.get("financial_year"),
            created_at=manifest.get("created_at"),
            encryption_mode=manifest.get("encryption_mode"),
            record_counts=manifest.get("record_counts") or {},
            included_sections=manifest.get("included_sections") or [],
            compatibility={
                "backup_format_version": manifest.get("backup_format_version"),
                "app_version": manifest.get("app_version"),
                "db_schema_version": manifest.get("db_schema_version"),
                "notes": compatibility.notes,
            },
            blockers=blockers,
            warnings=warnings,
            can_restore=len(blockers) == 0,
        )

    async def restore_backup(
        self,
        *,
        workspace_id: str,
        backup_id: str,
        db: AsyncSession,
        recovery_key: str | None = None,
        conflict_policy: str | None = None,
    ) -> RestoreResult:
        manifest, sections, document_blobs, warnings = self._load_backup_payload(
            workspace_id=workspace_id,
            backup_id=backup_id,
            recovery_key=recovery_key,
        )
        if manifest.get("workspace_id") != workspace_id:
            raise RecoveryRestoreError("workspace_mismatch", "Backup does not match the current workspace.")

        compatibility = evaluate_restore_compatibility(manifest)
        blockers = list(compatibility.blockers)
        missing_fields = sorted(list(REQUIRED_MANIFEST_FIELDS - set(manifest.keys())))
        if missing_fields:
            blockers.append(f"Backup metadata is missing required fields: {', '.join(missing_fields)}.")
        missing_sections = sorted(list(REQUIRED_SECTIONS - set(manifest.get("included_sections") or [])))
        if missing_sections:
            blockers.append(f"Required backup sections are missing: {', '.join(missing_sections)}.")
        if conflict_policy != "replace_current_workspace":
            blockers.append("Restore requires conflict_policy=replace_current_workspace.")
        if blockers:
            raise RecoveryRestoreError("restore_blocked", "Backup cannot be restored.")

        await self._log_restore_event(db=db, workspace_id=workspace_id, action="restore_apply_started", note=f"backup_id={backup_id}")
        checkpoint_id = ""
        rollback_performed = False
        try:
            checkpoint = await self.create_backup(workspace_id=workspace_id, db=db)
            checkpoint_id = checkpoint.backup_id
            await self._apply_payload_to_workspace(
                workspace_id=workspace_id,
                manifest=manifest,
                sections=sections,
                document_blobs=document_blobs,
                db=db,
            )
            verification = await self._verify_restored_workspace(workspace_id, db)
            post_restore_reconcile = await self._run_post_restore_reconcile(
                workspace_id=workspace_id,
                financial_year=manifest.get("financial_year"),
                db=db,
            )
            await self._log_restore_event(
                db=db,
                workspace_id=workspace_id,
                action="restore_apply_success",
                note=f"backup_id={backup_id}; checkpoint_id={checkpoint_id}",
            )
            return RestoreResult(
                status="ok",
                restored_workspace_id=workspace_id,
                checkpoint_id=checkpoint_id,
                rollback_performed=False,
                verification_result=verification,
                post_restore_reconcile=post_restore_reconcile,
                warnings=list(compatibility.warnings) + warnings,
                errors=[],
            )
        except Exception as exc:
            await self._log_restore_event(
                db=db,
                workspace_id=workspace_id,
                action="restore_apply_failed",
                note=f"backup_id={backup_id}; checkpoint_id={checkpoint_id}; error={type(exc).__name__}",
            )
            if checkpoint_id:
                await self._log_restore_event(
                    db=db,
                    workspace_id=workspace_id,
                    action="restore_rollback_started",
                    note=f"checkpoint_id={checkpoint_id}",
                )
                try:
                    checkpoint_manifest, checkpoint_sections, checkpoint_docs, _ = self._load_backup_payload(
                        workspace_id=workspace_id,
                        backup_id=checkpoint_id,
                        recovery_key=None,
                    )
                    await self._apply_payload_to_workspace(
                        workspace_id=workspace_id,
                        manifest=checkpoint_manifest,
                        sections=checkpoint_sections,
                        document_blobs=checkpoint_docs,
                        db=db,
                    )
                    rollback_performed = True
                    await self._log_restore_event(
                        db=db,
                        workspace_id=workspace_id,
                        action="restore_rollback_success",
                        note=f"checkpoint_id={checkpoint_id}",
                    )
                except Exception as rollback_exc:
                    await self._log_restore_event(
                        db=db,
                        workspace_id=workspace_id,
                        action="restore_rollback_failed",
                        note=f"checkpoint_id={checkpoint_id}; error={type(rollback_exc).__name__}",
                    )
                    raise RecoveryRestoreError(
                        "restore_rollback_failed",
                        "Restore failed and rollback also failed.",
                        RestoreResult(
                            status="failed",
                            restored_workspace_id=workspace_id,
                    checkpoint_id=checkpoint_id,
                    rollback_performed=False,
                    verification_result={"ok": False},
                    post_restore_reconcile=self._skipped_post_restore_reconcile(),
                    warnings=list(compatibility.warnings) + warnings,
                    errors=[f"Restore failed and rollback also failed: {type(exc).__name__}; {type(rollback_exc).__name__}."],
                ),
            )
            raise RecoveryRestoreError(
                "restore_failed",
                "Restore failed and workspace was rolled back.",
                RestoreResult(
                    status="failed",
                    restored_workspace_id=workspace_id,
                    checkpoint_id=checkpoint_id,
                    rollback_performed=rollback_performed,
                    verification_result={"ok": False},
                    post_restore_reconcile=self._skipped_post_restore_reconcile(),
                    warnings=list(compatibility.warnings) + warnings,
                    errors=[f"Restore failed and workspace was rolled back: {type(exc).__name__}."],
                ),
            )

    def verify_backup_file(
        self,
        workspace_id: str,
        backup_id: str,
        *,
        db: AsyncSession | None = None,
        recovery_key: str | None = None,
    ) -> VerifyResult:
        path = Path(self._backup_path) / workspace_id / f"{backup_id}.trb"
        if not path.exists():
            raise FileNotFoundError("Backup artifact not found.")

        try:
            with pyzipper.AESZipFile(
                str(path),
                "r",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as zf:
                try:
                    manifest = self._read_manifest_with_fallback_passwords(
                        zf=zf,
                        workspace_id=workspace_id,
                        recovery_key=recovery_key,
                    )
                except Exception:
                    return VerifyResult(
                        ok=False,
                        status="failed",
                        backup_id=backup_id,
                        verification={"ok": False, "error_code": "manifest_missing_or_invalid", "message": "Manifest missing or invalid."},
                    )

                integrity_error = self._validate_manifest_sections_and_checksums(zf=zf, manifest=manifest)
                if integrity_error is not None:
                    return VerifyResult(
                        ok=False,
                        status="failed",
                        backup_id=backup_id,
                        verification={"ok": False, **integrity_error},
                        manifest_summary=self._manifest_summary(manifest),
                    )

                return VerifyResult(
                    ok=True,
                    status="ok",
                    backup_id=backup_id,
                    verification={"ok": True, "error_code": None, "message": "Backup verification passed."},
                    manifest_summary=self._manifest_summary(manifest),
                )
        except RuntimeError:
            return VerifyResult(
                ok=False,
                status="failed",
                backup_id=backup_id,
                verification={
                    "ok": False,
                    "error_code": "decrypt_failed",
                    "message": "Unable to decrypt backup artifact.",
                },
            )
        except Exception:
            return VerifyResult(
                ok=False,
                status="failed",
                backup_id=backup_id,
                verification={
                    "ok": False,
                    "error_code": "backup_invalid",
                    "message": "Backup artifact is invalid or corrupted.",
                },
            )

    async def _collect_bundle(
        self,
        workspace: Workspace,
        db: AsyncSession,
        created_at: str,
        backup_id: str,
        *,
        encryption_mode: str,
    ) -> dict:
        workspace_id = workspace.id
        financial_year = workspace.financial_year

        profiles = (await db.execute(select(TaxProfile).where(TaxProfile.workspace_id == workspace_id))).scalars().all()
        sessions = (await db.execute(select(InterviewSession).where(InterviewSession.workspace_id == workspace_id))).scalars().all()
        events = (await db.execute(select(TaxEvent).where(TaxEvent.workspace_id == workspace_id))).scalars().all()
        review_items = (await db.execute(select(ReviewItem).where(ReviewItem.workspace_id == workspace_id))).scalars().all()
        obligations = (
            await db.execute(
                select(EvidenceObligation).where(
                    EvidenceObligation.workspace_id == workspace_id,
                    EvidenceObligation.financial_year == financial_year,
                )
            )
        ).scalars().all()
        matches = (
            await db.execute(
                select(EvidenceMatch).where(EvidenceMatch.workspace_id == workspace_id)
            )
        ).scalars().all()
        documents = (await db.execute(select(Document).where(Document.workspace_id == workspace_id))).scalars().all()

        db_schema_version = None
        try:
            db_schema_version = (await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))).scalar_one_or_none()
        except Exception:
            db_schema_version = None

        rule_version_rows = (
            await db.execute(
                select(EvidenceObligation.rule_version, func.count(EvidenceObligation.id))
                .where(EvidenceObligation.workspace_id == workspace_id)
                .group_by(EvidenceObligation.rule_version)
            )
        ).all()
        rule_distribution = {
            (rule if rule is not None else "unknown"): int(count) for rule, count in rule_version_rows
        }

        sections_payload: dict[str, bytes] = {}
        sections_payload["sections/workspace.json"] = self._json_bytes(self._row_to_dict(workspace))
        sections_payload["sections/tax_profiles.json"] = self._json_bytes([self._row_to_dict(x) for x in profiles])
        sections_payload["sections/interview_sessions.json"] = self._json_bytes([self._row_to_dict(x) for x in sessions])
        sections_payload["sections/tax_events.json"] = self._json_bytes([self._row_to_dict(x) for x in events])
        sections_payload["sections/review_items.json"] = self._json_bytes([self._row_to_dict(x) for x in review_items])
        sections_payload["sections/evidence_obligations.json"] = self._json_bytes([self._row_to_dict(x) for x in obligations])
        sections_payload["sections/evidence_matches.json"] = self._json_bytes([self._row_to_dict(x) for x in matches])
        sections_payload["sections/documents_metadata.json"] = self._json_bytes([self._row_to_dict(x) for x in documents])

        included_sections = sorted(list(REQUIRED_SECTIONS))
        record_counts = {
            "tax_profiles": len(profiles),
            "interview_sessions": len(sessions),
            "tax_events": len(events),
            "review_items": len(review_items),
            "evidence_obligations": len(obligations),
            "evidence_matches": len(matches),
            "documents_metadata": len(documents),
            "document_binaries": 0,
        }

        storage = get_storage_backend()
        for document in documents:
            if not document.storage_key:
                continue
            try:
                if not storage.exists(document.storage_key):
                    continue
                blob = storage.get(document.storage_key)
            except Exception:
                continue
            fname = f"documents/{document.id}/{Path(document.original_filename or 'file.bin').name}"
            sections_payload[fname] = blob
            record_counts["document_binaries"] += 1

        checksums = {name: hashlib.sha256(payload).hexdigest() for name, payload in sections_payload.items()}
        manifest = {
            "backup_format_version": BACKUP_FORMAT_VERSION,
            "backup_id": backup_id,
            "workspace_id": workspace_id,
            "financial_year": financial_year,
            "created_at": created_at,
            "app_version": settings.APP_VERSION,
            "db_schema_version": db_schema_version,
            "evidence_rule_version_distribution": rule_distribution,
            "included_sections": included_sections,
            "record_counts": record_counts,
            "checksum_metadata": {"algorithm": "sha256", "entries": checksums},
            "encryption_mode": encryption_mode,
        }
        return {
            "manifest": manifest,
            "sections_payload": sections_payload,
        }

    def _load_backup_payload(
        self,
        *,
        workspace_id: str,
        backup_id: str,
        recovery_key: str | None,
    ) -> tuple[dict, dict[str, object], dict[str, bytes], list[str]]:
        path = Path(self._backup_path) / workspace_id / f"{backup_id}.trb"
        if not path.exists():
            raise FileNotFoundError("Backup artifact not found.")
        try:
            with pyzipper.AESZipFile(
                str(path),
                "r",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as zf:
                try:
                    manifest = self._read_manifest_with_fallback_passwords(
                        zf=zf,
                        workspace_id=workspace_id,
                        recovery_key=recovery_key,
                    )
                except RuntimeError:
                    raise RecoveryPreviewError("decrypt_failed", "Unable to decrypt backup artifact.")
                except Exception:
                    raise RecoveryPreviewError("manifest_missing_or_invalid", "Manifest missing or invalid.")
                integrity_error = self._validate_checksum_entries(zf=zf, manifest=manifest)
                if integrity_error is not None:
                    raise RecoveryPreviewError(integrity_error["error_code"], integrity_error["message"])

                sections = {
                    "workspace": self._read_json_section(zf, "sections/workspace.json", workspace_id, recovery_key),
                    "tax_profiles": self._read_json_section(zf, "sections/tax_profiles.json", workspace_id, recovery_key) or [],
                    "interview_sessions": self._read_json_section(zf, "sections/interview_sessions.json", workspace_id, recovery_key) or [],
                    "tax_events": self._read_json_section(zf, "sections/tax_events.json", workspace_id, recovery_key) or [],
                    "review_items": self._read_json_section(zf, "sections/review_items.json", workspace_id, recovery_key) or [],
                    "evidence_obligations": self._read_json_section(zf, "sections/evidence_obligations.json", workspace_id, recovery_key) or [],
                    "evidence_matches": self._read_json_section(zf, "sections/evidence_matches.json", workspace_id, recovery_key) or [],
                    "documents_metadata": self._read_json_section(zf, "sections/documents_metadata.json", workspace_id, recovery_key) or [],
                }
                document_blobs: dict[str, bytes] = {}
                for name in zf.namelist():
                    if name.startswith("documents/"):
                        document_blobs[name] = self._read_bytes_entry(zf, name, workspace_id, recovery_key)
                return manifest, sections, document_blobs, []
        except RecoveryPreviewError:
            raise
        except Exception:
            raise RecoveryPreviewError("backup_invalid", "Backup artifact is invalid or corrupted.")

    async def _apply_payload_to_workspace(
        self,
        *,
        workspace_id: str,
        manifest: dict,
        sections: dict[str, object],
        document_blobs: dict[str, bytes],
        db: AsyncSession,
    ) -> None:
        await self._delete_workspace_rows(db=db, workspace_id=workspace_id)

        workspace_payload = dict(sections.get("workspace") or {})
        workspace = await db.get(Workspace, workspace_id)
        if workspace is None:
            workspace = Workspace(
                id=workspace_id,
                name=workspace_payload.get("name") or "Restored Workspace",
                financial_year=manifest.get("financial_year") or workspace_payload.get("financial_year") or "unknown",
                status=workspace_payload.get("status") or "active",
            )
            db.add(workspace)
        else:
            self._apply_row_values(workspace, workspace_payload)

        self._add_rows(db, TaxProfile, sections.get("tax_profiles") or [])
        self._add_rows(db, InterviewSession, sections.get("interview_sessions") or [])
        self._add_rows(db, Document, sections.get("documents_metadata") or [])
        self._add_rows(db, TaxEvent, sections.get("tax_events") or [])
        self._add_rows(db, ReviewItem, sections.get("review_items") or [])
        self._add_rows(db, EvidenceObligation, sections.get("evidence_obligations") or [])
        self._add_rows(db, EvidenceMatch, sections.get("evidence_matches") or [])

        self._restore_document_blobs(
            document_blobs=document_blobs,
            document_rows=sections.get("documents_metadata") or [],
        )
        await db.commit()

    async def _delete_workspace_rows(self, *, db: AsyncSession, workspace_id: str) -> None:
        for model in (EvidenceMatch, EvidenceObligation, ReviewItem, TaxEvent, Document, InterviewSession, TaxProfile):
            await db.execute(delete(model).where(model.workspace_id == workspace_id))
        await db.flush()

    def _add_rows(self, db: AsyncSession, model, rows: object) -> None:
        if not isinstance(rows, list):
            return
        allowed = {col.name for col in model.__table__.columns}
        for row in rows:
            if not isinstance(row, dict):
                continue
            payload = {key: self._coerce_column_value(model, key, value) for key, value in row.items() if key in allowed}
            db.add(model(**payload))

    def _apply_row_values(self, obj, row: dict) -> None:
        allowed = {col.name for col in obj.__table__.columns}
        for key, value in row.items():
            if key in allowed and key != "id":
                setattr(obj, key, self._coerce_column_value(type(obj), key, value))

    @staticmethod
    def _coerce_column_value(model, key: str, value):
        if value is None:
            return None
        col = model.__table__.columns.get(key)
        if col is not None and isinstance(col.type, DateTime) and isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return value
        return value

    def _restore_document_blobs(self, *, document_blobs: dict[str, bytes], document_rows: object) -> None:
        storage = get_storage_backend()
        storage_keys_by_document_id = {
            row.get("id"): row.get("storage_key")
            for row in document_rows
            if isinstance(row, dict) and row.get("id") and row.get("storage_key")
        }
        for backup_entry, blob in document_blobs.items():
            parts = backup_entry.split("/", 2)
            if len(parts) != 3:
                continue
            document_id = parts[1]
            storage_key = storage_keys_by_document_id.get(document_id)
            if not storage_key:
                continue
            try:
                storage.delete(storage_key)
            except Exception:
                pass
            storage.save(storage_key, blob)

    async def _verify_restored_workspace(self, workspace_id: str, db: AsyncSession) -> dict:
        workspace = await db.get(Workspace, workspace_id)
        return {"ok": workspace is not None, "workspace_id": workspace_id}

    async def _run_post_restore_reconcile(
        self,
        *,
        workspace_id: str,
        financial_year: str | None,
        db: AsyncSession,
    ) -> dict:
        await self._log_restore_event(
            db=db,
            workspace_id=workspace_id,
            action="restore_post_reconcile_started",
            note=f"financial_year={financial_year or 'unknown'}",
        )
        result = {
            "status": "skipped",
            "evidence_reconciled": False,
            "readiness_refreshed": False,
            "warnings": [],
            "errors": [],
        }
        try:
            from app.engines.readiness import ReadinessEngine
            from app.services.evidence_reconcile import EvidenceReconcileService

            evidence_outcome = await EvidenceReconcileService().trigger(
                workspace_id=workspace_id,
                financial_year=financial_year,
                trigger_source="restore_apply",
                force=True,
                db=db,
                raise_on_error=False,
            )
            if evidence_outcome.get("status") != "ok":
                result["status"] = "failed"
                result["errors"].append("Evidence reconcile failed after restore.")
                await self._log_restore_event(
                    db=db,
                    workspace_id=workspace_id,
                    action="restore_post_reconcile_failed",
                    note="evidence_reconcile_failed",
                )
                return result

            result["evidence_reconciled"] = True
            await ReadinessEngine().calculate(workspace_id, db)
            result["readiness_refreshed"] = True
            result["status"] = "success"
            await self._log_restore_event(
                db=db,
                workspace_id=workspace_id,
                action="restore_post_reconcile_success",
                note=f"financial_year={evidence_outcome.get('financial_year') or financial_year or 'unknown'}",
            )
            return result
        except Exception as exc:
            result["status"] = "failed"
            result["errors"].append(f"Post-restore reconcile failed: {type(exc).__name__}.")
            await self._log_restore_event(
                db=db,
                workspace_id=workspace_id,
                action="restore_post_reconcile_failed",
                note=f"error={type(exc).__name__}",
            )
            return result

    @staticmethod
    def _skipped_post_restore_reconcile() -> dict:
        return {
            "status": "skipped",
            "evidence_reconciled": False,
            "readiness_refreshed": False,
            "warnings": [],
            "errors": [],
        }

    async def _log_restore_event(self, *, db: AsyncSession, workspace_id: str, action: str, note: str | None = None) -> None:
        db.add(AuditLog(workspace_id=workspace_id, action=action, actor="system", note=note))
        await db.commit()

    def _write_encrypted_bundle(self, temp_path: Path, bundle: dict, password_bytes: bytes) -> None:
        with pyzipper.AESZipFile(
            str(temp_path),
            "w",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(password_bytes)
            for name, payload in bundle["sections_payload"].items():
                zf.writestr(name, payload)
            zf.writestr("manifest.json", self._json_bytes(bundle["manifest"]))

    def _password_for_workspace(self, workspace_id: str) -> bytes:
        secret = settings.SECRET_KEY or "development-insecure-secret"
        digest = hmac.new(secret.encode("utf-8"), workspace_id.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest.encode("utf-8")

    @staticmethod
    def _password_for_recovery_key(recovery_key: str) -> bytes:
        normalized = normalize_recovery_key(recovery_key)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return digest.encode("utf-8")

    async def _password_bytes_for_backup(
        self,
        *,
        workspace_id: str,
        db: AsyncSession,
        encryption_mode: str,
        recovery_key: str | None,
    ) -> bytes:
        if encryption_mode == ENCRYPTION_MODE_SERVER_DERIVED:
            return self._password_for_workspace(workspace_id)
        if not recovery_key:
            raise ValueError("Recovery key is required for recovery-key-derived backup encryption.")
        verified = await self.verify_recovery_key(workspace_id=workspace_id, recovery_key=recovery_key, db=db)
        if not verified:
            raise ValueError("Recovery key verification failed.")
        return self._password_for_recovery_key(recovery_key)

    def _read_manifest_with_fallback_passwords(
        self,
        *,
        zf: pyzipper.AESZipFile,
        workspace_id: str,
        recovery_key: str | None,
    ) -> dict:
        passwords: list[bytes] = []
        if recovery_key:
            passwords.append(self._password_for_recovery_key(recovery_key))
        passwords.append(self._password_for_workspace(workspace_id))
        for pwd in passwords:
            zf.setpassword(pwd)
            try:
                return json.loads(zf.read("manifest.json").decode("utf-8"))
            except RuntimeError:
                continue
            except Exception:
                raise
        raise RuntimeError("Unable to read manifest.")

    def _read_workspace_section(
        self,
        *,
        zf: pyzipper.AESZipFile,
        manifest: dict,
        workspace_id: str,
        recovery_key: str | None,
    ) -> dict | None:
        section_name = "sections/workspace.json"
        entries = (manifest.get("checksum_metadata") or {}).get("entries") or {}
        if section_name not in entries:
            return None
        passwords: list[bytes] = []
        if recovery_key:
            passwords.append(self._password_for_recovery_key(recovery_key))
        passwords.append(self._password_for_workspace(workspace_id))
        for pwd in passwords:
            zf.setpassword(pwd)
            try:
                return json.loads(zf.read(section_name).decode("utf-8"))
            except RuntimeError:
                continue
        return None

    def _read_json_section(
        self,
        zf: pyzipper.AESZipFile,
        section_name: str,
        workspace_id: str,
        recovery_key: str | None,
    ):
        data = self._read_bytes_entry(zf, section_name, workspace_id, recovery_key)
        return json.loads(data.decode("utf-8"))

    def _read_bytes_entry(
        self,
        zf: pyzipper.AESZipFile,
        entry_name: str,
        workspace_id: str,
        recovery_key: str | None,
    ) -> bytes:
        passwords: list[bytes] = []
        if recovery_key:
            passwords.append(self._password_for_recovery_key(recovery_key))
        passwords.append(self._password_for_workspace(workspace_id))
        for pwd in passwords:
            zf.setpassword(pwd)
            try:
                return zf.read(entry_name)
            except RuntimeError:
                continue
        raise RuntimeError("Unable to read backup entry.")

    def _validate_manifest_sections_and_checksums(self, *, zf: pyzipper.AESZipFile, manifest: dict) -> dict | None:
        missing_fields = sorted(list(REQUIRED_MANIFEST_FIELDS - set(manifest.keys())))
        if missing_fields:
            return {
                "error_code": "manifest_fields_missing",
                "message": f"Manifest missing required fields: {', '.join(missing_fields)}.",
            }

        included_sections = set(manifest.get("included_sections") or [])
        missing_sections = sorted(list(REQUIRED_SECTIONS - included_sections))
        if missing_sections:
            return {
                "error_code": "required_sections_missing",
                "message": f"Required backup sections missing: {', '.join(missing_sections)}.",
            }

        return self._validate_checksum_entries(zf=zf, manifest=manifest)

    def _validate_checksum_entries(self, *, zf: pyzipper.AESZipFile, manifest: dict) -> dict | None:
        checksum_meta = manifest.get("checksum_metadata") or {}
        entries = checksum_meta.get("entries") or {}
        for filename, expected in entries.items():
            try:
                payload = zf.read(filename)
            except Exception:
                return {
                    "error_code": "section_missing",
                    "message": f"Section {filename} is missing from backup.",
                }
            actual = hashlib.sha256(payload).hexdigest()
            if actual != expected:
                return {
                    "error_code": "checksum_mismatch",
                    "message": f"Checksum mismatch for {filename}.",
                }
        return None

    async def verify_recovery_key(self, workspace_id: str, recovery_key: str, db: AsyncSession) -> bool:
        ws_sec = (
            await db.execute(
                select(WorkspaceSecurity).where(WorkspaceSecurity.workspace_id == workspace_id)
            )
        ).scalar_one_or_none()
        if not ws_sec or not ws_sec.recovery_key_hash:
            return False
        normalized = normalize_recovery_key(recovery_key)
        return bcrypt.checkpw(normalized.encode("utf-8"), ws_sec.recovery_key_hash.encode("utf-8"))

    async def log_recovery_key_verification(
        self,
        *,
        db: AsyncSession,
        workspace_id: str,
        success: bool,
        actor: str = "user",
    ) -> None:
        log = AuditLog(
            workspace_id=workspace_id,
            action="recovery_key_verify_success" if success else "recovery_key_verify_failure",
            actor=actor,
            note="Recovery key verification succeeded." if success else "Recovery key verification failed.",
        )
        db.add(log)
        await db.commit()

    @staticmethod
    def _row_to_dict(obj) -> dict:
        result = {}
        for col in obj.__table__.columns:
            value = getattr(obj, col.name)
            if isinstance(value, datetime):
                result[col.name] = value.isoformat()
            else:
                result[col.name] = value
        return result

    @staticmethod
    def _json_bytes(payload) -> bytes:
        return json.dumps(payload, ensure_ascii=True, default=str).encode("utf-8")

    @staticmethod
    def _manifest_summary(manifest: dict) -> dict:
        return {
            "backup_format_version": manifest.get("backup_format_version"),
            "backup_id": manifest.get("backup_id"),
            "workspace_id": manifest.get("workspace_id"),
            "financial_year": manifest.get("financial_year"),
            "created_at": manifest.get("created_at"),
            "encryption_mode": manifest.get("encryption_mode"),
            "included_sections": manifest.get("included_sections", []),
            "record_counts": manifest.get("record_counts", {}),
        }
