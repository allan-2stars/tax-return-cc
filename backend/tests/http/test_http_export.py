"""HTTP smoke tests for /export route group."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest.mark.asyncio
async def test_eligibility_blocked(auth_client):
    """GET /export/eligibility returns can_export=False for fresh workspace (no interview)."""
    resp = await auth_client.get("/api/v1/export/eligibility")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["can_export"] is False
    assert len(body["data"]["blocking_reasons"]) > 0
    assert "eligibility_preview" in body["data"]
    status = body["data"]["evidence_export_status"]
    assert status["mode"] == "soft_block"
    assert isinstance(status["would_block_export"], bool)
    assert "message" in status


@pytest.mark.asyncio
async def test_eligibility_ready(eligible_client):
    """GET /export/eligibility returns can_export=True when interview complete + confirmed event."""
    resp = await eligible_client.get("/api/v1/export/eligibility")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["can_export"] is True
    preview = body["data"]["eligibility_preview"]
    assert isinstance(preview["would_block_export"], bool)
    assert "evidence_required_total" in preview
    assert "evidence_required_matched_total" in preview
    assert "evidence_recommended_missing_total" in preview
    status = body["data"]["evidence_export_status"]
    assert status["mode"] == "soft_block"
    assert status["would_block_export"] is False
    assert "satisfied" in status["message"].lower()
    assert "evidence_required_missing_count" in body["data"]
    assert "evidence_required_partial_count" in body["data"]
    assert "evidence_required_matched_count" in body["data"]
    assert "evidence_recommended_missing_count" in body["data"]


@pytest.mark.asyncio
async def test_generate(eligible_client):
    """POST /export/generate returns 200 with export_id when eligible."""
    resp = await eligible_client.post(
        "/api/v1/export/generate",
        json={"password": "export-test-password"},
    )
    # Route always returns 200 — export runs as background task, failures update DB record
    assert resp.status_code == 200
    assert "export_id" in resp.json()["data"]


@pytest.mark.asyncio
async def test_export_history(auth_client):
    """GET /export/history returns 200 with a list."""
    resp = await auth_client.get("/api/v1/export/history")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)


@pytest.mark.asyncio
async def test_status_lazily_marks_stale_generating_export_failed(auth_client, test_engine):
    """GET /export/{id}/status marks stale generating exports as failed."""
    from app.db.models import ExportRecord

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    stale_created = datetime.now(timezone.utc) - timedelta(seconds=700)
    async with maker() as session:
        record = ExportRecord(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            status="generating",
            created_at=stale_created,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)

    resp = await auth_client.get(f"/api/v1/export/{record.id}/status")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "failed"


@pytest.mark.asyncio
async def test_status_includes_safe_error_message_for_interrupted_export(auth_client, test_engine):
    """GET /export/{id}/status includes safe error_message for failed exports."""
    from app.db.models import BackgroundJob, ExportRecord

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        record = ExportRecord(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            status="failed",
        )
        session.add(record)
        await session.flush()

        msg = "Export interrupted (server restart or worker shutdown). Please generate again."
        job = BackgroundJob(
            workspace_id=auth_client.workspace_id,
            job_type="export_generate",
            status="failed",
            payload={"export_id": record.id},
            error=msg,
        )
        session.add(job)
        await session.commit()

    resp = await auth_client.get(f"/api/v1/export/{record.id}/status")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert data["error_message"] == msg


@pytest.mark.asyncio
async def test_status_masks_arbitrary_job_errors(auth_client, test_engine):
    """GET /export/{id}/status masks arbitrary BackgroundJob.error strings."""
    from app.db.models import BackgroundJob, ExportRecord

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        record = ExportRecord(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            status="failed",
        )
        session.add(record)
        await session.flush()

        job = BackgroundJob(
            workspace_id=auth_client.workspace_id,
            job_type="export_generate",
            status="failed",
            payload={"export_id": record.id},
            error="Traceback: secrets and stack frames",
        )
        session.add(job)
        await session.commit()

    resp = await auth_client.get(f"/api/v1/export/{record.id}/status")
    assert resp.status_code == 200
    assert resp.json()["data"]["error_message"] == "Export failed. Please generate again."


@pytest.mark.asyncio
async def test_eligibility_includes_soft_block_when_required_evidence_incomplete(auth_client, test_engine):
    from app.db.models import EvidenceObligation
    from app.services.evidence_rules import CURRENT_EVIDENCE_RULE_VERSION

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            EvidenceObligation(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                source_type="profile",
                obligation_key="private_health_annual_statement",
                category="private_health",
                label="PHI",
                required_level="required",
                status="missing",
                rule_version=CURRENT_EVIDENCE_RULE_VERSION,
            )
        )
        await session.commit()

    resp = await auth_client.get("/api/v1/export/eligibility")
    assert resp.status_code == 200
    status = resp.json()["data"]["evidence_export_status"]
    assert status["mode"] == "soft_block"
    assert status["would_block_export"] is True
    assert status["missing_required_count"] == 1
    assert status["blocking_required_count"] >= 1
    assert "allowed for now" in status["message"].lower()
    assert status["blocking_evidence_obligations"][0]["rule_version"] == CURRENT_EVIDENCE_RULE_VERSION
    assert resp.json()["data"]["can_export"] is False  # still blocked by other hard blockers, not evidence


@pytest.mark.asyncio
async def test_eligibility_missing_evidence_does_not_block_export_when_other_checks_pass(eligible_client, test_engine):
    from app.db.models import EvidenceObligation

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            EvidenceObligation(
                workspace_id=eligible_client.workspace_id,
                financial_year="2024-25",
                source_type="tax_event",
                obligation_key="work_expense_receipt",
                category="work_expense",
                label="Work expense receipt",
                required_level="required",
                status="missing",
            )
        )
        await session.commit()

    resp = await eligible_client.get("/api/v1/export/eligibility")
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["can_export"] is True
    assert body["evidence_export_status"]["would_block_export"] is True
    assert body["evidence_required_missing_count"] >= 1
