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
