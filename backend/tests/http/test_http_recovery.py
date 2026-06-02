import os

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
)
from app.services.recovery import RecoveryService


@pytest.mark.asyncio
async def test_create_backup_and_verify_success(auth_client, test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "documents"))

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            TaxProfile(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                has_wfh=True,
            )
        )
        event = TaxEvent(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            event_type="deduction",
            category="work_expense",
            description="Work expense",
            amount=50.0,
            status="confirmed",
        )
        session.add(event)
        await session.flush()
        session.add(
            ReviewItem(
                workspace_id=auth_client.workspace_id,
                tax_event_id=event.id,
                title="Review work expense",
                category="work_expense",
                amount=50.0,
                status="needs_user_review",
                questions_complete=True,
            )
        )
        session.add(
            InterviewSession(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                state="awaiting_evidence",
                answers={"residency": "resident"},
            )
        )
        obligation = EvidenceObligation(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            source_type="tax_event",
            obligation_key="work_expense_receipt",
            category="work_expense",
            label="Work expense receipt",
            required_level="required",
            status="missing",
            rule_version="2026.1",
        )
        session.add(obligation)
        await session.flush()
        session.add(
            EvidenceMatch(
                workspace_id=auth_client.workspace_id,
                obligation_id=obligation.id,
                match_type="tax_event",
                tax_event_id=event.id,
                status="candidate",
                confidence=0.8,
            )
        )
        doc = Document(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            original_filename="receipt.pdf",
            storage_key=f"{auth_client.workspace_id}/doc-1/original.pdf",
            file_type="application/pdf",
            file_size_bytes=8,
            sha256_hash="ab" * 32,
            status="ready",
            archived=False,
        )
        session.add(doc)
        await session.commit()

    os.makedirs(os.path.join(settings.STORAGE_PATH, auth_client.workspace_id, "doc-1"), exist_ok=True)
    with open(os.path.join(settings.STORAGE_PATH, auth_client.workspace_id, "doc-1", "original.pdf"), "wb") as f:
        f.write(b"PDFBYTES")

    response = await auth_client.post("/api/v1/recovery/backups")
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["status"] == "ok"
    assert body["backup_id"]
    assert body["filename"].endswith(".trb")
    assert body["manifest_summary"]["workspace_id"] == auth_client.workspace_id
    assert body["verification"]["ok"] is True

    verify = await auth_client.post("/api/v1/recovery/backups/verify", json={"backup_id": body["backup_id"]})
    assert verify.status_code == 200, verify.text
    verify_body = verify.json()["data"]
    assert verify_body["status"] == "ok"
    assert verify_body["verification"]["ok"] is True
    assert verify_body["manifest_summary"]["encryption_mode"] == "server_derived"


@pytest.mark.asyncio
async def test_verify_fails_for_tampered_backup(auth_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    create = await auth_client.post("/api/v1/recovery/backups")
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]
    backup_path = tmp_path / "backups" / auth_client.workspace_id / f"{backup_id}.trb"

    with open(backup_path, "rb") as f:
        payload = f.read()
    # Corrupt the encrypted artifact by truncating it.
    with open(backup_path, "wb") as f:
        f.write(payload[: len(payload) // 2])

    verify = await auth_client.post("/api/v1/recovery/backups/verify", json={"backup_id": backup_id})
    assert verify.status_code == 422


@pytest.mark.asyncio
async def test_failed_backup_leaves_no_finalized_artifact(auth_client, test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    original_collect = RecoveryService._collect_bundle

    async def _boom(self, workspace, db, created_at, backup_id, **kwargs):
        raise ValueError("forced failure")

    monkeypatch.setattr(RecoveryService, "_collect_bundle", _boom)
    response = await auth_client.post("/api/v1/recovery/backups")
    assert response.status_code == 422

    ws_dir = tmp_path / "backups" / auth_client.workspace_id
    if ws_dir.exists():
        assert list(ws_dir.glob("*.trb")) == []
        assert list(ws_dir.glob("*.tmp")) == []

    monkeypatch.setattr(RecoveryService, "_collect_bundle", original_collect)


@pytest.mark.asyncio
async def test_backup_verify_is_workspace_scoped(auth_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    create = await auth_client.post("/api/v1/recovery/backups")
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    create_ws = await auth_client.post(
        "/api/v1/workspaces",
        json={"name": "Other Workspace", "financial_year": "2025-26"},
    )
    assert create_ws.status_code == 200, create_ws.text

    verify = await auth_client.post("/api/v1/recovery/backups/verify", json={"backup_id": backup_id})
    assert verify.status_code == 404


@pytest.mark.asyncio
async def test_recovery_key_verify_success_and_audit(auth_client, test_engine):
    response = await auth_client.post(
        "/api/v1/recovery/key/verify",
        json={"recovery_key": auth_client.recovery_key},
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["verified"] is True
    assert body["status"] == "ok"
    assert body.get("verified_at")

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        logs = (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.workspace_id == auth_client.workspace_id,
                    AuditLog.action == "recovery_key_verify_success",
                )
            )
        ).scalars().all()
        assert len(logs) >= 1


@pytest.mark.asyncio
async def test_restore_preview_valid_server_derived_backup(auth_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    create = await auth_client.post("/api/v1/recovery/backups")
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    preview = await auth_client.post(
        "/api/v1/recovery/restore/preview",
        json={"backup_id": backup_id},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()["data"]
    assert body["status"] == "ok"
    assert body["backup_id"] == backup_id
    assert body["encryption_mode"] == "server_derived"
    assert body["can_restore"] is False
    assert "workspace with the same id already exists" in " ".join(body["blockers"]).lower()


@pytest.mark.asyncio
async def test_restore_preview_valid_recovery_key_derived_backup(auth_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    create = await auth_client.post(
        "/api/v1/recovery/backups",
        json={"encryption_mode": "recovery_key_derived", "recovery_key": auth_client.recovery_key},
    )
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    preview = await auth_client.post(
        "/api/v1/recovery/restore/preview",
        json={"backup_id": backup_id, "recovery_key": auth_client.recovery_key},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()["data"]
    assert body["backup_id"] == backup_id
    assert body["encryption_mode"] == "recovery_key_derived"
    assert "format version is compatible" in " ".join(body["compatibility"]["notes"]).lower()


@pytest.mark.asyncio
async def test_restore_preview_recovery_key_derived_wrong_key_fails_safely(auth_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    create = await auth_client.post(
        "/api/v1/recovery/backups",
        json={"encryption_mode": "recovery_key_derived", "recovery_key": auth_client.recovery_key},
    )
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    preview = await auth_client.post(
        "/api/v1/recovery/restore/preview",
        json={"backup_id": backup_id, "recovery_key": "WRONG-RECOVERY-KEY"},
    )
    assert preview.status_code == 422, preview.text
    detail = preview.json()["detail"]
    assert detail["error_code"] in {"decrypt_failed", "backup_invalid"}
    assert "WRONG-RECOVERY-KEY" not in preview.text


@pytest.mark.asyncio
async def test_restore_preview_corrupt_backup_fails_safely(auth_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    create = await auth_client.post("/api/v1/recovery/backups")
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]
    backup_path = tmp_path / "backups" / auth_client.workspace_id / f"{backup_id}.trb"

    with open(backup_path, "rb") as f:
        payload = f.read()
    with open(backup_path, "wb") as f:
        f.write(payload[:32])

    preview = await auth_client.post(
        "/api/v1/recovery/restore/preview",
        json={"backup_id": backup_id},
    )
    assert preview.status_code == 422, preview.text


@pytest.mark.asyncio
async def test_restore_preview_does_not_mutate_workspace_state(auth_client, test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    create = await auth_client.post("/api/v1/recovery/backups")
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        before_count = (
            await session.execute(select(func.count()).select_from(TaxEvent))
        ).scalar_one()

    preview = await auth_client.post(
        "/api/v1/recovery/restore/preview",
        json={"backup_id": backup_id},
    )
    assert preview.status_code == 200, preview.text

    async with maker() as session:
        after_count = (
            await session.execute(select(func.count()).select_from(TaxEvent))
        ).scalar_one()
    assert after_count == before_count


@pytest.mark.asyncio
async def test_recovery_key_verify_failure_safe_error_and_audit(auth_client, test_engine):
    response = await auth_client.post(
        "/api/v1/recovery/key/verify",
        json={"recovery_key": "WRONG-RECOVERY-KEY"},
    )
    assert response.status_code == 401, response.text
    detail = response.json()["detail"]
    assert detail["error_code"] == "invalid_recovery_key"
    assert "failed" in detail["message"].lower()
    assert "WRONG-RECOVERY-KEY" not in response.text

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        logs = (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.workspace_id == auth_client.workspace_id,
                    AuditLog.action == "recovery_key_verify_failure",
                )
            )
        ).scalars().all()
        assert len(logs) >= 1
