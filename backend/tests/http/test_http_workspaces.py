import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest.mark.asyncio
async def test_select_workspace_switches_cookie_context(auth_client, test_engine):
    from app.db.models import Workspace

    create = await auth_client.post(
        "/api/v1/workspaces",
        json={"name": "FY 2025-26", "financial_year": "2025-26"},
    )
    assert create.status_code == 200, create.text
    target = create.json()["data"]

    auth_client.cookies.set("session", auth_client.cookies.get("session"))
    resp = await auth_client.post(f"/api/v1/workspaces/{target['id']}/select")
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["id"] == target["id"]
    assert body["financial_year"] == "2025-26"

    session_status = await auth_client.get("/api/v1/auth/session")
    assert session_status.status_code == 200, session_status.text
    assert session_status.json()["data"]["workspace_id"] == target["id"]
    assert session_status.json()["data"]["financial_year"] == "2025-26"


@pytest.mark.asyncio
async def test_select_workspace_rejects_archived_workspace(auth_client, test_engine):
    from app.db.models import Workspace

    create = await auth_client.post(
        "/api/v1/workspaces",
        json={"name": "FY 2025-26", "financial_year": "2025-26"},
    )
    assert create.status_code == 200, create.text
    target_id = create.json()["data"]["id"]

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        ws = (await session.execute(select(Workspace).where(Workspace.id == target_id))).scalar_one()
        ws.status = "archived"
        await session.commit()

    resp = await auth_client.post(f"/api/v1/workspaces/{target_id}/select")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "not_found"
