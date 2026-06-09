"""
Golden path scenario test.

Exercises the complete user journey against the real ASGI stack:
  setup (via auth_client fixture) → interview → review → readiness → export eligibility

Document upload is skipped to avoid the background-task dependency;
TaxEvents are inserted directly into the DB to simulate confirmed evidence.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import ReviewItem, TaxEvent


@pytest.mark.asyncio
async def test_complete_user_journey(auth_client, test_engine):
    """Full scenario: setup → interview → review → readiness → export eligibility."""

    # ── Step 1: Verify setup state ────────────────────────────────────────────
    # auth_client fixture already completed setup + confirm + login.
    # Session endpoint returns {"data": {"workspace_id": ..., "setup_confirmed": ...}}
    # (no "is_authenticated" field — check setup_confirmed instead)
    session_resp = await auth_client.get("/api/v1/auth/session")
    assert session_resp.status_code == 200
    assert session_resp.json()["data"]["setup_confirmed"] is True

    # ── Step 2: Start and complete the interview ──────────────────────────────
    start = await auth_client.post("/api/v1/interview/start")
    assert start.status_code == 200
    assert start.json()["data"]["state"] == "in_progress"

    for qid, answer in [
        ("residency", "resident"),
        ("employment_type", "employee"),
        ("has_spouse", "no"),
        ("has_dependents", "no"),
        ("lodger_type", "self"),
    ]:
        resp = await auth_client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
        assert resp.status_code == 200, f"Failed on question {qid}: {resp.text}"

    complete = await auth_client.post("/api/v1/interview/complete")
    assert complete.status_code == 200
    assert complete.json()["data"]["state"] == "awaiting_evidence"

    # ── Step 3: Simulate document evidence (direct DB insert) ─────────────────
    # Background extraction is not executed by test client, so we insert
    # TaxEvents directly to simulate a document being processed.
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = TaxEvent(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            event_type="income",
            category="payg_income",
            description="PAYG salary from employer",
            amount=85000.0,
            status="needs_user_review",
        )
        session.add(event)
        await session.flush()

        item = ReviewItem(
            workspace_id=auth_client.workspace_id,
            tax_event_id=event.id,
            title="Salary income",
            category="payg_income",
            amount=85000.0,
            status="needs_user_review",
            questions_complete=True,
        )
        session.add(item)
        await session.commit()
        result_item_id = item.id

    # ── Step 4: Check review queue and confirm the item ───────────────────────
    queue = await auth_client.get("/api/v1/review/queue")
    assert queue.status_code == 200
    needs_review = queue.json()["data"]["needs_review"]["items"]
    assert any(i["id"] == result_item_id for i in needs_review), (
        "Review item not found in needs_review bucket"
    )

    # Capture readiness before confirm
    readiness_before_resp = await auth_client.get("/api/v1/readiness")
    assert readiness_before_resp.status_code == 200
    percentage_before = readiness_before_resp.json()["data"]["percentage"]

    confirm = await auth_client.post(
        f"/api/v1/review/{result_item_id}/action",
        json={"action": "confirmed"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["data"]["status"] == "confirmed"

    # ── Step 5: Recalculate readiness and verify percentage did not decrease ──
    recalc = await auth_client.post("/api/v1/readiness/recalculate")
    assert recalc.status_code == 200

    readiness_after_resp = await auth_client.get("/api/v1/readiness")
    assert readiness_after_resp.status_code == 200
    readiness_data = readiness_after_resp.json()["data"]
    assert "percentage" in readiness_data
    percentage_after = readiness_data["percentage"]
    assert isinstance(percentage_after, (int, float))
    # Confirming an event should never decrease readiness
    assert percentage_after >= percentage_before

    # ── Step 6: Check export eligibility ─────────────────────────────────────
    # We have: interview complete + confirmed event + no processing docs
    # → should be eligible
    eligibility = await auth_client.get("/api/v1/export/eligibility")
    assert eligibility.status_code == 200
    elig_data = eligibility.json()["data"]
    assert "can_export" in elig_data
    assert elig_data["can_export"] is True, (
        f"Expected can_export=True. Blocking reasons: {elig_data['blocking_reasons']}"
    )

    # ── Consistency check ─────────────────────────────────────────────────────
    # The confirmed event should appear in estimator totals
    summary = await auth_client.get("/api/v1/estimator/summary")
    assert summary.status_code == 200
    estimator_data = summary.json()["data"]
    assert float(estimator_data["gross_income"]) > 0, (
        "Expected gross_income > 0 after confirming a payg_income event"
    )
