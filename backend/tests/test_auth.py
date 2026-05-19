import pytest
from app.security import (
    generate_dek,
    encrypt_dek,
    decrypt_dek,
    generate_recovery_key,
    normalize_recovery_key,
    make_unlock_token,
    extract_dek_from_token,
    encrypt_for_draft,
    decrypt_from_draft,
)


def test_generate_dek_is_32_bytes():
    dek = generate_dek()
    assert len(dek) == 32
    assert isinstance(dek, bytes)


def test_generate_dek_is_random():
    assert generate_dek() != generate_dek()


def test_encrypt_decrypt_dek_roundtrip():
    dek = generate_dek()
    encrypted = encrypt_dek(dek, "my-passphrase")
    assert decrypt_dek(encrypted, "my-passphrase") == dek


def test_decrypt_dek_wrong_passphrase_raises():
    dek = generate_dek()
    encrypted = encrypt_dek(dek, "correct")
    with pytest.raises(Exception):
        decrypt_dek(encrypted, "wrong")


def test_recovery_key_format():
    key = generate_recovery_key()
    parts = key.split(" / ")
    assert len(parts) == 2
    for part in parts:
        segments = part.split("-")
        assert len(segments) == 4
        for seg in segments:
            assert len(seg) == 4
            assert all(c in "0123456789ABCDEF" for c in seg)


def test_normalize_recovery_key():
    key = "ABCD-EF01-2345-6789 / ABCD-EF01-2345-6789"
    assert normalize_recovery_key(key) == "ABCDEF0123456789ABCDEF0123456789"


def test_encrypt_decrypt_dek_with_recovery_key():
    dek = generate_dek()
    rk = generate_recovery_key()
    normalized = normalize_recovery_key(rk)
    encrypted = encrypt_dek(dek, normalized)
    assert decrypt_dek(encrypted, normalized) == dek


def test_unlock_token_roundtrip():
    dek = generate_dek()
    token = make_unlock_token(dek, "server-secret-key")
    assert extract_dek_from_token(token, "server-secret-key") == dek


def test_unlock_token_wrong_secret_raises():
    dek = generate_dek()
    token = make_unlock_token(dek, "correct-secret")
    with pytest.raises(Exception):
        extract_dek_from_token(token, "wrong-secret")


def test_draft_encrypt_decrypt_roundtrip():
    dek = generate_dek()
    content = {"field": "value", "amount": 123}
    encrypted = encrypt_for_draft(content, dek)
    assert decrypt_from_draft(encrypted, dek) == content


def test_draft_decrypt_wrong_dek_raises():
    dek = generate_dek()
    encrypted = encrypt_for_draft({"x": 1}, dek)
    with pytest.raises(Exception):
        decrypt_from_draft(encrypted, generate_dek())


from tests.conftest import TEST_PASSWORD


# ── login / logout / session ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_correct_password_sets_cookie(client, patch_password):
    await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    resp = await client.post("/api/v1/auth/login", json={"password": TEST_PASSWORD})
    assert resp.status_code == 200
    assert "session" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client, patch_password):
    await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    resp = await client.post("/api/v1/auth/login", json={"password": "wrong-password"})
    assert resp.status_code == 401
    assert "session" not in resp.cookies


@pytest.mark.asyncio
async def test_logout_clears_both_cookies(auth_client):
    # Unlock to get both cookies set
    await auth_client.post(
        "/api/v1/auth/unlock",
        json={"password": TEST_PASSWORD},
    )
    resp = await auth_client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert resp.cookies.get("session") in (None, "")
    assert resp.cookies.get("unlock_session") in (None, "")


@pytest.mark.asyncio
async def test_session_endpoint_authenticated(auth_client):
    resp = await auth_client.get("/api/v1/auth/session")
    assert resp.status_code == 200
    assert resp.json()["authenticated"] is True


@pytest.mark.asyncio
async def test_session_endpoint_unauthenticated(client):
    resp = await client.get("/api/v1/auth/session")
    assert resp.status_code == 401


# ── setup ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_setup_creates_workspace_security(client, patch_password):
    login = await client.post("/api/v1/auth/login", json={"password": TEST_PASSWORD})
    assert login.status_code == 200

    resp = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "recovery_key" in body
    assert "workspace_id" in body
    assert " / " in body["recovery_key"]


@pytest.mark.asyncio
async def test_setup_populates_dek_fields(client, patch_password):
    from sqlalchemy import select
    from app.db.models import WorkspaceSecurity

    login = await client.post("/api/v1/auth/login", json={"password": TEST_PASSWORD})
    assert login.status_code == 200

    setup = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    workspace_id = setup.json()["workspace_id"]

    from app.db.base import get_db
    db_override = client.app.dependency_overrides[get_db]
    async for db in db_override():
        row = (
            await db.execute(
                select(WorkspaceSecurity).where(
                    WorkspaceSecurity.workspace_id == workspace_id
                )
            )
        ).scalar_one()
        assert row.password_hash is not None
        assert row.password_encrypted_dek is not None
        assert row.recovery_key_hash is not None
        assert row.recovery_encrypted_dek is not None
        break


@pytest.mark.asyncio
async def test_setup_twice_returns_409(client, patch_password):
    resp1 = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert resp1.status_code == 200

    resp2 = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert resp2.status_code == 409
    assert resp2.json()["detail"]["error_code"] == "already_setup"


# ── recover ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recover_reencrypts_dek(auth_client, patch_password):
    workspace_id = auth_client.workspace_id
    recovery_key = auth_client.recovery_key
    new_password = "new-password-after-recovery"

    resp = await auth_client.post(
        "/api/v1/auth/recover",
        json={
            "workspace_id": workspace_id,
            "recovery_key": recovery_key,
            "new_password": new_password,
        },
    )
    assert resp.status_code == 200

    login = await auth_client.post(
        "/api/v1/auth/login", json={"password": new_password}
    )
    assert login.status_code == 200


# ── unlock session expiry ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unlock_expired_returns_401(auth_client, patch_password):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import update
    from app.db.models import WorkspaceSecurity
    from app.db.base import get_db

    workspace_id = auth_client.workspace_id

    # Unlock to get both cookies
    unlock = await auth_client.post(
        "/api/v1/auth/unlock",
        json={"password": TEST_PASSWORD},
    )
    assert unlock.status_code == 200
    assert "unlock_session" in unlock.cookies

    # Expire the server-side unlock record directly in the DB
    db_override = auth_client.app.dependency_overrides[get_db]
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    async for db in db_override():
        await db.execute(
            update(WorkspaceSecurity)
            .where(WorkspaceSecurity.workspace_id == workspace_id)
            .values(unlock_session_expires=past)
        )
        await db.commit()
        break

    # Draft endpoint should now return 401 despite unlock_session cookie being present
    resp = await auth_client.get("/api/v1/drafts/tax_profile")
    assert resp.status_code == 401
