"""
Tests for M6 Interview Engine.

TDD — all 12 tests written before implementation.
Expected to fail (ImportError) until Tasks 2-5 complete.
"""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from unittest.mock import MagicMock

from app.db.models import (
    Workspace, TaxProfile, TaxEvent, SkillVersionLock, InterviewSession,
)
from app.skills.base import TaxSkill, Question


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def patch_async_session_local(test_engine, monkeypatch):
    import app.db.base as db_base
    test_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(db_base, "AsyncSessionLocal", test_maker)


@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def workspace(db_session):
    ws = Workspace(name="Interview Test WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


# ── helper ────────────────────────────────────────────────────────────────────

def _make_mock_skill(skill_id: str = "crypto_au") -> MagicMock:
    """Minimal mock TaxSkill with one question, usable for activation tests."""
    skill = MagicMock(spec=TaxSkill)
    skill.skill_id = skill_id
    skill.version = "1.0.0"
    skill.owned_categories = ["crypto"]
    skill.get_questions.return_value = [
        Question(id=f"{skill_id}_q1", ask="Mock skill question", type="yes_no")
    ]
    return skill


# ── 1. start() → session in_progress, first platform question returned ────────

@pytest.mark.asyncio
async def test_start_creates_session_in_progress_with_first_question(db_session, workspace):
    from app.engines.interview import InterviewEngine

    engine = InterviewEngine()
    session, question = await engine.start(workspace.id, workspace.financial_year, db_session)

    assert session.state == "in_progress"
    assert session.workspace_id == workspace.id
    assert question is not None
    assert question.id == "fy_confirm"


# ── 2. process_answer() → answer saved, next question returned ────────────────

@pytest.mark.asyncio
async def test_process_answer_saves_answer_and_advances(db_session, workspace):
    from app.engines.interview import InterviewEngine

    engine = InterviewEngine()
    session, q1 = await engine.start(workspace.id, workspace.financial_year, db_session)

    session, q2 = await engine.process_answer(session.id, q1.id, "yes", db_session)

    assert q2 is not None
    assert q2.id != q1.id
    assert session.answers is not None
    assert session.answers.get(q1.id) == "yes"


# ── 3. Branch insertion: has_spouse → spouse_income_range inserted next ───────

@pytest.mark.asyncio
async def test_has_spouse_inserts_spouse_income_range_branch(db_session, workspace):
    from app.engines.interview import InterviewEngine

    engine = InterviewEngine()
    session, q = await engine.start(workspace.id, workspace.financial_year, db_session)

    for qid, ans in [
        ("fy_confirm", "yes"),
        ("residency", "resident"),
        ("employment_type", "employee"),
    ]:
        session, q = await engine.process_answer(session.id, qid, ans, db_session)

    assert q.id == "family_situation"
    session, branch_q = await engine.process_answer(
        session.id, "family_situation", "has_spouse", db_session
    )

    assert branch_q.id == "spouse_income_range"


# ── 4. go_back() undoes branch insertion and removes answer ───────────────────

@pytest.mark.asyncio
async def test_go_back_undoes_branch_insertion(db_session, workspace):
    from app.engines.interview import InterviewEngine

    engine = InterviewEngine()
    session, q = await engine.start(workspace.id, workspace.financial_year, db_session)

    for qid, ans in [
        ("fy_confirm", "yes"),
        ("residency", "resident"),
        ("employment_type", "employee"),
    ]:
        session, q = await engine.process_answer(session.id, qid, ans, db_session)

    session, branch_q = await engine.process_answer(
        session.id, "family_situation", "has_spouse", db_session
    )
    assert branch_q.id == "spouse_income_range"

    session, prev_q = await engine.go_back(session.id, db_session)

    assert prev_q.id == "family_situation"
    assert "family_situation" not in (session.answers or {})
    pending_ids = [
        (step["id"] if isinstance(step, dict) else step)
        for step in (session.pending_queue or [])
    ]
    assert "spouse_income_range" not in pending_ids


# ── 5. Skill activation inserts skill questions into the queue ────────────────

@pytest.mark.asyncio
async def test_skill_activation_inserts_skill_questions(db_session, workspace):
    from app.engines.interview import InterviewEngine

    mock_skill = _make_mock_skill("crypto_au")
    mock_registry = MagicMock()
    mock_registry.load_for_profile.return_value = []
    mock_registry.check_activation_delta.side_effect = lambda answers, current: (
        [mock_skill]
        if answers.get("employment_type") == "employee"
        and not any(s.skill_id == "crypto_au" for s in current)
        else []
    )

    engine = InterviewEngine(registry=mock_registry)
    session, q = await engine.start(workspace.id, workspace.financial_year, db_session)

    for qid, ans in [
        ("fy_confirm", "yes"),
        ("residency", "resident"),
        ("employment_type", "employee"),
        ("family_situation", "single"),
        ("lodger_type", "self"),
    ]:
        session, q = await engine.process_answer(session.id, qid, ans, db_session)

    assert q is not None
    assert q.id == "crypto_au_q1"
    assert "crypto_au" in (session.activated_skills or [])


# ── 6. go_back() undoes skill activation and deletes SkillVersionLock ─────────

@pytest.mark.asyncio
async def test_go_back_removes_skill_lock_on_undo(db_session, workspace):
    from app.engines.interview import InterviewEngine

    mock_skill = _make_mock_skill("crypto_au")
    mock_registry = MagicMock()
    mock_registry.load_for_profile.return_value = []
    mock_registry.check_activation_delta.side_effect = lambda answers, current: (
        [mock_skill]
        if answers.get("employment_type") == "employee"
        and not any(s.skill_id == "crypto_au" for s in current)
        else []
    )

    engine = InterviewEngine(registry=mock_registry)
    session, q = await engine.start(workspace.id, workspace.financial_year, db_session)

    session, _ = await engine.process_answer(session.id, "fy_confirm", "yes", db_session)
    session, _ = await engine.process_answer(session.id, "residency", "resident", db_session)
    session, _ = await engine.process_answer(session.id, "employment_type", "employee", db_session)

    result = await db_session.execute(
        select(SkillVersionLock).where(SkillVersionLock.workspace_id == workspace.id)
    )
    assert result.scalar_one_or_none() is not None
    assert "crypto_au" in (session.activated_skills or [])

    session, prev_q = await engine.go_back(session.id, db_session)

    assert prev_q.id == "employment_type"
    assert "employment_type" not in (session.answers or {})
    assert "crypto_au" not in (session.activated_skills or [])

    result2 = await db_session.execute(
        select(SkillVersionLock).where(SkillVersionLock.workspace_id == workspace.id)
    )
    assert result2.scalar_one_or_none() is None


# ── 7. skip() records reason and returns next question ───────────────────────

@pytest.mark.asyncio
async def test_skip_records_reason_and_returns_next_question(db_session, workspace):
    from app.engines.interview import InterviewEngine

    engine = InterviewEngine()
    session, first_q = await engine.start(workspace.id, workspace.financial_year, db_session)

    session, next_q = await engine.skip(session.id, first_q.id, "not sure yet", db_session)

    assert next_q is not None
    assert next_q.id != first_q.id
    skipped_ids = [
        (s.get("question_id") if isinstance(s, dict) else s)
        for s in (session.skipped_steps or [])
    ]
    assert first_q.id in skipped_ids


# ── 8. pause → resume preserves current question ─────────────────────────────

@pytest.mark.asyncio
async def test_pause_resume_preserves_current_question(db_session, workspace):
    from app.engines.interview import InterviewEngine

    engine = InterviewEngine()
    session, first_q = await engine.start(workspace.id, workspace.financial_year, db_session)
    session, q2 = await engine.process_answer(session.id, first_q.id, "yes", db_session)

    session = await engine.pause(session.id, db_session)
    assert session.state == "paused"

    session, resumed_q = await engine.resume(session.id, db_session)

    assert session.state == "in_progress"
    assert resumed_q.id == q2.id
    assert (session.answers or {}).get(first_q.id) == "yes"


# ── 9. complete() → state=awaiting_evidence, completed_at set ────────────────

@pytest.mark.asyncio
async def test_complete_sets_awaiting_evidence_not_complete(db_session, workspace):
    from app.engines.interview import InterviewEngine

    engine = InterviewEngine()
    session, _ = await engine.start(workspace.id, workspace.financial_year, db_session)

    session = await engine.complete(session.id, db_session)

    assert session.state == "awaiting_evidence"
    assert session.state != "complete"
    assert session.completed_at is not None


# ── 10. check_inline_questions → list[tuple[TaxEvent, list[InlineQuestion]]] ──

@pytest.mark.asyncio
async def test_check_inline_questions_returns_typed_pairs(db_session, workspace):
    from app.engines.interview import InterviewEngine, InlineQuestion

    event = TaxEvent(
        workspace_id=workspace.id,
        financial_year=workspace.financial_year,
        event_type="deduction",
        category="work_expense",
        description="Work laptop",
        amount=1500.0,
        status="needs_user_review",
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    engine = InterviewEngine()
    results = await engine.check_inline_questions(workspace.id, [event], db_session)

    assert isinstance(results, list)
    for item in results:
        assert isinstance(item, tuple)
        assert len(item) == 2
        _, inline_qs = item
        assert isinstance(inline_qs, list)
        for iq in inline_qs:
            assert isinstance(iq, InlineQuestion)


# ── 11. Platform answers update TaxProfile fields ─────────────────────────────

@pytest.mark.asyncio
async def test_platform_answers_update_tax_profile(db_session, workspace):
    from app.engines.interview import InterviewEngine

    engine = InterviewEngine()
    session, q = await engine.start(workspace.id, workspace.financial_year, db_session)

    for qid, ans in [
        ("fy_confirm", "yes"),
        ("residency", "resident"),
        ("employment_type", "employee"),
    ]:
        session, q = await engine.process_answer(session.id, qid, ans, db_session)

    result = await db_session.execute(
        select(TaxProfile).where(TaxProfile.workspace_id == workspace.id)
    )
    profile = result.scalar_one()
    assert profile.resident_status == "resident"
    assert profile.employment_type == "employee"


# ── 12. Full Q1-Q5 → employee_tax_au activates, skill questions begin ─────────

@pytest.mark.asyncio
async def test_full_platform_flow_activates_employee_skill(db_session, workspace):
    from app.engines.interview import InterviewEngine

    engine = InterviewEngine()
    session, q = await engine.start(workspace.id, workspace.financial_year, db_session)

    for qid, ans in [
        ("fy_confirm", "yes"),
        ("residency", "resident"),
        ("employment_type", "employee"),
        ("family_situation", "single"),
        ("lodger_type", "self"),
    ]:
        session, q = await engine.process_answer(session.id, qid, ans, db_session)

    assert q is not None
    assert "employee_tax_au" in (session.activated_skills or [])
    platform_ids = {"fy_confirm", "residency", "employment_type", "family_situation", "lodger_type"}
    assert q.id not in platform_ids


# ── 13. _q_dict exposes required, why, hint fields ───────────────────────────

@pytest.mark.asyncio
async def test_question_dict_includes_required_why_hint(auth_client):
    """_q_dict must serialise required, why, hint for the frontend."""
    await auth_client.post("/api/v1/interview/start")
    resp = await auth_client.get("/api/v1/interview/session")
    assert resp.status_code == 200
    q = resp.json()["data"]["current_question"]
    assert q is not None
    assert "required" in q
    assert "why" in q
    assert "hint" in q
    assert isinstance(q["required"], bool)
