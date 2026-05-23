import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import ReviewItem, TaxEvent

TEST_PASSWORD = "test-password-m2"

# ── unlocked_client ──────────────────────────────────────────────────────────
# auth_client that has also called /auth/unlock (carries unlock_session cookie).

@pytest_asyncio.fixture
async def unlocked_client(auth_client):
    """auth_client extended with a valid unlock_session cookie."""
    resp = await auth_client.post(
        "/api/v1/auth/unlock",
        json={"password": TEST_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    yield auth_client


# ── review_item_id ────────────────────────────────────────────────────────────
# Inserts a ReviewItem + TaxEvent directly into the DB so review action
# tests have an item to act on without needing full evidence extraction.

@pytest_asyncio.fixture
async def review_item_id(auth_client, test_engine) -> str:
    """Insert a ReviewItem into the test DB and return its id."""
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = TaxEvent(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            event_type="income",
            category="payg_income",
            description="Smoke test salary income",
            amount=75000.0,
            status="needs_user_review",
        )
        session.add(event)
        await session.flush()

        item = ReviewItem(
            workspace_id=auth_client.workspace_id,
            tax_event_id=event.id,
            title="Salary income",
            category="payg_income",
            amount=75000.0,
            status="needs_user_review",
        )
        session.add(item)
        await session.commit()
        return item.id


# ── bulk_review_item_ids ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def bulk_review_item_ids(auth_client, test_engine) -> list[str]:
    """Insert 3 ReviewItems and return their ids."""
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    ids = []
    async with maker() as session:
        for i in range(3):
            event = TaxEvent(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                event_type="deduction",
                category="work_expense",
                description=f"Bulk test expense {i}",
                amount=float(100 * (i + 1)),
                status="needs_user_review",
            )
            session.add(event)
            await session.flush()
            item = ReviewItem(
                workspace_id=auth_client.workspace_id,
                tax_event_id=event.id,
                title=f"Work expense {i}",
                category="work_expense",
                amount=float(100 * (i + 1)),
                status="needs_user_review",
            )
            session.add(item)
            await session.flush()
            ids.append(item.id)
        await session.commit()
    return ids


# ── eligible_client ───────────────────────────────────────────────────────────
# auth_client that satisfies all export eligibility conditions:
#   1. Interview state = awaiting_evidence or complete
#   2. At least one confirmed TaxEvent in DB
#   3. No documents with status = "processing"

@pytest_asyncio.fixture
async def eligible_client(auth_client, test_engine):
    """auth_client with interview complete + 1 confirmed event. No processing docs."""
    # Complete the interview
    await auth_client.post("/api/v1/interview/start")
    for qid, answer in [
        ("fy_confirm", "2024-25"),
        ("residency", "resident"),
        ("employment_type", "employee"),
        ("family_situation", "single_no_dependents"),
        ("lodger_type", "self"),
    ]:
        await auth_client.post(
            "/api/v1/interview/answer",
            json={"question_id": qid, "answer": answer},
        )
    await auth_client.post("/api/v1/interview/complete")

    # Insert a confirmed TaxEvent directly (bypasses AI extraction)
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = TaxEvent(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            event_type="income",
            category="payg_income",
            description="PAYG salary",
            amount=75000.0,
            status="confirmed",
        )
        session.add(event)
        await session.commit()

    yield auth_client
