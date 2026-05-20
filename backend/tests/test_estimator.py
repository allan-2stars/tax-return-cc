"""
Tests for M9 Tax Figure Summariser — TDD.
"""
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import TaxEvent, Workspace


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def workspace(db_session):
    ws = Workspace(name="Estimator Test WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


# ── helpers ───────────────────────────────────────────────────────────────────

async def _create_event(
    db,
    workspace_id: str,
    event_type: str = "income",
    category: str = "payg_income",
    amount: float = 0.0,
    status: str = "confirmed",
) -> TaxEvent:
    ev = TaxEvent(
        workspace_id=workspace_id,
        financial_year="2024-25",
        event_type=event_type,
        category=category,
        description="Test event",
        amount=amount,
        status=status,
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


# ── 1. sums only confirmed TaxEvents ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_summary_sums_only_confirmed_events(workspace, db_session):
    from app.engines.estimator import TaxEstimator

    await _create_event(db_session, workspace.id, event_type="income", category="payg_income", amount=80000.0, status="confirmed")
    await _create_event(db_session, workspace.id, event_type="deduction", category="work_expense", amount=5000.0, status="confirmed")
    await _create_event(db_session, workspace.id, event_type="income", category="payg_income", amount=10000.0, status="needs_user_review")

    estimator = TaxEstimator()
    summary = await estimator.get_summary(workspace.id, db_session)

    assert summary.gross_income == Decimal("80000")
    assert summary.total_deductions == Decimal("5000")
    assert summary.taxable_income == Decimal("75000")
    assert summary.confirmed_only is True


# ── 2. pending_count reflects non-confirmed items ─────────────────────────────

@pytest.mark.asyncio
async def test_get_summary_pending_count_reflects_unconfirmed_events(workspace, db_session):
    from app.engines.estimator import TaxEstimator

    await _create_event(db_session, workspace.id, amount=50000.0, status="confirmed")
    await _create_event(db_session, workspace.id, amount=1000.0, status="needs_user_review")
    await _create_event(db_session, workspace.id, amount=2000.0, status="needs_agent_review")

    estimator = TaxEstimator()
    summary = await estimator.get_summary(workspace.id, db_session)

    assert summary.pending_count == 2


# ── 3. always includes ato_calculator_url ─────────────────────────────────────

@pytest.mark.asyncio
async def test_get_summary_always_includes_ato_calculator_url(workspace, db_session):
    from app.engines.estimator import TaxEstimator

    estimator = TaxEstimator()
    summary = await estimator.get_summary(workspace.id, db_session)

    assert summary.ato_calculator_url == "https://www.ato.gov.au/calculators-and-tools"


# ── 4. always includes disclaimer text ───────────────────────────────────────

@pytest.mark.asyncio
async def test_get_summary_always_includes_disclaimer(workspace, db_session):
    from app.engines.estimator import TaxEstimator

    estimator = TaxEstimator()
    summary = await estimator.get_summary(workspace.id, db_session)

    assert summary.disclaimer
    assert "confirmed" in summary.disclaimer.lower()
    assert "tax agent" in summary.disclaimer.lower()
