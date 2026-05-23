"""HTTP smoke tests for /readiness route group."""
import pytest


@pytest.mark.asyncio
async def test_get_readiness(auth_client):
    """GET /readiness returns 200 with percentage field under data."""
    resp = await auth_client.get("/api/v1/readiness")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "percentage" in body["data"]
    assert isinstance(body["data"]["percentage"], int)


@pytest.mark.asyncio
async def test_get_missing(auth_client):
    """GET /readiness/missing returns 200 with available_now and available_after_fy keys."""
    resp = await auth_client.get("/api/v1/readiness/missing")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "available_now" in body["data"]
    assert "available_after_fy" in body["data"]
    assert isinstance(body["data"]["available_now"], list)
    assert isinstance(body["data"]["available_after_fy"], list)


@pytest.mark.asyncio
async def test_recalculate(auth_client):
    """POST /readiness/recalculate returns 200 with status=recalculating."""
    resp = await auth_client.post("/api/v1/readiness/recalculate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "recalculating"
