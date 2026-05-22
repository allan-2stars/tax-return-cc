import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.conftest import TEST_PASSWORD


@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with maker() as session:
        yield session


@pytest.mark.asyncio
async def test_change_password_success(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": "new-password-99"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    login = await auth_client.post(
        "/api/v1/auth/login", json={"password": "new-password-99"}
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong-password", "new_password": "new-password-99"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["error_code"] == "invalid_password"


@pytest.mark.asyncio
async def test_change_password_dek_still_decryptable(auth_client, db_session):
    from app.repositories import auth as auth_repo
    from app.security import decrypt_dek

    resp = await auth_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": "changed-pw-123"},
    )
    assert resp.status_code == 200

    ws = await auth_repo.get_security(db_session, auth_client.workspace_id)
    dek = decrypt_dek(ws.password_encrypted_dek, "changed-pw-123")
    assert len(dek) == 32


@pytest.mark.asyncio
async def test_regenerate_recovery_key_returns_new_key(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/recovery-key/regenerate",
        json={"password": TEST_PASSWORD},
    )
    assert resp.status_code == 200
    new_key = resp.json()["data"]["recovery_key"]
    assert " / " in new_key
    assert "-" in new_key


@pytest.mark.asyncio
async def test_regenerate_recovery_key_wrong_password(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/recovery-key/regenerate",
        json={"password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_regenerate_recovery_key_old_key_invalid(auth_client):
    original_key = auth_client.recovery_key

    resp = await auth_client.post(
        "/api/v1/auth/recovery-key/regenerate",
        json={"password": TEST_PASSWORD},
    )
    assert resp.status_code == 200

    recover_resp = await auth_client.post(
        "/api/v1/auth/recover",
        json={
            "recovery_key": original_key,
            "new_password": "should-fail",
            "workspace_id": auth_client.workspace_id,
        },
    )
    assert recover_resp.status_code == 401


@pytest.mark.asyncio
async def test_change_password_clears_unlock_session(auth_client, db_session):
    # First unlock to set the token
    await auth_client.post("/api/v1/auth/unlock", json={"password": TEST_PASSWORD})

    from app.repositories import auth as auth_repo
    ws_before = await auth_repo.get_security(db_session, auth_client.workspace_id)
    assert ws_before.unlock_session_token is not None

    await auth_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": "new-secure-pw-1"},
    )

    # Refresh from DB
    await db_session.refresh(ws_before)
    assert ws_before.unlock_session_token is None
    assert ws_before.unlock_session_expires is None


@pytest.mark.asyncio
async def test_regenerate_recovery_key_dek_unchanged(auth_client, db_session):
    """DEK bytes are preserved — only the key wrapping changes."""
    from app.repositories import auth as auth_repo
    from app.security import decrypt_dek, normalize_recovery_key

    # Get DEK under original password before regeneration
    ws = await auth_repo.get_security(db_session, auth_client.workspace_id)
    original_dek = decrypt_dek(ws.password_encrypted_dek, TEST_PASSWORD)

    resp = await auth_client.post(
        "/api/v1/auth/recovery-key/regenerate",
        json={"password": TEST_PASSWORD},
    )
    assert resp.status_code == 200
    new_key = resp.json()["data"]["recovery_key"]

    # Refresh and verify DEK via the NEW recovery key
    await db_session.refresh(ws)
    normalized = normalize_recovery_key(new_key)
    new_dek = decrypt_dek(ws.recovery_encrypted_dek, normalized)
    assert new_dek == original_dek


# ── settings endpoints ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_usage_returns_aggregation(auth_client, db_session):
    from datetime import datetime, timezone
    from app.db.models import AuditLog

    for _ in range(3):
        db_session.add(AuditLog(
            workspace_id=auth_client.workspace_id,
            action="ai_interaction",
            actor="ai",
            ai_operation="classify",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.0005,
            ai_success=True,
            created_at=datetime.now(timezone.utc),
        ))
    await db_session.commit()

    resp = await auth_client.get("/api/v1/settings/ai-usage")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total_cost_usd" in data
    classify = next((i for i in data["items"] if i["operation"] == "classify"), None)
    assert classify is not None
    assert classify["calls"] == 3


@pytest.mark.asyncio
async def test_storage_usage_returns_byte_counts(auth_client):
    resp = await auth_client.get("/api/v1/settings/storage-usage")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "documents_bytes" in data
    assert "exports_bytes" in data
    assert "db_bytes" in data
    assert isinstance(data["documents_bytes"], int)
    assert isinstance(data["exports_bytes"], int)
    assert isinstance(data["db_bytes"], int)


@pytest.mark.asyncio
async def test_diagnostic_log_download(auth_client):
    resp = await auth_client.get("/api/v1/settings/diagnostic-log")
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    body = resp.json()
    assert "document_count" in body
    assert "event_count" in body
    assert "active_skills" in body
    assert "TFN" not in str(body)
    assert "password" not in str(body)


@pytest.mark.asyncio
async def test_settings_about_returns_skills_and_disclaimer(auth_client):
    resp = await auth_client.get("/api/v1/settings/about")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "active_skills" in data
    assert "disclaimer" in data
    assert "organise" in data["disclaimer"]
    assert isinstance(data["active_skills"], list)


# ── workspaces ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_workspaces_returns_current(auth_client):
    resp = await auth_client.get("/api/v1/workspaces")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["financial_year"] == "2024-25"
    assert "readiness_pct" in items[0]


@pytest.mark.asyncio
async def test_patch_workspace_name(auth_client):
    resp = await auth_client.patch(
        f"/api/v1/workspaces/{auth_client.workspace_id}",
        json={"name": "Updated Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_patch_workspace_wrong_id_returns_403(auth_client):
    resp = await auth_client.patch(
        "/api/v1/workspaces/other-workspace-id",
        json={"name": "Hacked"},
    )
    assert resp.status_code == 403
