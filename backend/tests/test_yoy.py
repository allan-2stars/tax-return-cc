"""
Tests for M9 Year-over-Year Suggestions Engine — TDD.
"""
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import TaxEvent, Workspace, YoySuggestion


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def workspace_current(db_session):
    ws = Workspace(name="Current FY", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def workspace_prev(db_session):
    ws = Workspace(name="Previous FY", financial_year="2023-24", status="archived")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


# ── helpers ───────────────────────────────────────────────────────────────────

async def _create_event(
    db,
    workspace_id: str,
    event_type: str = "deduction",
    category: str = "work_expense",
    status: str = "confirmed",
    amount: float = 500.0,
    description: str = "Test deduction",
) -> TaxEvent:
    ev = TaxEvent(
        workspace_id=workspace_id,
        financial_year="2024-25",
        event_type=event_type,
        category=category,
        description=description,
        amount=amount,
        status=status,
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


async def _create_suggestion(
    db,
    workspace_id: str,
    source_workspace_id: str,
    category: str = "work_expense",
    status: str = "pending",
) -> YoySuggestion:
    s = YoySuggestion(
        workspace_id=workspace_id,
        source_workspace_id=source_workspace_id,
        financial_year="2024-25",
        category=category,
        description="Test suggestion",
        amount_last_year=500.0,
        status=status,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


# ── 1. returns deduction events from previous FY workspace ───────────────────

@pytest.mark.asyncio
async def test_generate_suggestions_returns_deduction_events(
    workspace_current, workspace_prev, db_session
):
    from app.engines.yoy import YoYEngine

    await _create_event(
        db_session, workspace_prev.id,
        event_type="deduction", category="work_expense",
        status="confirmed", amount=350.0,
    )

    engine = YoYEngine()
    suggestions = await engine.generate_suggestions(workspace_current.id, db_session)

    assert len(suggestions) == 1
    assert suggestions[0].category == "work_expense"
    assert suggestions[0].amount_last_year == 350.0
    assert suggestions[0].workspace_id == workspace_current.id
    assert suggestions[0].source_workspace_id == workspace_prev.id


# ── 2. excludes income events ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_suggestions_excludes_income_events(
    workspace_current, workspace_prev, db_session
):
    from app.engines.yoy import YoYEngine

    await _create_event(
        db_session, workspace_prev.id,
        event_type="income", category="payg_income",
        status="confirmed", amount=80000.0,
    )

    engine = YoYEngine()
    suggestions = await engine.generate_suggestions(workspace_current.id, db_session)

    assert len(suggestions) == 0


# ── 3. excludes items already in current FY ───────────────────────────────────

@pytest.mark.asyncio
async def test_generate_suggestions_excludes_items_already_in_current_fy(
    workspace_current, workspace_prev, db_session
):
    from app.engines.yoy import YoYEngine

    # Previous FY has a deduction
    await _create_event(
        db_session, workspace_prev.id,
        event_type="deduction", category="work_expense",
        status="confirmed",
    )

    # Current FY already has the same category
    await _create_event(
        db_session, workspace_current.id,
        event_type="deduction", category="work_expense",
        status="needs_user_review",
    )

    engine = YoYEngine()
    suggestions = await engine.generate_suggestions(workspace_current.id, db_session)

    assert len(suggestions) == 0


# ── 4. process_action("dismissed") updates suggestion status ─────────────────

@pytest.mark.asyncio
async def test_process_action_dismissed_updates_status(
    workspace_current, workspace_prev, db_session
):
    from app.engines.yoy import YoYEngine

    suggestion = await _create_suggestion(
        db_session, workspace_current.id, workspace_prev.id, status="pending"
    )

    engine = YoYEngine()
    updated = await engine.process_action(suggestion.id, "dismissed", db_session)

    assert updated.status == "dismissed"
    assert updated.actioned_at is not None
