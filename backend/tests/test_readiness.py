"""
Tests for M7 Tax Readiness Engine.

TDD — all 11 tests written before implementation.
Expected to fail until Tasks 2-4 complete.
"""
import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.models import (
    Workspace,
    TaxProfile,
    TaxEvent,
    SkillVersionLock,
    Document,
    ReadinessScore as ReadinessScoreModel,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

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
async def workspace_ended_fy(db_session):
    """financial_year=2024-25 — FY ended 2025-06-30, before today 2026-05-20."""
    ws = Workspace(name="Readiness Ended FY", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def workspace_active_fy(db_session):
    """financial_year=2025-26 — FY ends 2026-06-30, still active today 2026-05-20."""
    ws = Workspace(name="Readiness Active FY", financial_year="2025-26", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


# ── helpers ───────────────────────────────────────────────────────────────────

async def _create_profile(db_session, workspace_id: str, financial_year: str, **kwargs):
    profile = TaxProfile(
        workspace_id=workspace_id, financial_year=financial_year, **kwargs
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


async def _lock_employee_tax_au(db_session, workspace_id: str):
    lock = SkillVersionLock(
        workspace_id=workspace_id, skill_id="employee_tax_au", skill_version="1.0.0"
    )
    db_session.add(lock)
    await db_session.commit()


async def _create_event(
    db_session,
    workspace_id: str,
    financial_year: str,
    category: str,
    status: str,
    amount: float = 100.0,
):
    event = TaxEvent(
        workspace_id=workspace_id,
        financial_year=financial_year,
        event_type="income",
        category=category,
        description=f"Test {category}",
        amount=amount,
        status=status,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


# ── 1. calculate() returns 0% when no skills locked ──────────────────────────

@pytest.mark.asyncio
async def test_calculate_returns_zero_when_no_skills(workspace_ended_fy, db_session):
    from app.engines.readiness import ReadinessEngine

    await _create_profile(db_session, workspace_ended_fy.id, "2024-25")

    engine = ReadinessEngine()
    score = await engine.calculate(workspace_ended_fy.id, db_session)

    assert score.percentage == 0
    assert score.breakdown == []
    assert score.missing_items == []
    assert score.is_stale is False


# ── 2. calculate() returns 100% when all required evidence confirmed ──────────

@pytest.mark.asyncio
async def test_calculate_returns_100_when_all_required_evidence_confirmed(
    workspace_ended_fy, db_session
):
    from app.engines.readiness import ReadinessEngine

    # FY ended → all requirements in denominator
    # has_wfh=False → wfh_diary excluded; has_private_health=False → private_health excluded
    # Denominator: payg_summary(30) + bank_interest(10) + work_receipts(15) = 55
    await _create_profile(
        db_session, workspace_ended_fy.id, "2024-25",
        has_wfh=False, has_private_health=False,
    )
    await _lock_employee_tax_au(db_session, workspace_ended_fy.id)

    await _create_event(db_session, workspace_ended_fy.id, "2024-25", "payg_income", "confirmed")
    await _create_event(db_session, workspace_ended_fy.id, "2024-25", "bank_interest", "confirmed")
    await _create_event(db_session, workspace_ended_fy.id, "2024-25", "work_expense", "confirmed")

    engine = ReadinessEngine()
    score = await engine.calculate(workspace_ended_fy.id, db_session)

    assert score.percentage == 100
    assert score.is_stale is False


# ── 3. calculate() gives half weight to needs_review events ──────────────────

@pytest.mark.asyncio
async def test_calculate_half_weight_for_needs_review(workspace_ended_fy, db_session):
    from app.engines.readiness import ReadinessEngine

    # Denominator: payg_summary(30) + bank_interest(10) + work_receipts(15) = 55
    # payg_income → needs_user_review → 30 * 0.5 = 15
    # bank_interest → confirmed → 10
    # work_expense → confirmed → 15
    # achieved = 40; percentage = round(40/55*100) = round(72.72) = 73
    await _create_profile(
        db_session, workspace_ended_fy.id, "2024-25",
        has_wfh=False, has_private_health=False,
    )
    await _lock_employee_tax_au(db_session, workspace_ended_fy.id)

    await _create_event(db_session, workspace_ended_fy.id, "2024-25", "payg_income", "needs_user_review")
    await _create_event(db_session, workspace_ended_fy.id, "2024-25", "bank_interest", "confirmed")
    await _create_event(db_session, workspace_ended_fy.id, "2024-25", "work_expense", "confirmed")

    engine = ReadinessEngine()
    score = await engine.calculate(workspace_ended_fy.id, db_session)

    assert score.percentage == 73
    assert 0 < score.percentage < 100


# ── 4. calculate() excludes after_fy_end requirements during active FY ────────

@pytest.mark.asyncio
async def test_calculate_excludes_after_fy_end_requirements_during_active_fy(
    workspace_active_fy, db_session
):
    from app.engines.readiness import ReadinessEngine

    # FY 2025-26 is still active (ends 2026-06-30, today is 2026-05-20)
    # after_fy_end excluded: payg_summary(30), bank_interest(10)
    # condition excluded: wfh_diary(has_wfh=False), private_health(has_private_health=False)
    # Only in denominator: work_receipts(15)
    await _create_profile(
        db_session, workspace_active_fy.id, "2025-26",
        has_wfh=False, has_private_health=False,
    )
    await _lock_employee_tax_au(db_session, workspace_active_fy.id)

    # Confirm work_expense to get 100% on the reduced denominator
    await _create_event(db_session, workspace_active_fy.id, "2025-26", "work_expense", "confirmed")
    # Also add a confirmed payg_income — should NOT push score above 100%
    # (payg_summary requirement is excluded from denominator entirely)
    await _create_event(db_session, workspace_active_fy.id, "2025-26", "payg_income", "confirmed")

    engine = ReadinessEngine()
    score = await engine.calculate(workspace_active_fy.id, db_session)

    # If after_fy_end exclusion works: total=15, achieved=15, percentage=100
    # If payg_summary were included: total=55, achieved=45, percentage=82
    assert score.percentage == 100
    assert score.breakdown[0].total_weight == 15


# ── 5. calculate() excludes requirements when profile condition not met ────────

@pytest.mark.asyncio
async def test_calculate_excludes_requirements_when_condition_not_met(
    workspace_ended_fy, db_session
):
    from app.engines.readiness import ReadinessEngine

    # has_wfh=False → wfh_diary(15) excluded
    # has_private_health=False → private_health_statement(10) excluded
    # Denominator without those: 30+10+15=55 (not 30+10+15+15+10=80)
    await _create_profile(
        db_session, workspace_ended_fy.id, "2024-25",
        has_wfh=False, has_private_health=False,
    )
    await _lock_employee_tax_au(db_session, workspace_ended_fy.id)

    await _create_event(db_session, workspace_ended_fy.id, "2024-25", "payg_income", "confirmed")
    await _create_event(db_session, workspace_ended_fy.id, "2024-25", "bank_interest", "confirmed")
    await _create_event(db_session, workspace_ended_fy.id, "2024-25", "work_expense", "confirmed")

    engine = ReadinessEngine()
    score = await engine.calculate(workspace_ended_fy.id, db_session)

    # 100% proves wfh_diary was excluded (otherwise we'd need a wfh_deduction event too)
    assert score.percentage == 100
    assert score.breakdown[0].total_weight == 55


# ── 6. calculate() returns correct per-skill breakdown ────────────────────────

@pytest.mark.asyncio
async def test_calculate_returns_correct_per_skill_breakdown(workspace_ended_fy, db_session):
    from app.engines.readiness import ReadinessEngine

    await _create_profile(
        db_session, workspace_ended_fy.id, "2024-25",
        has_wfh=False, has_private_health=False,
    )
    await _lock_employee_tax_au(db_session, workspace_ended_fy.id)

    # Only confirm payg_income → achieved_weight = 30, total = 55
    await _create_event(db_session, workspace_ended_fy.id, "2024-25", "payg_income", "confirmed")

    engine = ReadinessEngine()
    score = await engine.calculate(workspace_ended_fy.id, db_session)

    assert len(score.breakdown) == 1
    bd = score.breakdown[0]
    assert bd.skill_id == "employee_tax_au"
    assert bd.total_weight == 55
    assert bd.achieved_weight == 30
    assert bd.percentage == round(30 / 55 * 100)   # 55


# ── 7. mark_stale() sets is_stale = True in DB ────────────────────────────────

@pytest.mark.asyncio
async def test_mark_stale_sets_is_stale_true(workspace_ended_fy, db_session):
    from app.engines.readiness import ReadinessEngine

    record = ReadinessScoreModel(
        workspace_id=workspace_ended_fy.id,
        financial_year="2024-25",
        percentage=50.0,
        is_stale=False,
    )
    db_session.add(record)
    await db_session.commit()

    engine = ReadinessEngine()
    await engine.mark_stale(workspace_ended_fy.id, db_session)

    await db_session.refresh(record)
    assert record.is_stale is True


# ── 8. recalculate() sets is_stale = False ────────────────────────────────────

@pytest.mark.asyncio
async def test_recalculate_sets_is_stale_false(workspace_ended_fy, db_session):
    from app.engines.readiness import ReadinessEngine
    from app.db.base import AsyncSessionLocal
    from sqlalchemy import select

    record = ReadinessScoreModel(
        workspace_id=workspace_ended_fy.id,
        financial_year="2024-25",
        percentage=0.0,
        is_stale=True,
    )
    db_session.add(record)
    await db_session.commit()
    await _create_profile(db_session, workspace_ended_fy.id, "2024-25")

    engine = ReadinessEngine()
    # recalculate opens its own AsyncSessionLocal session — call directly in tests
    await engine.recalculate(workspace_ended_fy.id)

    async with AsyncSessionLocal() as new_session:
        result = await new_session.execute(
            select(ReadinessScoreModel).where(
                ReadinessScoreModel.workspace_id == workspace_ended_fy.id
            )
        )
        updated = result.scalar_one_or_none()
        assert updated is not None
        assert updated.is_stale is False


# ── 9. get_missing_items() returns correct available_after_fy flag ────────────

@pytest.mark.asyncio
async def test_missing_items_have_correct_available_after_fy_flag(
    workspace_ended_fy, db_session
):
    from app.engines.readiness import ReadinessEngine

    await _create_profile(
        db_session, workspace_ended_fy.id, "2024-25",
        has_wfh=False, has_private_health=False,
    )
    await _lock_employee_tax_au(db_session, workspace_ended_fy.id)
    # No events → all requirements are missing

    engine = ReadinessEngine()
    missing = await engine.get_missing_items(workspace_ended_fy.id, db_session)

    req_ids = {m.requirement_id for m in missing}
    assert "payg_summary" in req_ids
    assert "work_receipts" in req_ids
    # wfh_diary and private_health_statement are excluded (conditions not met)
    assert "wfh_diary" not in req_ids
    assert "private_health_statement" not in req_ids

    # Check available_after_fy flags match employee_tax_au YAML
    payg = next(m for m in missing if m.requirement_id == "payg_summary")
    work = next(m for m in missing if m.requirement_id == "work_receipts")
    assert payg.available_after_fy is True     # YAML: available_after_fy: true
    assert work.available_after_fy is False    # YAML: available_after_fy: false


# ── 10. Interview complete() triggers readiness recalculation ─────────────────

@pytest.mark.asyncio
async def test_interview_complete_triggers_readiness_recalculation(
    workspace_ended_fy, db_session
):
    from app.engines.interview import InterviewEngine
    from app.engines.readiness import ReadinessEngine

    await _create_profile(db_session, workspace_ended_fy.id, "2024-25")

    mock_readiness = MagicMock(spec=ReadinessEngine)
    mock_readiness.recalculate = AsyncMock()
    mock_readiness.mark_stale = AsyncMock()

    engine = InterviewEngine(readiness_engine=mock_readiness)
    session, _ = await engine.start(workspace_ended_fy.id, "2024-25", db_session)

    await engine.complete(session.id, db_session)

    # create_task is fire-and-forget; yield once to let it run
    await asyncio.sleep(0)

    mock_readiness.recalculate.assert_called_once_with(workspace_ended_fy.id)


# ── 11. Evidence Engine document "ready" triggers mark_stale ─────────────────

@pytest.mark.asyncio
async def test_evidence_ready_triggers_mark_stale(workspace_ended_fy, db_session, tmp_path):
    from app.engines.evidence import EvidenceEngine
    from app.engines.readiness import ReadinessEngine
    from app.storage.local import LocalStorageBackend

    storage = LocalStorageBackend(base_path=str(tmp_path))

    mock_readiness = MagicMock(spec=ReadinessEngine)
    mock_readiness.mark_stale = AsyncMock()

    doc = Document(
        workspace_id=workspace_ended_fy.id,
        financial_year="2024-25",
        original_filename="test.pdf",
        storage_key=f"{workspace_ended_fy.id}/test_doc/original.pdf",
        file_type="pdf",
        sha256_hash="deadbeef" * 8,
        status="processing",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    engine = EvidenceEngine(
        db=db_session, storage=storage, readiness_engine=mock_readiness
    )

    # Patch _extract to skip real file I/O — we only care about the mark_stale call
    with patch.object(
        engine, "_extract", return_value=("extracted text", {}, "pdfplumber", 0.9)
    ):
        await engine.extract_and_finalize(doc.id)

    mock_readiness.mark_stale.assert_called_once_with(
        workspace_ended_fy.id, db_session
    )
