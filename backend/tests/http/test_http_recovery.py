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


@pytest.mark.asyncio
async def test_recovery_safety_status_missing_when_no_backup(auth_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    response = await auth_client.get("/api/v1/recovery/safety-status")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "missing"
    assert data["requires_backup_before_dangerous_action"] is True
    assert data["policy_window_hours"] == 24


@pytest.mark.asyncio
async def test_recovery_safety_status_healthy_after_verified_backup(auth_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    backup = await auth_client.post("/api/v1/recovery/backups")
    assert backup.status_code == 200, backup.text

    response = await auth_client.get("/api/v1/recovery/safety-status")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "healthy"
    assert data["last_backup_at"]
    assert data["last_verified_at"]
    assert data["requires_backup_before_dangerous_action"] is False


@pytest.mark.asyncio
async def test_restore_apply_success_end_to_end(auth_client, test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "documents"))

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = TaxEvent(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            event_type="deduction",
            category="donation",
            description="Original donation",
            amount=25.0,
            status="confirmed",
        )
        session.add(event)
        await session.commit()

    create = await auth_client.post("/api/v1/recovery/backups")
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    async with maker() as session:
        event = (await session.execute(select(TaxEvent).where(TaxEvent.workspace_id == auth_client.workspace_id))).scalar_one()
        event.description = "Mutated donation"
        event.amount = 99.0
        await session.commit()

    restore = await auth_client.post(
        "/api/v1/recovery/restore/apply",
        json={"backup_id": backup_id, "conflict_policy": "replace_current_workspace"},
    )
    assert restore.status_code == 200, restore.text
    body = restore.json()["data"]
    assert body["status"] == "ok"
    assert body["restored_workspace_id"] == auth_client.workspace_id
    assert body["checkpoint_id"]
    assert body["rollback_performed"] is False
    assert body["verification_result"]["ok"] is True

    async with maker() as session:
        restored = (await session.execute(select(TaxEvent).where(TaxEvent.workspace_id == auth_client.workspace_id))).scalar_one()
        assert restored.description == "Original donation"
        assert restored.amount == 25.0


@pytest.mark.asyncio
async def test_restore_apply_recovery_key_derived_success(auth_client, test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    create = await auth_client.post(
        "/api/v1/recovery/backups",
        json={"encryption_mode": "recovery_key_derived", "recovery_key": auth_client.recovery_key},
    )
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    restore = await auth_client.post(
        "/api/v1/recovery/restore/apply",
        json={
            "backup_id": backup_id,
            "recovery_key": auth_client.recovery_key,
            "conflict_policy": "replace_current_workspace",
        },
    )
    assert restore.status_code == 200, restore.text
    assert restore.json()["data"]["verification_result"]["ok"] is True


@pytest.mark.asyncio
async def test_restore_apply_recovery_key_derived_wrong_key_fails_before_mutation(auth_client, test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    create = await auth_client.post(
        "/api/v1/recovery/backups",
        json={"encryption_mode": "recovery_key_derived", "recovery_key": auth_client.recovery_key},
    )
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        before_count = (await session.execute(select(func.count()).select_from(TaxEvent))).scalar_one()

    restore = await auth_client.post(
        "/api/v1/recovery/restore/apply",
        json={"backup_id": backup_id, "recovery_key": "WRONG-RECOVERY-KEY", "conflict_policy": "replace_current_workspace"},
    )
    assert restore.status_code == 422, restore.text
    assert "WRONG-RECOVERY-KEY" not in restore.text

    async with maker() as session:
        after_count = (await session.execute(select(func.count()).select_from(TaxEvent))).scalar_one()
    assert after_count == before_count


@pytest.mark.asyncio
async def test_restore_apply_corrupt_payload_fails_before_mutation(auth_client, test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    create = await auth_client.post("/api/v1/recovery/backups")
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]
    backup_path = tmp_path / "backups" / auth_client.workspace_id / f"{backup_id}.trb"
    with open(backup_path, "rb") as f:
        payload = f.read()
    with open(backup_path, "wb") as f:
        f.write(payload[:32])

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        before_count = (await session.execute(select(func.count()).select_from(TaxEvent))).scalar_one()

    restore = await auth_client.post(
        "/api/v1/recovery/restore/apply",
        json={"backup_id": backup_id, "conflict_policy": "replace_current_workspace"},
    )
    assert restore.status_code == 422, restore.text

    async with maker() as session:
        after_count = (await session.execute(select(func.count()).select_from(TaxEvent))).scalar_one()
    assert after_count == before_count


@pytest.mark.asyncio
async def test_restore_apply_simulated_failure_rolls_back(auth_client, test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            TaxEvent(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                event_type="income",
                category="bank_interest",
                description="Pre restore event",
                amount=12.0,
            )
        )
        await session.commit()

    create = await auth_client.post("/api/v1/recovery/backups")
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    async with maker() as session:
        event = (await session.execute(select(TaxEvent).where(TaxEvent.workspace_id == auth_client.workspace_id))).scalar_one()
        event.description = "Current event that must survive failed restore"
        await session.commit()

    async def fail_after_apply(self, workspace_id, db):
        raise RuntimeError("forced restore verification failure")

    monkeypatch.setattr(RecoveryService, "_verify_restored_workspace", fail_after_apply)
    restore = await auth_client.post(
        "/api/v1/recovery/restore/apply",
        json={"backup_id": backup_id, "conflict_policy": "replace_current_workspace"},
    )
    assert restore.status_code == 422, restore.text
    data = restore.json()["detail"].get("data") or {}
    assert data.get("rollback_performed") is True

    async with maker() as session:
        event = (await session.execute(select(TaxEvent).where(TaxEvent.workspace_id == auth_client.workspace_id))).scalar_one()
        assert event.description == "Current event that must survive failed restore"


@pytest.mark.asyncio
async def test_restore_apply_restores_document_binary_to_current_storage(auth_client, test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "storage-a"))

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    storage_key = f"{auth_client.workspace_id}/doc-restore/original.pdf"
    os.makedirs(tmp_path / "storage-a" / auth_client.workspace_id / "doc-restore", exist_ok=True)
    with open(tmp_path / "storage-a" / storage_key, "wb") as f:
        f.write(b"ORIGINAL-PDF")

    async with maker() as session:
        session.add(
            Document(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                original_filename="original.pdf",
                storage_key=storage_key,
                file_type="application/pdf",
                file_size_bytes=12,
                sha256_hash="cd" * 32,
                status="ready",
                archived=False,
            )
        )
        await session.commit()

    create = await auth_client.post("/api/v1/recovery/backups")
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "storage-b"))
    restore = await auth_client.post(
        "/api/v1/recovery/restore/apply",
        json={"backup_id": backup_id, "conflict_policy": "replace_current_workspace"},
    )
    assert restore.status_code == 200, restore.text
    restored_path = tmp_path / "storage-b" / storage_key
    assert restored_path.exists()
    assert restored_path.read_bytes() == b"ORIGINAL-PDF"


@pytest.mark.asyncio
async def test_restore_apply_writes_audit_events(auth_client, test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    create = await auth_client.post("/api/v1/recovery/backups")
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    restore = await auth_client.post(
        "/api/v1/recovery/restore/apply",
        json={"backup_id": backup_id, "conflict_policy": "replace_current_workspace"},
    )
    assert restore.status_code == 200, restore.text

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        actions = {
            row.action
            for row in (
                await session.execute(select(AuditLog).where(AuditLog.workspace_id == auth_client.workspace_id))
            ).scalars().all()
        }
    assert "restore_apply_started" in actions
    assert "restore_apply_success" in actions


@pytest.mark.asyncio
async def test_restore_apply_runs_post_restore_reconcile_and_refreshes_downstream_state(auth_client, test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            TaxProfile(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                has_private_health=True,
            )
        )
        session.add(
            TaxEvent(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                event_type="income",
                category="bank_interest",
                description="Interest",
                amount=10.0,
                status="confirmed",
            )
        )
        await session.commit()

    create = await auth_client.post("/api/v1/recovery/backups")
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    restore = await auth_client.post(
        "/api/v1/recovery/restore/apply",
        json={"backup_id": backup_id, "conflict_policy": "replace_current_workspace"},
    )
    assert restore.status_code == 200, restore.text
    post = restore.json()["data"]["post_restore_reconcile"]
    assert post["status"] == "success"
    assert post["evidence_reconciled"] is True
    assert post["readiness_refreshed"] is True

    obligations = await auth_client.get("/api/v1/evidence/obligations")
    assert obligations.status_code == 200, obligations.text
    obligations_data = obligations.json()["data"]
    assert obligations_data["freshness"]["freshness_state"] == "fresh"
    assert obligations_data["freshness"]["trigger_source"] == "restore_apply"
    items = obligations_data["obligations"]
    assert any(item["obligation_key"] == "private_health_annual_statement" for item in items)
    assert all("explanation" in item for item in items)

    readiness = await auth_client.get("/api/v1/readiness")
    assert readiness.status_code == 200, readiness.text
    readiness_data = readiness.json()["data"]
    assert readiness_data["evidence_obligation_summary"]["total_obligations"] >= 1
    assert readiness_data["evidence_freshness"]["freshness_state"] == "fresh"
    assert readiness_data["evidence_freshness"]["trigger_source"] == "restore_apply"

    eligibility = await auth_client.get("/api/v1/export/eligibility")
    assert eligibility.status_code == 200, eligibility.text
    eligibility_data = eligibility.json()["data"]
    assert eligibility_data["eligibility_preview"]["evidence_total"] >= 1
    assert eligibility_data["evidence_freshness"]["freshness_state"] == "fresh"
    assert eligibility_data["evidence_freshness"]["trigger_source"] == "restore_apply"


@pytest.mark.asyncio
async def test_restore_apply_post_restore_reconcile_failure_reports_warning_without_rollback(auth_client, test_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_PATH", str(tmp_path / "backups"))

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            TaxEvent(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                event_type="deduction",
                category="donation",
                description="Restored donation",
                amount=25.0,
                status="confirmed",
            )
        )
        await session.commit()

    create = await auth_client.post("/api/v1/recovery/backups")
    assert create.status_code == 200, create.text
    backup_id = create.json()["data"]["backup_id"]

    from app.services.evidence_reconcile import EvidenceReconcileService

    async def fail_reconcile(self, **kwargs):
        return {"status": "failed", "reason": "forced_failure"}

    monkeypatch.setattr(EvidenceReconcileService, "trigger", fail_reconcile)
    restore = await auth_client.post(
        "/api/v1/recovery/restore/apply",
        json={"backup_id": backup_id, "conflict_policy": "replace_current_workspace"},
    )
    assert restore.status_code == 200, restore.text
    body = restore.json()["data"]
    assert body["status"] == "ok"
    assert body["rollback_performed"] is False
    assert body["post_restore_reconcile"]["status"] == "failed"
    assert body["post_restore_reconcile"]["evidence_reconciled"] is False

    async with maker() as session:
        restored = (
            await session.execute(
                select(TaxEvent).where(
                    TaxEvent.workspace_id == auth_client.workspace_id,
                    TaxEvent.description == "Restored donation",
                )
            )
        ).scalar_one_or_none()
        assert restored is not None
        actions = {
            row.action
            for row in (
                await session.execute(select(AuditLog).where(AuditLog.workspace_id == auth_client.workspace_id))
            ).scalars().all()
        }
    assert "restore_post_reconcile_started" in actions
    assert "restore_post_reconcile_failed" in actions
