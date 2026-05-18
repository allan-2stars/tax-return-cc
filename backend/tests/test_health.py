from unittest.mock import AsyncMock, patch

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
    assert "db" in body
    assert "storage" in body


@pytest.mark.asyncio
async def test_health_storage_degraded_still_200(client, missing_storage_settings):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["storage"] != "ok"


@pytest.mark.asyncio
async def test_health_db_unreachable_still_200(client):
    with patch("app.repositories.health.ping", new_callable=AsyncMock, return_value=False):
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["db"] == "error"
