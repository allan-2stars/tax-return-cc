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
