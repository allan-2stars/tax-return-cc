"""
Tests for M10 Phase 6 — manual event creation and receipt attachment.
"""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from unittest.mock import patch

from app.db.models import TaxEvent, ReviewItem as ReviewItemModel, Workspace, TaxProfile, Document


@pytest_asyncio.fixture(autouse=True)
async def patch_async_session_local(test_engine, monkeypatch):
    import app.db.base as db_base
    test_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(db_base, "AsyncSessionLocal", test_maker)


@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def workspace(db_session):
    ws = Workspace(name="Events Test WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def existing_event(db_session, workspace):
    evt = TaxEvent(
        workspace_id=workspace.id,
        financial_year="2024-25",
        event_type="deduction",
        category="work_expense",
        description="Laptop stand",
        amount=89.00,
        date="2025-08-01",
        source="manual_entry",
        status="needs_user_review",
        risk_level="low",
    )
    db_session.add(evt)
    await db_session.commit()
    await db_session.refresh(evt)
    return evt


@pytest.mark.asyncio
async def test_create_manual_event_one_off_creates_tax_event_and_review_item(
    db_session, workspace
):
    """POST /events/manual (one-off) creates 1 TaxEvent + 1 ReviewItem."""
    import asyncio
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = asyncio.sleep(0)

        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="deduction",
            category="work_subscription",
            description="Spotify",
            amount=119.88,
            date="2025-09-01",
            frequency="one_off",
            note=None,
            periods=None,
            db=db_session,
        )

    assert len(events) == 1
    assert events[0].source == "manual_entry"
    assert events[0].description == "Spotify"
    assert events[0].amount == 119.88

    result = await db_session.execute(
        select(ReviewItemModel).where(ReviewItemModel.workspace_id == workspace.id)
    )
    items = result.scalars().all()
    assert len(items) == 1
    assert items[0].tax_event_id == events[0].id


@pytest.mark.asyncio
async def test_create_manual_event_monthly_creates_grouped_events(
    db_session, workspace
):
    """Monthly recurring with 2 periods creates 2 TaxEvents with same group_id."""
    import asyncio
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = asyncio.sleep(0)

        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="deduction",
            category="work_subscription",
            description="Surfshark VPN",
            amount=0,
            date="2025-07-01",
            frequency="monthly",
            note=None,
            periods=[
                {"months": 3, "amount_per_month": 17.0},
                {"months": 8, "amount_per_month": 20.0},
            ],
            db=db_session,
        )

    assert len(events) == 2
    assert events[0].group_id == events[1].group_id
    assert events[0].group_id is not None
    assert events[0].amount == 51.0   # 3 × 17.0
    assert events[1].amount == 160.0  # 8 × 20.0
    assert all(e.is_recurring for e in events)
    assert "2 periods" in events[0].group_display
    assert "$211.00 total" in events[0].group_display


@pytest.mark.asyncio
async def test_attach_receipt_links_document_no_new_event(
    db_session, workspace, existing_event
):
    """attach_receipt links a Document to an existing TaxEvent, no new event created."""
    import tempfile
    from app.engines.evidence import EvidenceEngine
    from app.storage.local import LocalStorageBackend

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageBackend(base_path=tmpdir)
        engine = EvidenceEngine(db=db_session, storage=storage)

        fake_pdf = b"%PDF-1.4 1 0 obj<</Type /Catalog>> endobj"

        doc = await engine.attach_receipt(
            event_id=existing_event.id,
            workspace_id=workspace.id,
            file_data=fake_pdf,
            filename="receipt.pdf",
        )

    assert doc.id is not None
    assert doc.workspace_id == workspace.id

    await db_session.refresh(existing_event)
    assert existing_event.document_id == doc.id

    result = await db_session.execute(
        select(TaxEvent).where(TaxEvent.workspace_id == workspace.id)
    )
    all_events = result.scalars().all()
    assert len(all_events) == 1


@pytest.mark.asyncio
async def test_create_manual_event_stores_metadata(db_session, workspace):
    """metadata dict is persisted on the TaxEvent."""
    import asyncio
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    meta = {"investment_sub_type": "shares", "transaction_type": "buy", "units": 100}

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = asyncio.sleep(0)
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="capital_gain",
            description="Shares Buy: 100 × CBA @ $82.50",
            amount=8259.95,
            date="2025-08-15",
            frequency="one_off",
            note=None,
            periods=None,
            metadata=meta,
            db=db_session,
        )

    assert events[0].event_metadata == meta


@pytest.mark.asyncio
async def test_create_manual_event_needs_agent_review_sets_status_on_event_and_review_item(
    db_session, workspace
):
    """review_status='needs_agent_review' propagates to TaxEvent and ReviewItem."""
    import asyncio
    from app.engines.review import ReviewEngine
    from sqlalchemy import select
    from app.db.models import ReviewItem as ReviewItemModel

    engine = ReviewEngine()

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = asyncio.sleep(0)
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="foreign_income",
            description="US Dividends",
            amount=500.0,
            date="2025-03-01",
            frequency="one_off",
            note=None,
            periods=None,
            metadata={"investment_sub_type": "foreign_income"},
            review_status="needs_agent_review",
            db=db_session,
        )

    assert events[0].status == "needs_agent_review"
    assert events[0].risk_level == "high"

    result = await db_session.execute(
        select(ReviewItemModel).where(ReviewItemModel.tax_event_id == events[0].id)
    )
    item = result.scalar_one()
    assert item.status == "needs_agent_review"
