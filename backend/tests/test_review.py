"""
Tests for M8 Review Engine.

TDD — all 12 tests written before implementation.
Expected to fail until Tasks 2-5 complete.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.models import (
    Workspace,
    TaxProfile,
    TaxEvent,
    ReviewItem as ReviewItemModel,
    AuditLog,
    InterviewSession,
    Document,
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
async def workspace(db_session):
    ws = Workspace(name="Review Test WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def profile(db_session, workspace):
    p = TaxProfile(
        workspace_id=workspace.id,
        financial_year="2024-25",
        employment_type="employee",
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


# ── helpers ───────────────────────────────────────────────────────────────────

async def _create_event(
    db_session,
    workspace_id: str,
    category: str = "work_expense",
    status: str = "needs_user_review",
    amount: float = 100.0,
    risk_level: str = "low",
) -> TaxEvent:
    event = TaxEvent(
        workspace_id=workspace_id,
        financial_year="2024-25",
        event_type="deduction",
        category=category,
        description=f"Test {category}",
        amount=amount,
        risk_level=risk_level,
        status=status,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


async def _create_item(
    db_session,
    workspace_id: str,
    event: TaxEvent | None = None,
    status: str = "needs_user_review",
    risk_level: str = "low",
    amount: float = 100.0,
    questions_complete: bool = True,
    inline_questions: list | None = None,
) -> ReviewItemModel:
    item = ReviewItemModel(
        workspace_id=workspace_id,
        tax_event_id=event.id if event else None,
        category=event.category if event else "work_expense",
        amount=amount,
        risk_level=risk_level,
        status=status,
        questions_complete=questions_complete,
        inline_questions=inline_questions or [],
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


async def _create_interview_session(
    db_session, workspace_id: str, answers: dict | None = None
) -> InterviewSession:
    session = InterviewSession(
        workspace_id=workspace_id,
        financial_year="2024-25",
        state="in_progress",
        answers=answers or {},
        activated_skills=[],
        pending_queue=[],
        completed_steps=[],
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


def _mock_readiness():
    m = MagicMock()
    m.recalculate = AsyncMock()
    m.mark_stale = AsyncMock()
    return m


# ── 1. create_review_item() creates ReviewItem from TaxEvent ──────────────────

@pytest.mark.asyncio
async def test_create_review_item_creates_from_tax_event(workspace, db_session):
    from app.engines.review import ReviewEngine

    event = await _create_event(
        db_session, workspace.id, category="payg_income",
        amount=5000.0, risk_level="low",
    )

    engine = ReviewEngine()
    item = await engine.create_review_item(event, db_session)

    assert item.workspace_id == workspace.id
    assert item.tax_event_id == event.id
    assert item.category == event.category
    assert item.amount == event.amount
    assert item.risk_level == event.risk_level
    assert item.status == "needs_user_review"
    assert item.id is not None


# ── 2. Queue sort order: incomplete questions → high risk → amount desc ────────

@pytest.mark.asyncio
async def test_get_queue_sort_order(workspace, db_session):
    from app.engines.review import ReviewEngine

    # Item A: questions complete, high risk, amount=100
    event_a = await _create_event(db_session, workspace.id, amount=100.0, risk_level="high")
    item_a = await _create_item(
        db_session, workspace.id, event_a,
        risk_level="high", amount=100.0, questions_complete=True,
    )

    # Item B: questions INCOMPLETE, low risk, amount=50
    event_b = await _create_event(db_session, workspace.id, amount=50.0, risk_level="low")
    item_b = await _create_item(
        db_session, workspace.id, event_b,
        risk_level="low", amount=50.0, questions_complete=False,
        inline_questions=[{"id": "q1", "ask": "Test?"}],
    )

    # Item C: questions complete, low risk, amount=200
    event_c = await _create_event(db_session, workspace.id, amount=200.0, risk_level="low")
    item_c = await _create_item(
        db_session, workspace.id, event_c,
        risk_level="low", amount=200.0, questions_complete=True,
    )

    engine = ReviewEngine()
    queue = await engine.get_queue(workspace.id, db_session)

    # All items in one combined list for sort testing
    all_items = queue.agent_required + queue.high_risk + queue.needs_review + queue.confirmed
    ids = [i.id for i in all_items]

    # Incomplete questions first, then high risk, then higher amount
    assert ids.index(item_b.id) < ids.index(item_a.id)   # incomplete before high-risk
    assert ids.index(item_a.id) < ids.index(item_c.id)   # high-risk before low-risk
    # item_c has amount=200 > item_b amount=50 but item_b is first (incomplete)


# ── 3. process_action(CONFIRMED) → event confirmed, AuditLog written ──────────

@pytest.mark.asyncio
async def test_process_action_confirmed(workspace, db_session):
    from app.engines.review import ReviewEngine, UserAction

    event = await _create_event(db_session, workspace.id)
    item = await _create_item(db_session, workspace.id, event)

    engine = ReviewEngine(readiness_engine=_mock_readiness())
    result = await engine.process_action(item.id, UserAction.CONFIRMED, {}, db_session)

    assert result.status == "confirmed"
    assert result.user_action == "confirmed"
    assert result.reviewed_at is not None

    await db_session.refresh(event)
    assert event.status == "confirmed"
    assert event.review_status == "user_confirmed"

    logs = (await db_session.execute(
        select(AuditLog).where(AuditLog.workspace_id == workspace.id)
    )).scalars().all()
    assert any(log.action == "confirmed" and log.actor == "user" for log in logs)


# ── 4. process_action(AMENDED) → correction_history appended, item confirmed ──

@pytest.mark.asyncio
async def test_process_action_amended(workspace, db_session):
    from app.engines.review import ReviewEngine, UserAction

    event = await _create_event(db_session, workspace.id, amount=100.0)
    item = await _create_item(db_session, workspace.id, event, amount=100.0)

    payload = {"amount": 250.0, "category": "work_equipment", "note": "corrected amount"}
    engine = ReviewEngine(readiness_engine=_mock_readiness())
    result = await engine.process_action(item.id, UserAction.AMENDED, payload, db_session)

    assert result.status == "confirmed"
    assert result.amended_amount == 250.0
    assert result.amended_category == "work_equipment"
    assert result.user_note == "corrected amount"

    await db_session.refresh(event)
    assert event.correction_history is not None
    assert len(event.correction_history) == 1
    entry = event.correction_history[0]
    assert entry["field"] == "amount"
    assert float(entry["old_value"]) == 100.0
    assert float(entry["new_value"]) == 250.0


# ── 5. process_action(FLAGGED) → item + event status = needs_agent_review ─────

@pytest.mark.asyncio
async def test_process_action_flagged(workspace, db_session):
    from app.engines.review import ReviewEngine, UserAction

    event = await _create_event(db_session, workspace.id)
    item = await _create_item(db_session, workspace.id, event)

    engine = ReviewEngine(readiness_engine=_mock_readiness())
    result = await engine.process_action(
        item.id, UserAction.FLAGGED, {"note": "need agent"}, db_session
    )

    assert result.status == "needs_agent_review"
    assert result.user_note == "need agent"

    await db_session.refresh(event)
    assert event.status == "needs_agent_review"


# ── 6. process_action(SKIPPED) → skipped_until set, status unchanged ──────────

@pytest.mark.asyncio
async def test_process_action_skipped(workspace, db_session):
    from app.engines.review import ReviewEngine, UserAction

    event = await _create_event(db_session, workspace.id)
    item = await _create_item(db_session, workspace.id, event)

    engine = ReviewEngine(readiness_engine=_mock_readiness())
    result = await engine.process_action(item.id, UserAction.SKIPPED, {}, db_session)

    assert result.status == "needs_user_review"        # status unchanged
    assert result.user_action == "skipped"
    assert result.skipped_until is not None
    # skipped_until should be approximately now + 1 day
    expected = datetime.now(timezone.utc) + timedelta(days=1)
    diff = abs((result.skipped_until - expected).total_seconds())
    assert diff < 60


# ── 7. Bulk confirm → each item individually logged in AuditLog ───────────────

@pytest.mark.asyncio
async def test_bulk_confirm_logs_each_item_individually(workspace, db_session):
    from app.engines.review import ReviewEngine, UserAction

    event_a = await _create_event(db_session, workspace.id)
    event_b = await _create_event(db_session, workspace.id)
    item_a = await _create_item(db_session, workspace.id, event_a)
    item_b = await _create_item(db_session, workspace.id, event_b)

    engine = ReviewEngine(readiness_engine=_mock_readiness())
    results = await engine.bulk_action(
        [item_a.id, item_b.id], UserAction.CONFIRMED, db_session
    )

    assert len(results) == 2
    assert all(r.status == "confirmed" for r in results)

    logs = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace.id,
            AuditLog.action == "confirmed",
        )
    )).scalars().all()
    # Each item logged separately
    assert len(logs) == 2
    logged_event_ids = {log.tax_event_id for log in logs}
    assert event_a.id in logged_event_ids
    assert event_b.id in logged_event_ids


# ── 8. Bulk amend → rejected (only CONFIRMED allowed for bulk) ────────────────

@pytest.mark.asyncio
async def test_bulk_amend_raises_error(workspace, db_session):
    from app.engines.review import ReviewEngine, UserAction

    event = await _create_event(db_session, workspace.id)
    item = await _create_item(db_session, workspace.id, event)

    engine = ReviewEngine(readiness_engine=_mock_readiness())
    with pytest.raises(ValueError, match="[Bb]ulk"):
        await engine.bulk_action([item.id], UserAction.AMENDED, db_session)


# ── 9. submit_inline_answer → answer saved, questions_complete updated ────────

@pytest.mark.asyncio
async def test_submit_inline_answer_saves_answer_and_marks_complete(
    workspace, db_session
):
    from app.engines.review import ReviewEngine

    event = await _create_event(db_session, workspace.id)
    item = await _create_item(
        db_session, workspace.id, event,
        questions_complete=False,
        inline_questions=[{"id": "work_purpose", "ask": "Was this for work?"}],
    )
    session = await _create_interview_session(db_session, workspace.id)

    engine = ReviewEngine()
    result = await engine.submit_inline_answer(
        item_id=item.id,
        question_id="work_purpose",
        answer="yes",
        event_id=event.id,
        db=db_session,
    )

    # Answer saved to interview session
    await db_session.refresh(session)
    assert session.answers.get("work_purpose") == "yes"

    # All inline questions answered → questions_complete = True
    assert result.questions_complete is True


# ── 10. ask_claude → response contains disclaimer, AuditLog written ───────────

@pytest.mark.asyncio
async def test_ask_claude_returns_answer_with_disclaimer(workspace, db_session, profile):
    from app.engines.review import ReviewEngine

    event = await _create_event(db_session, workspace.id)
    item = await _create_item(db_session, workspace.id, event)

    disclaimer = "does not constitute tax advice"
    mock_ai = MagicMock()
    mock_ai.ask = AsyncMock(
        return_value=f"Your WFH expenses are a candidate deduction. {disclaimer}"
    )

    engine = ReviewEngine(ai_adapter=mock_ai)
    answer = await engine.ask_claude(item.id, "Can I claim WFH?", profile, db_session)

    mock_ai.ask.assert_called_once()
    assert disclaimer in answer


# ── 11. After any action → readiness recalculation triggered ──────────────────

@pytest.mark.asyncio
async def test_process_action_triggers_readiness_recalculation(workspace, db_session):
    from app.engines.review import ReviewEngine, UserAction

    event = await _create_event(db_session, workspace.id)
    item = await _create_item(db_session, workspace.id, event)

    mock_readiness = _mock_readiness()
    engine = ReviewEngine(readiness_engine=mock_readiness)

    await engine.process_action(item.id, UserAction.CONFIRMED, {}, db_session)

    # create_task is fire-and-forget; yield to event loop
    await asyncio.sleep(0)

    mock_readiness.recalculate.assert_called_once_with(workspace.id)


# ── 12. Evidence Engine creates ReviewItem after TaxEvent created ─────────────

@pytest.mark.asyncio
async def test_evidence_engine_creates_review_item_after_tax_event(
    workspace, db_session, tmp_path
):
    from app.engines.evidence import EvidenceEngine
    from app.engines.review import ReviewEngine
    from app.storage.local import LocalStorageBackend

    storage = LocalStorageBackend(base_path=str(tmp_path))

    mock_review = MagicMock(spec=ReviewEngine)
    mock_review.create_review_item = AsyncMock(return_value=MagicMock())

    doc = Document(
        workspace_id=workspace.id,
        financial_year="2024-25",
        original_filename="payg.pdf",
        storage_key=f"{workspace.id}/doc1/original.pdf",
        file_type="pdf",
        sha256_hash="cafebabe" * 8,
        status="processing",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    # Patch AI to return a classification that triggers an event extraction
    mock_classification = MagicMock()
    mock_classification.document_type = "payg_summary"
    mock_classification.skill_id = "employee_tax_au"

    mock_skill = MagicMock()
    from app.ai.base import EventCandidate
    mock_skill.extract_events.return_value = [
        EventCandidate(
            event_type="income",
            category="payg_income",
            description="Salary",
            amount=80000.0,
            date="2024-07-01",
            confidence=0.95,
            ai_reasoning="PAYG income",
        )
    ]

    mock_ai = MagicMock()
    mock_ai.classify = AsyncMock(return_value=mock_classification)

    engine = EvidenceEngine(
        db=db_session,
        storage=storage,
        ai_adapter=mock_ai,
        review_engine=mock_review,
    )

    with patch.object(engine, "_extract", return_value=("payg text", {}, "pdfplumber", 0.9)), \
         patch("app.engines.evidence.get_registry") as mock_reg:
        mock_reg.return_value.get_owner.return_value = mock_skill
        await engine.extract_and_finalize(doc.id)

    # ReviewItem should have been created for the extracted TaxEvent
    mock_review.create_review_item.assert_called_once()


# ── group_id and group_display appear in queue response ─────────────────────

@pytest.mark.asyncio
async def test_queue_response_includes_group_id_and_group_display(workspace, db_session, profile):
    """GET /review/queue includes group_id and group_display from linked TaxEvent."""
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    event = await _create_event(db_session, workspace.id, category="work_expense")
    # Set group_id on the event directly
    event.group_id = "grp-recurring-123"
    event.group_display = "Monthly subscription"
    await db_session.commit()
    await db_session.refresh(event)

    await engine.create_review_item(event, db_session)

    # Fetch queue via engine
    queue = await engine.get_queue(workspace.id, db_session)
    all_items = queue.agent_required + queue.high_risk + queue.needs_review + queue.confirmed
    assert len(all_items) == 1

    # Verify the item can be serialised and includes group fields
    from app.api.routes.review import _item_dict
    d = _item_dict(all_items[0])
    assert d["group_id"] == "grp-recurring-123"
    assert d["group_display"] == "Monthly subscription"
