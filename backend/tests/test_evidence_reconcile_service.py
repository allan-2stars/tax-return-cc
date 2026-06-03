import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import TaxProfile, Workspace
from app.services.evidence_freshness import build_evidence_freshness
from app.services.evidence_reconcile import EvidenceReconcileService


@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def workspace(db_session):
    ws = Workspace(name="Reconcile Service WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest.mark.asyncio
async def test_trigger_debounce_skips_within_window_and_keeps_reconciled_at(db_session, workspace):
    db_session.add(
        TaxProfile(
            workspace_id=workspace.id,
            financial_year="2024-25",
            has_private_health=True,
        )
    )
    await db_session.commit()

    service = EvidenceReconcileService()
    first = await service.trigger(
        workspace_id=workspace.id,
        trigger_source="event_update",
        db=db_session,
    )
    assert first["status"] == "ok"
    assert first.get("skipped") is False

    ws = await db_session.scalar(select(Workspace).where(Workspace.id == workspace.id))
    first_reconciled_at = ws.evidence_reconciled_at
    assert first_reconciled_at is not None

    second = await service.trigger(
        workspace_id=workspace.id,
        trigger_source="event_update",
        db=db_session,
    )
    assert second["status"] == "ok"
    assert second.get("skipped") is True
    assert second.get("skip_reason") == "debounce_window"

    ws_after = await db_session.scalar(select(Workspace).where(Workspace.id == workspace.id))
    assert ws_after.evidence_reconciled_at == first_reconciled_at
    meta = ws_after.evidence_reconcile_meta or {}
    assert meta.get("skipped") is True
    assert meta.get("skip_reason") == "debounce_window"
    assert meta.get("debounce_window_seconds") == 3
    assert meta.get("previous_reconciled_at") is not None


@pytest.mark.asyncio
async def test_manual_force_bypasses_debounce(db_session, workspace):
    db_session.add(TaxProfile(workspace_id=workspace.id, financial_year="2024-25"))
    await db_session.commit()
    service = EvidenceReconcileService()

    await service.trigger(
        workspace_id=workspace.id,
        trigger_source="event_update",
        db=db_session,
        force=False,
    )
    forced = await service.trigger(
        workspace_id=workspace.id,
        trigger_source="manual_reconcile",
        db=db_session,
        force=True,
    )
    assert forced["status"] == "ok"
    assert forced.get("skipped") is False


def test_evidence_freshness_stale_state_for_never_reconciled_workspace():
    ws = Workspace(name="Freshness WS", financial_year="2024-25", status="active")

    freshness = build_evidence_freshness(ws)

    assert freshness["freshness_state"] == "stale"
    assert freshness["last_reconciled_at"] is None
    assert freshness["last_attempted_at"] is None
    assert freshness["last_failure_at"] is None
    assert "not been checked" in freshness["freshness_reason"].lower()


def test_evidence_freshness_fresh_state_for_successful_reconcile():
    now = datetime.now(timezone.utc)
    ws = Workspace(
        name="Freshness WS",
        financial_year="2024-25",
        status="active",
        evidence_reconciled_at=now,
        evidence_reconcile_status="succeeded",
        evidence_reconcile_meta={"last_completed_at": now.isoformat()},
    )

    freshness = build_evidence_freshness(ws)

    assert freshness["freshness_state"] == "fresh"
    assert freshness["last_reconciled_at"] == now.isoformat()
    assert freshness["last_attempted_at"] == now.isoformat()
    assert freshness["last_failure_at"] is None


def test_evidence_freshness_reconciling_state_for_running_reconcile():
    now = datetime.now(timezone.utc)
    ws = Workspace(
        name="Freshness WS",
        financial_year="2024-25",
        status="active",
        evidence_reconcile_status="running",
        evidence_reconcile_meta={"last_started_at": now.isoformat(), "last_trigger_source": "document_upload"},
    )

    freshness = build_evidence_freshness(ws)

    assert freshness["freshness_state"] == "reconciling"
    assert freshness["last_attempted_at"] == now.isoformat()
    assert freshness["trigger_source"] == "document_upload"


def test_evidence_freshness_failed_state_for_failed_reconcile():
    now = datetime.now(timezone.utc)
    ws = Workspace(
        name="Freshness WS",
        financial_year="2024-25",
        status="active",
        evidence_reconcile_status="failed",
        evidence_reconcile_meta={"last_failed_at": now.isoformat()},
    )

    freshness = build_evidence_freshness(ws)

    assert freshness["freshness_state"] == "failed"
    assert freshness["last_failure_at"] == now.isoformat()
    assert "could not be refreshed" in freshness["freshness_reason"].lower()
