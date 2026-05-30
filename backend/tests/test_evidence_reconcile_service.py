import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import TaxProfile, Workspace
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
