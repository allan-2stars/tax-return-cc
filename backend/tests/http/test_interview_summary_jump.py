"""HTTP tests for GET /interview/summary and POST /interview/jump."""
import pytest


async def _complete_full_interview(client) -> None:
    """Answer all platform + skill questions, then mark the interview complete."""
    resp = await client.post("/api/v1/interview/start")
    assert resp.status_code == 200, resp.text

    # Platform answers — these are the fixed questions for any employee
    platform_answers = [
        ("fy_confirm",        "2024-25"),
        ("residency",         "resident"),
        ("employment_type",   "employee"),
        ("family_situation",  "single_no_dependents"),
        ("lodger_type",       "self"),
    ]
    for qid, answer in platform_answers:
        resp = await client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, f"Answer failed for {qid}: {resp.text}"

    # Answer remaining skill questions until there are none left
    body = resp.json()
    next_q = body["data"].get("next_question")
    while next_q is not None:
        qid = next_q["id"]
        q_type = next_q.get("type", "text")
        options = next_q.get("options") or []
        if q_type == "number":
            answer = "3"
        elif options:
            answer = str(options[0])
        else:
            answer = "yes"
        resp = await client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, f"Answer failed for skill question {qid}: {resp.text}"
        body = resp.json()
        next_q = body["data"].get("next_question")

    resp = await client.post("/api/v1/interview/complete")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["state"] == "awaiting_evidence"


@pytest.mark.asyncio
async def test_get_summary(auth_client):
    """GET /interview/summary returns sections with Your situation containing residency."""
    await _complete_full_interview(auth_client)

    resp = await auth_client.get("/api/v1/interview/summary")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    sections = body["data"]["sections"]
    assert isinstance(sections, list)

    # First section must be "Your situation"
    first = sections[0]
    assert first["title"] == "Your situation"

    # The answers list must contain the residency entry
    answers_by_id = {a["question_id"]: a for a in first["answers"]}
    assert "residency" in answers_by_id, (
        f"Expected 'residency' in answers, got {list(answers_by_id.keys())}"
    )

    residency = answers_by_id["residency"]
    assert residency["question_label"] == "Residency status"
    assert residency["answer_label"] == "Australian resident"

    # Every answer row must be editable
    for section in sections:
        for answer in section["answers"]:
            assert answer["editable"] is True, (
                f"answer {answer['question_id']} has editable={answer['editable']}"
            )


@pytest.mark.asyncio
async def test_jump_to_question(auth_client):
    """POST /interview/jump with a known question_id rewinds to that question."""
    await _complete_full_interview(auth_client)

    resp = await auth_client.post(
        "/api/v1/interview/jump",
        json={"question_id": "residency"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["state"] == "in_progress"
    assert body["data"]["current_question"]["id"] == "residency"


@pytest.mark.asyncio
async def test_jump_unknown_question(auth_client):
    """POST /interview/jump with an unknown question_id returns 404."""
    await _complete_full_interview(auth_client)

    resp = await auth_client.post(
        "/api/v1/interview/jump",
        json={"question_id": "nonexistent_q"},
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_jump_then_answer(auth_client):
    """After jumping back to residency and re-answering, state is still in_progress."""
    await _complete_full_interview(auth_client)

    # Jump back to residency
    resp = await auth_client.post(
        "/api/v1/interview/jump",
        json={"question_id": "residency"},
    )
    assert resp.status_code == 200, resp.text

    # Answer residency again
    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "residency", "answer": "resident"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # More questions remain (we jumped mid-session)
    assert body["data"]["state"] == "in_progress"
