import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape(client):
    response = await client.get("/api/v1/health")
    body = response.json()
    assert body["status"] == "ok"
    assert "data" in body
    assert "db" in body["data"]
    assert "storage" in body["data"]


@pytest.mark.asyncio
async def test_health_storage_degraded_still_200(client, missing_storage_settings):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["storage"] != "ok"
