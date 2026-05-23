"""HTTP smoke tests for /review route group."""
import pytest


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
