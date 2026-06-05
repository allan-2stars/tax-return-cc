"""HTTP smoke tests for /interview route group."""
import pytest


@pytest.mark.asyncio
async def test_get_session_not_started(auth_client):
    """GET /interview/session returns 200 with state=not_started when no session exists."""
    resp = await auth_client.get("/api/v1/interview/session")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["state"] == "not_started"


@pytest.mark.asyncio
async def test_start_interview(auth_client):
    """POST /interview/start returns 200 with state=in_progress and a first question."""
    resp = await auth_client.post("/api/v1/interview/start")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["state"] == "in_progress"
    assert body["data"]["current_question"]["id"] == "fy_confirm"
    assert body["data"]["session_id"] is not None


@pytest.mark.asyncio
async def test_answer_question(auth_client):
    """POST /interview/answer returns 200 and advances to next question."""
    await auth_client.post("/api/v1/interview/start")
    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "fy_confirm", "answer": "2024-25"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["state"] == "in_progress"
    # Next question should be residency
    assert body["data"]["next_question"]["id"] == "residency"


@pytest.mark.asyncio
async def test_skip_question(auth_client):
    """POST /interview/skip returns 200 and records the skip."""
    await auth_client.post("/api/v1/interview/start")
    resp = await auth_client.post(
        "/api/v1/interview/skip",
        json={"question_id": "fy_confirm", "reason": "not sure"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["state"] == "in_progress"


@pytest.mark.asyncio
async def test_back_navigation(auth_client):
    """POST /interview/back after answering returns previous question."""
    await auth_client.post("/api/v1/interview/start")
    # Answer first question
    await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "fy_confirm", "answer": "2024-25"},
    )
    # Go back
    resp = await auth_client.post("/api/v1/interview/back")
    assert resp.status_code == 200
    body = resp.json()
    # Should be back at fy_confirm
    assert body["data"]["current_question"]["id"] == "fy_confirm"


@pytest.mark.asyncio
async def test_start_interview_fy_confirm_includes_workspace_financial_year(auth_client, test_engine):
    """fy_confirm options must include the workspace financial_year."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.models import Workspace

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        ws = (await session.execute(select(Workspace).where(Workspace.id == auth_client.workspace_id))).scalar_one()
        ws.financial_year = "2025-26"
        await session.commit()

    resp = await auth_client.post("/api/v1/interview/start")
    assert resp.status_code == 200, resp.text
    q = resp.json()["data"]["current_question"]
    assert q["id"] == "fy_confirm"
    assert "2025-26" in (q.get("options") or [])


@pytest.mark.asyncio
async def test_get_session_fy_confirm_options_include_workspace_financial_year_and_no_duplicates(
    auth_client, test_engine
):
    """GET /interview/session must return fy_confirm options aligned to workspace FY (dynamic, not import-time)."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.models import Workspace

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        ws = (
            await session.execute(select(Workspace).where(Workspace.id == auth_client.workspace_id))
        ).scalar_one()
        ws.financial_year = "2025-26"
        await session.commit()

    await auth_client.post("/api/v1/interview/start")
    resp = await auth_client.get("/api/v1/interview/session")
    assert resp.status_code == 200, resp.text
    q = resp.json()["data"]["current_question"]
    assert q["id"] == "fy_confirm"
    opts = q.get("options") or []
    assert opts[0] == "2025-26"
    assert len(opts) == len(set(opts))


@pytest.mark.asyncio
async def test_answer_single_choice_invalid_option_returns_422(auth_client):
    """Single choice answers must be one of question.options."""
    await auth_client.post("/api/v1/interview/start")
    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "fy_confirm", "answer": "1900-01"},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error_code"] == "invalid_answer"


@pytest.mark.asyncio
async def test_answer_fy_confirm_accepts_workspace_financial_year(auth_client, test_engine):
    """Answering fy_confirm with workspace.financial_year must be accepted (dynamic options)."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.models import Workspace

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        ws = (
            await session.execute(select(Workspace).where(Workspace.id == auth_client.workspace_id))
        ).scalar_one()
        ws.financial_year = "2025-26"
        await session.commit()

    await auth_client.post("/api/v1/interview/start")
    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "fy_confirm", "answer": "2025-26"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_answer_fy_confirm_rejects_future_financial_year(auth_client, test_engine):
    """fy_confirm should not accept arbitrary FY strings outside the allowed dynamic set."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.models import Workspace

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        ws = (
            await session.execute(select(Workspace).where(Workspace.id == auth_client.workspace_id))
        ).scalar_one()
        ws.financial_year = "2025-26"
        await session.commit()

    await auth_client.post("/api/v1/interview/start")
    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "fy_confirm", "answer": "2099-00"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "invalid_answer"


@pytest.mark.asyncio
async def test_dependent_count_rejects_out_of_range_and_not_persisted(auth_client):
    """dependent_count must be integer between 1 and 20 when has_dependents=yes."""
    await auth_client.post("/api/v1/interview/start")
    for qid, answer in [
        ("fy_confirm", "2024-25"),
        ("residency", "resident"),
        ("employment_type", "employee"),
        ("has_spouse", "no"),
        ("has_dependents", "yes"),
    ]:
        resp = await auth_client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, resp.text
    # Next question should be dependent_count
    assert resp.json()["data"]["next_question"]["id"] == "dependent_count"

    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "dependent_count", "answer": "0"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "invalid_answer"

    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "dependent_count", "answer": "-1"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "invalid_answer"

    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "dependent_count", "answer": "1.5"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "invalid_answer"

    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "dependent_count", "answer": "9999"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "invalid_answer"

    # Summary must not include dependent_count
    resp = await auth_client.get("/api/v1/interview/summary")
    assert resp.status_code == 200
    sections = resp.json()["data"]["sections"]
    situation = next((s for s in sections if s["title"] == "Your situation"), None)
    assert situation is not None
    ids = {a["question_id"] for a in situation["answers"]}
    assert "dependent_count" not in ids


@pytest.mark.asyncio
async def test_dependent_count_accepts_1_to_20(auth_client):
    """dependent_count should accept integers 1..20 when has_dependents=yes."""
    await auth_client.post("/api/v1/interview/start")
    for qid, answer in [
        ("fy_confirm", "2024-25"),
        ("residency", "resident"),
        ("employment_type", "employee"),
        ("has_spouse", "no"),
        ("has_dependents", "yes"),
    ]:
        resp = await auth_client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["next_question"]["id"] == "dependent_count"

    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "dependent_count", "answer": "1"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_skip_conditional_question_propagates_and_returns_summary(auth_client):
    """Skipping a conditional follow-up should safely end that branch and return to summary."""
    await auth_client.post("/api/v1/interview/start")
    for qid, answer in [
        ("fy_confirm", "2024-25"),
        ("residency", "resident"),
        ("employment_type", "employee"),
        ("has_spouse", "no"),
        ("has_dependents", "no"),
        ("lodger_type", "self"),
        ("wfh", "yes_regular"),
    ]:
        resp = await auth_client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, resp.text

    assert resp.json()["data"]["next_question"]["id"] == "wfh_method"

    skip_resp = await auth_client.post(
        "/api/v1/interview/skip",
        json={"question_id": "wfh_method", "reason": "skip_for_now"},
    )
    assert skip_resp.status_code == 200, skip_resp.text
    body = skip_resp.json()["data"]
    assert body["state"] == "awaiting_evidence"
    assert body["next_question"] is None

    session_resp = await auth_client.get("/api/v1/interview/session")
    assert session_resp.status_code == 200, session_resp.text
    session = session_resp.json()["data"]
    assert session["state"] == "awaiting_evidence"
    assert session["current_question"] is None
    assert session["answers"]["wfh"] == "yes_regular"
    assert "wfh_method" not in session["answers"]
    assert "wfh_days" not in session["answers"]


@pytest.mark.asyncio
async def test_skip_conditional_child_preserves_unrelated_answers(auth_client):
    """Skipping a branch child must not wipe unrelated completed platform answers."""
    await auth_client.post("/api/v1/interview/start")
    for qid, answer in [
        ("fy_confirm", "2024-25"),
        ("residency", "resident"),
        ("employment_type", "employee"),
        ("has_spouse", "yes"),
        ("spouse_income_range", "45000_120000"),
        ("spouse_novated_lease", "no"),
        ("has_dependents", "no"),
        ("lodger_type", "self"),
        ("wfh", "yes_regular"),
    ]:
        resp = await auth_client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, resp.text

    resp = await auth_client.post(
        "/api/v1/interview/skip",
        json={"question_id": "wfh_method", "reason": "skip_for_now"},
    )
    assert resp.status_code == 200, resp.text

    session_resp = await auth_client.get("/api/v1/interview/session")
    assert session_resp.status_code == 200, session_resp.text
    answers = session_resp.json()["data"]["answers"]
    assert answers["residency"] == "resident"
    assert answers["spouse_income_range"] == "45000_120000"
    assert answers["spouse_novated_lease"] == "no"


@pytest.mark.asyncio
async def test_skip_platform_question_keeps_valid_session_and_marks_incomplete(auth_client):
    """Skipping an early platform question must not produce invalid in_progress/null state."""
    await auth_client.post("/api/v1/interview/start")
    resp = await auth_client.post(
        "/api/v1/interview/skip",
        json={"question_id": "fy_confirm", "reason": "skip_for_now"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["next_question"] is not None
    assert body["next_question"]["id"] == "residency"

    session_resp = await auth_client.get("/api/v1/interview/session")
    assert session_resp.status_code == 200, session_resp.text
    session = session_resp.json()["data"]
    assert not (session["state"] == "in_progress" and session["current_question"] is None)
    incomplete_ids = {q["question_id"] for q in session.get("incomplete_questions", [])}
    assert "fy_confirm" in incomplete_ids


async def _reach_wfh_days_question(auth_client):
    await auth_client.post("/api/v1/interview/start")
    for qid, answer in [
        ("fy_confirm", "2024-25"),
        ("residency", "resident"),
        ("employment_type", "employee"),
        ("has_spouse", "no"),
        ("has_dependents", "no"),
        ("lodger_type", "self"),
        ("wfh", "yes_regular"),
        ("wfh_method", "fixed_rate"),
    ]:
        resp = await auth_client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, f"{qid} failed: {resp.text}"
    assert resp.json()["data"]["next_question"]["id"] == "wfh_days"


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["-3", "0", "1.5", "8"])
async def test_wfh_days_rejects_invalid_values_and_not_persisted(auth_client, invalid):
    """wfh_days must reject invalid values and must not persist in summary."""
    await _reach_wfh_days_question(auth_client)

    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "wfh_days", "answer": invalid},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "invalid_answer"

    resp = await auth_client.get("/api/v1/interview/summary")
    assert resp.status_code == 200
    sections = resp.json()["data"]["sections"]
    all_ids = {a["question_id"] for s in sections for a in s["answers"]}
    assert "wfh_days" not in all_ids


@pytest.mark.asyncio
@pytest.mark.parametrize("valid", ["1", "2", "7"])
async def test_wfh_days_accepts_1_to_7_integers(auth_client, valid):
    """wfh_days should accept integer days 1..7."""
    await _reach_wfh_days_question(auth_client)

    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "wfh_days", "answer": valid},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_spouse_rfba_amount_rejects_out_of_range_and_not_persisted(auth_client):
    """spouse_rfba_amount must be between 0 and 1_000_000."""
    await auth_client.post("/api/v1/interview/start")
    for qid, answer in [
        ("fy_confirm", "2024-25"),
        ("residency", "resident"),
        ("employment_type", "employee"),
        ("has_spouse", "yes"),
        ("spouse_income_range", "45000_120000"),
        ("spouse_novated_lease", "yes"),
    ]:
        resp = await auth_client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["next_question"]["id"] == "spouse_rfba_amount"

    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "spouse_rfba_amount", "answer": "999999999999999999999"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "invalid_answer"

    resp = await auth_client.get("/api/v1/interview/summary")
    assert resp.status_code == 200
    sections = resp.json()["data"]["sections"]
    situation = next((s for s in sections if s["title"] == "Your situation"), None)
    assert situation is not None
    ids = {a["question_id"] for a in situation["answers"]}
    assert "spouse_rfba_amount" not in ids


@pytest.mark.asyncio
async def test_skip_spouse_rfba_amount_advances_and_stays_recoverable(auth_client):
    """Skipping spouse_rfba_amount should continue the interview and remain recoverable."""
    await auth_client.post("/api/v1/interview/start")
    for qid, answer in [
        ("fy_confirm", "2024-25"),
        ("residency", "resident"),
        ("employment_type", "employee"),
        ("has_spouse", "yes"),
        ("spouse_income_range", "45000_120000"),
        ("spouse_novated_lease", "yes"),
    ]:
        resp = await auth_client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["next_question"]["id"] == "spouse_rfba_amount"

    resp = await auth_client.post(
        "/api/v1/interview/skip",
        json={"question_id": "spouse_rfba_amount", "reason": "skip_for_now"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["state"] == "in_progress"
    assert body["next_question"]["id"] == "has_dependents"

    for qid, answer in [
        ("has_dependents", "no"),
        ("lodger_type", "self"),
    ]:
        resp = await auth_client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, resp.text

    session_resp = await auth_client.get("/api/v1/interview/session")
    assert session_resp.status_code == 200, session_resp.text
    session = session_resp.json()["data"]
    assert session["state"] == "awaiting_evidence"
    assert session["needs_restart"] is False
    assert session["current_question"] is None
    incomplete_ids = {q["question_id"] for q in session.get("incomplete_questions", [])}
    assert "spouse_rfba_amount" in incomplete_ids


@pytest.mark.asyncio
async def test_session_needs_restart_when_awaiting_evidence_missing_platform_answers(auth_client, test_engine):
    """If an awaiting_evidence session is missing required platform answers, flag needs_restart."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.models import InterviewSession

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        broken = InterviewSession(
            workspace_id=auth_client.workspace_id,
            financial_year="2025-26",
            state="awaiting_evidence",
            current_step=None,
            pending_queue=[],
            completed_steps=[],
            skipped_steps=[],
            answers={"fy_confirm": "2025-26"},
            branch_path=[],
            activated_skills=[],
        )
        session.add(broken)
        await session.commit()

    resp = await auth_client.get("/api/v1/interview/session")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["state"] == "awaiting_evidence"
    assert data["needs_restart"] is True
    assert "residency" in (data.get("missing_platform_ids") or [])


@pytest.mark.asyncio
async def test_restart_abandons_old_session_and_starts_fresh(auth_client, test_engine):
    """POST /interview/restart abandons broken session and returns a fresh in_progress session."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.models import InterviewSession

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        broken = InterviewSession(
            workspace_id=auth_client.workspace_id,
            financial_year="2025-26",
            state="awaiting_evidence",
            current_step=None,
            pending_queue=[],
            completed_steps=[],
            skipped_steps=[],
            answers={"fy_confirm": "2025-26"},
            branch_path=[],
            activated_skills=[],
        )
        session.add(broken)
        await session.commit()

    resp = await auth_client.post("/api/v1/interview/restart")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["state"] == "in_progress"
    assert body["data"]["current_question"]["id"] == "fy_confirm"
    new_id = body["data"]["session_id"]
    assert new_id

    # Old session must not remain active.
    async with maker() as session:
        result = await session.execute(
            select(InterviewSession).where(InterviewSession.workspace_id == auth_client.workspace_id)
        )
        all_sessions = list(result.scalars().all())
        assert len(all_sessions) >= 2
        old = next(s for s in all_sessions if s.id != new_id)
        assert old.state == "abandoned"

@pytest.mark.asyncio
async def test_legacy_pending_queue_family_situation_is_mapped_to_has_spouse(auth_client, test_engine):
    """Legacy compatibility: pending_queue may contain 'family_situation' from older deployments."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.models import InterviewSession

    # Create a legacy session directly in DB (simulates persisted state from older releases)
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        legacy = InterviewSession(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            state="in_progress",
            current_step={"id": "employment_type"},
            pending_queue=["family_situation", "lodger_type"],
            completed_steps=["fy_confirm", "residency"],
            skipped_steps=[],
            answers={"fy_confirm": "2024-25", "residency": "resident"},
            branch_path=[],
            activated_skills=[],
        )
        session.add(legacy)
        await session.commit()

    # Answer current question; should advance to has_spouse (not crash on unknown family_situation)
    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "employment_type", "answer": "employee"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["next_question"]["id"] == "has_spouse"


@pytest.mark.asyncio
async def test_legacy_current_step_family_situation_normalizes_to_has_spouse(auth_client, test_engine):
    """Legacy compatibility: current_step itself may be 'family_situation'."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.models import InterviewSession

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        legacy = InterviewSession(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            state="in_progress",
            current_step={"id": "family_situation"},
            pending_queue=["lodger_type"],
            completed_steps=["fy_confirm", "residency", "employment_type"],
            skipped_steps=[],
            answers={
                "fy_confirm": "2024-25",
                "residency": "resident",
                "employment_type": "employee",
            },
            branch_path=[],
            activated_skills=[],
        )
        session.add(legacy)
        await session.commit()

    # Fetch session: server should normalize legacy current_step so UI can render has_spouse.
    resp = await auth_client.get("/api/v1/interview/session")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["current_question"]["id"] == "has_spouse"

    # Answer has_spouse; next visible question must be has_dependents (legacy family_situation expands to both)
    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "has_spouse", "answer": "no"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["next_question"]["id"] == "has_dependents"
