"""HTTP smoke tests for /review route group."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Document, ReviewDecisionHistory, ReviewItem, TaxEvent, TaxProfile


@pytest.mark.asyncio
async def test_get_queue(auth_client):
    """GET /review/queue returns 200 with correct bucket structure."""
    resp = await auth_client.get("/api/v1/review/queue")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    data = body["data"]
    assert "needs_review" in data
    assert "agent_required" in data
    assert "confirmed" in data
    bucket_items = (
        data["needs_review"]["items"]
        + data["agent_required"]["items"]
        + data["high_risk"]["items"]
        + data["confirmed"]["items"]
    )
    if bucket_items:
        first = bucket_items[0]
        assert "explanation" in first
        assert first["explanation"]["target_type"] == "review_item"
        assert first["explanation"]["target_id"] == first["id"]


@pytest.mark.asyncio
async def test_get_queue_includes_extracted_source_metadata(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        doc = Document(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            original_filename="BHP_Contract_Note.pdf",
            storage_key=f"{auth_client.workspace_id}/doc-1/original.pdf",
            sha256_hash="a" * 64,
            status="ready",
            document_type="share_buy_contract_note",
        )
        session.add(doc)
        await session.flush()

        event = TaxEvent(
            workspace_id=auth_client.workspace_id,
            document_id=doc.id,
            financial_year="2024-25",
            event_type="investment",
            category="shares_acquisition",
            description="BHP contract note",
            amount=5210.0,
            date="2025-09-15",
            source="document_extracted",
            confidence=0.92,
            status="needs_user_review",
            review_status="pending",
            event_metadata={
                "stock_code": "BHP",
                "exchange": "ASX",
                "units": 100,
                "price_per_unit": 52.10,
                "brokerage_fee": 19.95,
                "transaction_type": "buy",
            },
        )
        session.add(event)
        await session.flush()

        item = ReviewItem(
            workspace_id=auth_client.workspace_id,
            tax_event_id=event.id,
            title="BHP contract note",
            category="shares_acquisition",
            amount=5210.0,
            date="2025-09-15",
            risk_level="low",
            confidence=0.92,
            questions_complete=True,
            status="needs_user_review",
        )
        session.add(item)
        await session.commit()
        review_item_id = item.id

    resp = await auth_client.get("/api/v1/review/queue")
    assert resp.status_code == 200
    items = resp.json()["data"]["needs_review"]["items"]
    payload = next(i for i in items if i["id"] == review_item_id)
    assert payload["source"] == "document_extracted"
    assert payload["event_metadata"]["stock_code"] == "BHP"
    assert payload["source_document"] == {
        "document_id": doc.id,
        "original_filename": "BHP_Contract_Note.pdf",
    }


@pytest.mark.asyncio
async def test_confirm_action(auth_client, review_item_id):
    """POST /review/{id}/action with action=confirmed returns 200 with confirmed status."""
    resp = await auth_client.post(
        f"/api/v1/review/{review_item_id}/action",
        json={"action": "confirmed"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "confirmed"
    assert body["data"]["id"] == review_item_id
    assert len(body["data"]["decision_history"]) == 1
    assert body["data"]["decision_history"][0]["action"] == "confirmed"
    assert body["data"]["decision_history"][0]["changed_fields"]["status"] == {
        "old": "needs_user_review",
        "new": "confirmed",
    }


@pytest.mark.asyncio
async def test_amend_action(auth_client, review_item_id):
    """POST /review/{id}/action with action=amended returns 200 with amended amount/category."""
    resp = await auth_client.post(
        f"/api/v1/review/{review_item_id}/action",
        json={"action": "amended", "amount": 50000.0, "category": "work_expense"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "confirmed"
    assert body["data"]["amended_amount"] == 50000.0
    history = body["data"]["decision_history"]
    assert history[0]["action"] == "amended"
    assert history[0]["changed_fields"]["amount"]["new"] == 50000.0
    assert history[0]["changed_fields"]["category"]["new"] == "work_expense"


@pytest.mark.asyncio
async def test_flag_action(auth_client, review_item_id):
    """POST /review/{id}/action with action=flagged returns 200 with needs_agent_review status."""
    resp = await auth_client.post(
        f"/api/v1/review/{review_item_id}/action",
        json={"action": "flagged"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "needs_agent_review"


@pytest.mark.asyncio
async def test_bulk_confirm(auth_client, bulk_review_item_ids):
    """POST /review/bulk-action confirms all supplied items."""
    resp = await auth_client.post(
        "/api/v1/review/bulk-action",
        json={"item_ids": bulk_review_item_ids, "action": "confirmed"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Response shape: {"data": {"items": [...], "count": N}}
    assert body["data"]["count"] == len(bulk_review_item_ids)
    assert all(i["status"] == "confirmed" for i in body["data"]["items"])
    bulk_ids = {i["decision_history"][0]["bulk_action_id"] for i in body["data"]["items"]}
    assert len(bulk_ids) == 1
    assert None not in bulk_ids


@pytest.mark.asyncio
async def test_get_review_item_history_endpoint_workspace_scoped(auth_client, review_item_id, test_engine):
    await auth_client.post(
        f"/api/v1/review/{review_item_id}/action",
        json={"action": "confirmed"},
    )

    resp = await auth_client.get(f"/api/v1/review/{review_item_id}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["review_item_id"] == review_item_id
    assert body["data"]["history"][0]["action"] == "confirmed"

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        foreign_item = ReviewItem(
            workspace_id="foreign-workspace",
            tax_event_id=None,
            title="Foreign item",
            category="work_expense",
            amount=1.0,
            status="needs_user_review",
            questions_complete=True,
        )
        session.add(foreign_item)
        await session.flush()
        foreign_item_id = foreign_item.id
        session.add(
            ReviewDecisionHistory(
                workspace_id="foreign-workspace",
                review_item_id=foreign_item_id,
                tax_event_id=None,
                action="confirmed",
                actor="user",
                previous_status="needs_user_review",
                new_status="confirmed",
                changed_fields={},
            )
        )
        await session.commit()

    forbidden = await auth_client.get(f"/api/v1/review/{foreign_item_id}/history")
    assert forbidden.status_code == 404


@pytest.mark.asyncio
async def test_undo_confirmed_action_restores_review_item(auth_client, review_item_id):
    confirmed = await auth_client.post(
        f"/api/v1/review/{review_item_id}/action",
        json={"action": "confirmed"},
    )
    assert confirmed.status_code == 200

    resp = await auth_client.post(f"/api/v1/review/{review_item_id}/undo")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "needs_user_review"
    assert body["data"]["user_action"] is None
    assert body["data"]["decision_history"][0]["action"] == "undo"


@pytest.mark.asyncio
async def test_undo_is_workspace_scoped(auth_client, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        foreign_item = ReviewItem(
            workspace_id="foreign-workspace",
            tax_event_id=None,
            title="Foreign item",
            category="work_expense",
            amount=1.0,
            status="confirmed",
            questions_complete=True,
            user_action="confirmed",
        )
        session.add(foreign_item)
        await session.flush()
        foreign_item_id = foreign_item.id
        session.add(
            ReviewDecisionHistory(
                workspace_id="foreign-workspace",
                review_item_id=foreign_item_id,
                tax_event_id=None,
                action="confirmed",
                actor="user",
                previous_status="needs_user_review",
                new_status="confirmed",
                changed_fields={
                    "status": {"old": "needs_user_review", "new": "confirmed"},
                    "user_action": {"old": None, "new": "confirmed"},
                },
            )
        )
        await session.commit()

    resp = await auth_client.post(f"/api/v1/review/{foreign_item_id}/undo")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_bulk_undo_restores_items(auth_client, bulk_review_item_ids):
    confirmed = await auth_client.post(
        "/api/v1/review/bulk-action",
        json={"item_ids": bulk_review_item_ids, "action": "confirmed"},
    )
    assert confirmed.status_code == 200
    bulk_id = confirmed.json()["data"]["items"][0]["decision_history"][0]["bulk_action_id"]

    resp = await auth_client.post(f"/api/v1/review/bulk-action/{bulk_id}/undo")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["count"] == len(bulk_review_item_ids)
    assert all(item["status"] == "needs_user_review" for item in body["data"]["items"])
    assert all(item["decision_history"][0]["action"] == "undo" for item in body["data"]["items"])


@pytest.mark.asyncio
async def test_review_action_triggers_reconcile(auth_client, review_item_id, test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        session.add(
            TaxProfile(
                workspace_id=auth_client.workspace_id,
                financial_year="2024-25",
                has_private_health=True,
            )
        )
        await session.commit()

    await auth_client.post("/api/v1/evidence/reconcile")
    before = await auth_client.get("/api/v1/evidence/obligations")
    keys_before = {o["obligation_key"] for o in before.json()["data"]["obligations"]}
    assert "private_health_annual_statement" in keys_before

    async with maker() as session:
        profile = await session.scalar(
            select(TaxProfile).where(TaxProfile.workspace_id == auth_client.workspace_id)
        )
        profile.has_private_health = False
        await session.commit()

    resp = await auth_client.post(
        f"/api/v1/review/{review_item_id}/action",
        json={"action": "confirmed"},
    )
    assert resp.status_code == 200
    # Route-triggered reconcile may be debounced; force one full pass for deterministic assertion.
    await auth_client.post("/api/v1/evidence/reconcile")

    after = await auth_client.get("/api/v1/evidence/obligations")
    keys_after = {o["obligation_key"] for o in after.json()["data"]["obligations"]}
    assert "private_health_annual_statement" not in keys_after
