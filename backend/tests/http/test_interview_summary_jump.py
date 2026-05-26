"""HTTP tests for GET /interview/summary and POST /interview/jump."""
import pytest


async def _complete_full_interview(client) -> None:
    """Answer all platform + skill questions, then mark the interview complete."""
    resp = await client.post("/api/v1/interview/start")
    assert resp.status_code == 200, resp.text

    # Platform answers — these are the fixed questions for any employee
    platform_answers = [
        ("fy_confirm",      "2024-25"),
        ("residency",       "resident"),
        ("employment_type", "employee"),
        ("has_spouse",      "no"),
        ("has_dependents",  "no"),
        ("lodger_type",     "self"),
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

    # Skill sections (if any) should have non-null question_labels (q.ask text from skill)
    for section in sections:
        if section["title"] == "Your situation":
            continue
        for ans in section["answers"]:
            assert ans["question_label"], (
                f"Skill section '{section['title']}' answer {ans['question_id']} has empty question_label"
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
    # After answering residency again, employment_type must be next
    # (residency has no branches for "resident"; employment_type follows deterministically)
    assert body["data"]["next_question"]["id"] == "employment_type"


# ── Additional tests (Bug 1 + Bug 2 regression) ───────────────────────────────

async def _complete_interview_with_spouse(client) -> None:
    """Complete interview using has_spouse to activate spouse branch questions."""
    resp = await client.post("/api/v1/interview/start")
    assert resp.status_code == 200, resp.text

    answers = [
        ("fy_confirm",           "2024-25"),
        ("residency",            "resident"),
        ("employment_type",      "employee"),
        ("has_spouse",           "yes"),
        ("spouse_income_range",  "45000_120000"),
        ("spouse_novated_lease", "no"),
        ("has_dependents",       "no"),
        ("lodger_type",          "self"),
    ]
    for qid, answer in answers:
        resp = await client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, f"Answer failed for {qid}: {resp.text}"

    # Answer remaining skill questions
    body = resp.json()
    next_q = body["data"].get("next_question")
    while next_q is not None:
        qid = next_q["id"]
        options = next_q.get("options") or []
        answer = str(options[0]) if options else ("3" if next_q.get("type") == "number" else "yes")
        resp = await client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, f"Skill answer failed for {qid}: {resp.text}"
        next_q = resp.json()["data"].get("next_question")

    resp = await client.post("/api/v1/interview/complete")
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_jump_branch_question(auth_client):
    """Jump to a branch question (spouse_income_range) succeeds."""
    await _complete_interview_with_spouse(auth_client)

    resp = await auth_client.post(
        "/api/v1/interview/jump",
        json={"question_id": "spouse_income_range"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["state"] == "in_progress"
    assert body["data"]["current_question"]["id"] == "spouse_income_range"


@pytest.mark.asyncio
async def test_jump_skill_question(auth_client):
    """Jump to a skill question (wfh from employee_tax_au) succeeds."""
    await _complete_full_interview(auth_client)

    resp = await auth_client.post(
        "/api/v1/interview/jump",
        json={"question_id": "wfh"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["state"] == "in_progress"
    assert body["data"]["current_question"]["id"] == "wfh"


@pytest.mark.asyncio
async def test_summary_includes_skill_questions(auth_client):
    """GET /interview/summary includes skill section with wfh answers."""
    await _complete_full_interview(auth_client)

    resp = await auth_client.get("/api/v1/interview/summary")
    assert resp.status_code == 200, resp.text
    sections = resp.json()["data"]["sections"]

    titles = [s["title"] for s in sections]
    assert "Your employment" in titles, f"Expected 'Your employment' section, got: {titles}"

    emp_section = next(s for s in sections if s["title"] == "Your employment")
    answer_ids = [a["question_id"] for a in emp_section["answers"]]
    assert "wfh" in answer_ids, f"Expected 'wfh' in skill answers, got: {answer_ids}"

    for ans in emp_section["answers"]:
        assert ans["question_label"], (
            f"Skill answer {ans['question_id']} has empty question_label"
        )


@pytest.mark.asyncio
async def test_jump_safety_limit(auth_client):
    """Jump to the very first question (fy_confirm) succeeds — tests the safety limit
    allows traversing the full branch_path without hitting an artificial cap."""
    await _complete_full_interview(auth_client)

    resp = await auth_client.post(
        "/api/v1/interview/jump",
        json={"question_id": "fy_confirm"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["state"] == "in_progress"
    assert body["data"]["current_question"]["id"] == "fy_confirm"


@pytest.mark.asyncio
async def test_summary_wfh_skill_values_formatted(auth_client):
    """Skill answer 'yes_regular' → 'Yes, regularly'; 'fixed_rate' → 'Fixed rate (67c per hour)'."""
    await _complete_full_interview(auth_client)

    resp = await auth_client.get("/api/v1/interview/summary")
    assert resp.status_code == 200, resp.text
    sections = resp.json()["data"]["sections"]

    emp_section = next((s for s in sections if s["title"] == "Your employment"), None)
    assert emp_section is not None, f"Expected 'Your employment' section, got: {[s['title'] for s in sections]}"

    answers_by_id = {a["question_id"]: a for a in emp_section["answers"]}

    assert "wfh" in answers_by_id, f"Expected 'wfh' in skill answers, got: {list(answers_by_id)}"
    wfh_label = answers_by_id["wfh"]["answer_label"]
    assert wfh_label == "Yes, regularly", (
        f"Expected 'Yes, regularly', got '{wfh_label}'"
    )

    if "wfh_method" in answers_by_id:
        method_label = answers_by_id["wfh_method"]["answer_label"]
        assert method_label == "Fixed rate (67c per hour)", (
            f"Expected 'Fixed rate (67c per hour)', got '{method_label}'"
        )


@pytest.mark.asyncio
async def test_jump_edit_mode_sets_flags(auth_client):
    """POST /interview/jump with edit_mode=true sets session into edit mode."""
    await _complete_full_interview(auth_client)

    resp = await auth_client.post(
        "/api/v1/interview/jump",
        json={"question_id": "residency", "edit_mode": True},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["state"] == "in_progress"
    assert body["data"]["current_question"]["id"] == "residency"
    assert body["data"]["edit_mode"] is True


@pytest.mark.asyncio
async def test_edit_mode_returns_to_completion_after_one_answer(auth_client):
    """In edit_mode, answering the target question returns state=awaiting_evidence immediately."""
    await _complete_full_interview(auth_client)

    # Jump to residency in edit_mode
    resp = await auth_client.post(
        "/api/v1/interview/jump",
        json={"question_id": "residency", "edit_mode": True},
    )
    assert resp.status_code == 200, resp.text

    # Answer residency — must return to awaiting_evidence without further questions
    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "residency", "answer": "resident"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["state"] == "awaiting_evidence"
    assert body["data"]["next_question"] is None


@pytest.mark.asyncio
async def test_edit_mode_with_branches_asks_branches_before_returning(auth_client):
    """In edit_mode, editing an answer that triggers branches must ask those branches
    before returning state=awaiting_evidence. Regression for edit_mode branch wipe bug."""
    await _complete_full_interview(auth_client)

    # Jump to has_spouse in edit_mode
    resp = await auth_client.post(
        "/api/v1/interview/jump",
        json={"question_id": "has_spouse", "edit_mode": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["edit_mode"] is True

    # Answer has_spouse = "yes" — this triggers spouse branch questions
    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "has_spouse", "answer": "yes"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Must still be in_progress — branch questions must be asked first
    assert body["data"]["state"] == "in_progress", (
        f"Expected in_progress while asking branches, got {body['data']['state']}"
    )
    assert body["data"]["next_question"]["id"] == "spouse_income_range"

    # Answer the branch questions
    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "spouse_income_range", "answer": "45000_120000"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["next_question"]["id"] == "spouse_novated_lease"

    resp = await auth_client.post(
        "/api/v1/interview/answer",
        json={"question_id": "spouse_novated_lease", "answer": "no"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Branches exhausted — now returns to completion
    assert body["data"]["state"] == "awaiting_evidence"
    assert body["data"]["next_question"] is None


@pytest.mark.asyncio
async def test_summary_yes_no_strings_formatted(auth_client):
    """Skill section answers with raw 'yes'/'no' are returned as 'Yes'/'No'."""
    await _complete_full_interview(auth_client)

    resp = await auth_client.get("/api/v1/interview/summary")
    assert resp.status_code == 200, resp.text
    sections = resp.json()["data"]["sections"]

    for section in sections:
        if section["title"] == "Your situation":
            continue
        for ans in section["answers"]:
            val = ans["answer_value"]
            label = ans["answer_label"]
            if val in ("yes", "no"):
                assert label in ("Yes", "No"), (
                    f"Question '{ans['question_id']}': raw '{val}' should be "
                    f"formatted as 'Yes'/'No', got '{label}'"
                )
