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
