"""HTTP smoke tests for /export route group."""
import pytest


@pytest.mark.asyncio
async def test_eligibility_blocked(auth_client):
    """GET /export/eligibility returns can_export=False for fresh workspace (no interview)."""
    resp = await auth_client.get("/api/v1/export/eligibility")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["can_export"] is False
    assert len(body["data"]["blocking_reasons"]) > 0


@pytest.mark.asyncio
async def test_eligibility_ready(eligible_client):
    """GET /export/eligibility returns can_export=True when interview complete + confirmed event."""
    resp = await eligible_client.get("/api/v1/export/eligibility")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["can_export"] is True


@pytest.mark.asyncio
async def test_generate(eligible_client):
    """POST /export/generate returns 200 with export_id when eligible."""
    resp = await eligible_client.post(
        "/api/v1/export/generate",
        json={"password": "export-test-password"},
    )
    # Route always returns 200 — export runs as background task, failures update DB record
    assert resp.status_code == 200
    assert "export_id" in resp.json()["data"]


@pytest.mark.asyncio
async def test_export_history(auth_client):
    """GET /export/history returns 200 with a list."""
    resp = await auth_client.get("/api/v1/export/history")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
