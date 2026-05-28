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
async def test_login_session_cookie_ttl_is_one_day(client, patch_password):
    await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    resp = await client.post("/api/v1/auth/login", json={"password": TEST_PASSWORD})
    assert resp.status_code == 200

    cookie_headers = resp.headers.get_list("set-cookie")
    session_cookie = next((h for h in cookie_headers if h.startswith("session=")), "")
    assert "Max-Age=86400" in session_cookie


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
    assert resp.json()["status"] == "ok"
    assert "data" in resp.json()
    assert "workspace_id" in resp.json()["data"]


@pytest.mark.asyncio
async def test_session_endpoint_no_workspace_returns_setup_required(client):
    # Fresh DB with no workspace → first-run signal
    resp = await client.get("/api/v1/auth/session")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["setup_required"] is True
    assert data["authenticated"] is False


@pytest.mark.asyncio
async def test_session_endpoint_unauthenticated_with_workspace_returns_401(client):
    # Workspace exists but no session cookie → 401
    await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    client.cookies.clear()
    resp = await client.get("/api/v1/auth/session")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_session_endpoint_cookie_workspace_missing_returns_401(client, patch_password):
    """If session cookie references a workspace_id that does not exist, /auth/session must not return ok."""
    from app.api.dependencies import sign_session

    # Create a real workspace so the endpoint does not return setup_required.
    setup = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert setup.status_code == 200

    client.cookies.set("session", sign_session("00000000-0000-0000-0000-000000000000"))
    resp = await client.get("/api/v1/auth/session")
    assert resp.status_code == 401
    assert resp.json()["detail"]["error_code"] == "invalid_session"


# ── setup ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_setup_creates_workspace_security(client, patch_password):
    resp = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert "recovery_key" in body
    assert "workspace_id" in body
    assert " / " in body["recovery_key"]


@pytest.mark.asyncio
async def test_setup_populates_dek_fields(client, patch_password):
    from sqlalchemy import select
    from app.db.models import WorkspaceSecurity

    setup = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    workspace_id = setup.json()["data"]["workspace_id"]

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
async def test_setup_reentry_when_unconfirmed_returns_200(client, patch_password):
    # First setup — workspace created, setup_confirmed=False
    resp1 = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert resp1.status_code == 200

    # Second setup without confirming — allowed (incomplete first-run)
    resp2 = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert resp2.status_code == 200
    assert "recovery_key" in resp2.json()["data"]


@pytest.mark.asyncio
async def test_setup_after_confirmed_returns_409(client, patch_password):
    from app.security import normalize_recovery_key

    # Setup and fully confirm
    setup = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert setup.status_code == 200
    last_8 = normalize_recovery_key(setup.json()["data"]["recovery_key"])[-8:]
    await client.post(
        "/api/v1/auth/setup/confirm",
        json={"confirmation": f"{last_8[:4]}-{last_8[4:]}"},
    )

    # Now re-setup must be blocked
    resp = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["error_code"] == "already_setup"


# ── recover ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recover_reencrypts_dek(auth_client, patch_password):
    recovery_key = auth_client.recovery_key
    new_password = "new-password-after-recovery"

    resp = await auth_client.post(
        "/api/v1/auth/recover",
        json={
            "recovery_key": recovery_key,
            "new_password": new_password,
        },
    )
    assert resp.status_code == 200

    login = await auth_client.post(
        "/api/v1/auth/login", json={"password": new_password}
    )
    assert login.status_code == 200


# ── recover (no workspace_id) ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recover_without_workspace_id_reencrypts_dek(auth_client, patch_password):
    """
    Recovery is a pre-auth flow: client should not need to know workspace_id.
    Backend must infer the singleton workspace.
    """
    recovery_key = auth_client.recovery_key
    new_password = "new-password-after-recovery-no-ws"

    resp = await auth_client.post(
        "/api/v1/auth/recover",
        json={
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


# ── drafts ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_draft_save_and_retrieve(auth_client, patch_password):
    unlock = await auth_client.post(
        "/api/v1/auth/unlock",
        json={"password": TEST_PASSWORD},
    )
    assert unlock.status_code == 200
    assert "unlock_session" in unlock.cookies

    content = {"name": "Allan", "income": 95000}

    save_resp = await auth_client.post(
        "/api/v1/drafts/tax_profile",
        json={"content": content},
    )
    assert save_resp.status_code == 200

    get_resp = await auth_client.get("/api/v1/drafts/tax_profile")
    assert get_resp.status_code == 200
    assert get_resp.json()["content"] == content


@pytest.mark.asyncio
async def test_draft_requires_unlock(auth_client):
    # No unlock performed — unlock_session cookie absent
    resp = await auth_client.get("/api/v1/drafts/tax_profile")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_draft_invalid_form_type_returns_422(auth_client, patch_password):
    await auth_client.post(
        "/api/v1/auth/unlock",
        json={"password": TEST_PASSWORD},
    )
    resp = await auth_client.post(
        "/api/v1/drafts/invalid_type",
        json={"content": {}},
    )
    assert resp.status_code == 422


# ── setup confirmation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_setup_confirm_correct_chars(client, patch_password):
    from app.security import normalize_recovery_key

    setup = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert setup.status_code == 200
    recovery_key = setup.json()["data"]["recovery_key"]

    last_8 = normalize_recovery_key(recovery_key)[-8:]
    resp = await client.post(
        "/api/v1/auth/setup/confirm",
        json={"confirmation": f"{last_8[:4]}-{last_8[4:]}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_setup_confirm_wrong_chars_returns_400(client, patch_password):
    await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    resp = await client.post(
        "/api/v1/auth/setup/confirm",
        json={"confirmation": "0000-0000"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_require_auth_blocks_before_confirm(client, patch_password):
    # After setup but before confirm, protected endpoints must return 403
    setup = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert setup.status_code == 200
    # session cookie is set by setup — client is authenticated but NOT confirmed
    resp = await client.get("/api/v1/auth/session")
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "setup_not_confirmed"


@pytest.mark.asyncio
async def test_recover_wrong_key_returns_401(auth_client, patch_password):
    resp = await auth_client.post(
        "/api/v1/auth/recover",
        json={
            "recovery_key": "WRONG-WRONG-WRONG-WRONG / WRONG-WRONG-WRONG-WRONG",
            "new_password": "some-new-password",
        },
    )
    assert resp.status_code == 401

    # Verify old password still works (data unchanged)
    login = await auth_client.post(
        "/api/v1/auth/login", json={"password": TEST_PASSWORD}
    )
    assert login.status_code == 200
