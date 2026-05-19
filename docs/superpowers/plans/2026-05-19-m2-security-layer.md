# M2 Security Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the full security layer — bcrypt auth, httpOnly session cookie, DEK + recovery key system, unlock session, and encrypted draft autosave.

**Architecture:** Single-user app with one master password. `APP_PASSWORD_HASH` in `.env` is the bootstrap credential used before first-run setup. `POST /auth/setup` creates a Workspace + WorkspaceSecurity record, generates a random 32-byte DEK encrypted two ways (with the password and with the recovery key), and returns the recovery key once in plaintext. After setup, login verifies against `WorkspaceSecurity.password_hash`. Unlock decrypts the DEK and re-encrypts it with the server `SECRET_KEY`, storing the result in DB; `require_unlock` decrypts it on demand. The DEK is never stored in plaintext, never logged, never returned in any API response.

**Tech Stack:** `bcrypt`, `cryptography` (Fernet + PBKDF2HMAC), `itsdangerous` (URLSafeTimedSerializer for session cookie), FastAPI Cookie/Request/Query, SQLAlchemy async, pytest-asyncio + httpx.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/security.py` | Create | Pure crypto utilities — no DB, no FastAPI imports |
| `backend/app/repositories/auth.py` | Create | WorkspaceSecurity + EncryptedDraft DB access |
| `backend/app/api/dependencies.py` | Create | `require_auth`, `require_unlock` FastAPI dependencies |
| `backend/app/api/routes/auth.py` | Replace stub | 6 auth endpoints |
| `backend/app/api/routes/drafts.py` | Create | 2 draft endpoints |
| `backend/app/api/__init__.py` | Modify | Register drafts router |
| `backend/tests/conftest.py` | Modify | Add auth fixtures (append, do not remove existing) |
| `backend/tests/test_auth.py` | Modify | Add integration tests (crypto unit tests already there) |
| `frontend/app/(auth)/login/page.tsx` | Replace stub | Minimal real login form |

---

## Task 1: `app/security.py` — Crypto utilities

**Files:**
- Create: `backend/app/security.py`
- Test: `backend/tests/test_auth.py` (crypto unit tests, already written in M2 kick-off)

### Design notes

- `encrypt_dek` derives a Fernet key from the passphrase using PBKDF2-SHA256 (480 000 iterations) and a fresh random 16-byte salt. Output is `base64url(salt[16] || fernet_token)` — self-contained, no separate salt storage needed.
- `make_unlock_token` re-encrypts the DEK with a Fernet key derived from `settings.SECRET_KEY` via SHA-256. The token is stored server-side in `WorkspaceSecurity.unlock_session_token`; it never leaves the server.
- Recovery key format: `XXXX-XXXX-XXXX-XXXX / XXXX-XXXX-XXXX-XXXX` (32 uppercase hex chars, dashes and slash for readability). The normalized form (strip all non-hex chars) is used as the DEK encryption passphrase.
- Draft content is encrypted with `Fernet(urlsafe_b64encode(dek))`.

- [ ] **Step 1: Write failing crypto unit tests**

Create `backend/tests/test_auth.py` with the following content (these are pure unit tests that need no DB or HTTP client):

```python
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
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
make test-file FILE=tests/test_auth.py
```

Expected: `ModuleNotFoundError: No module named 'app.security'`

- [ ] **Step 3: Create `backend/app/security.py`**

```python
import base64
import hashlib
import json
import os
import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_PBKDF2_ITERATIONS = 480_000


def generate_dek() -> bytes:
    return os.urandom(32)


def _pbkdf2_fernet(passphrase: str, salt: bytes) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return Fernet(key)


def encrypt_dek(dek: bytes, passphrase: str) -> str:
    """Returns base64url(salt[16] || fernet_token). Self-contained."""
    salt = os.urandom(16)
    token = _pbkdf2_fernet(passphrase, salt).encrypt(dek)
    return base64.urlsafe_b64encode(salt + token).decode()


def decrypt_dek(encrypted_str: str, passphrase: str) -> bytes:
    data = base64.urlsafe_b64decode(encrypted_str.encode())
    salt, token = data[:16], data[16:]
    return _pbkdf2_fernet(passphrase, salt).decrypt(token)


def generate_recovery_key() -> str:
    """Returns XXXX-XXXX-XXXX-XXXX / XXXX-XXXX-XXXX-XXXX (32 hex chars)."""
    raw = secrets.token_hex(16).upper()
    segs = [raw[i : i + 4] for i in range(0, 32, 4)]
    return f"{'-'.join(segs[:4])} / {'-'.join(segs[4:])}"


def normalize_recovery_key(key: str) -> str:
    """Strip all non-hex chars to get 32 uppercase hex chars."""
    return "".join(c for c in key.upper() if c in "0123456789ABCDEF")


def _server_fernet(secret: str) -> Fernet:
    key = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def make_unlock_token(dek: bytes, secret: str) -> str:
    """Encrypt DEK with server SECRET_KEY for server-side storage."""
    return _server_fernet(secret).encrypt(dek).decode()


def extract_dek_from_token(token: str, secret: str) -> bytes:
    return _server_fernet(secret).decrypt(token.encode())


def encrypt_for_draft(content: dict, dek: bytes) -> str:
    f = Fernet(base64.urlsafe_b64encode(dek))
    return f.encrypt(json.dumps(content).encode()).decode()


def decrypt_from_draft(encrypted: str, dek: bytes) -> dict:
    f = Fernet(base64.urlsafe_b64encode(dek))
    return json.loads(f.decrypt(encrypted.encode()).decode())
```

- [ ] **Step 4: Run crypto unit tests — expect all 11 to pass**

```bash
make test-file FILE=tests/test_auth.py
```

---

## Task 2: `app/repositories/auth.py` — DB access

**Files:**
- Create: `backend/app/repositories/auth.py`

No separate test step — this is exercised fully by the integration tests in Task 4.

- [ ] **Step 1: Create the repository**

```python
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EncryptedDraft, WorkspaceSecurity


async def get_security(db: AsyncSession, workspace_id: str) -> WorkspaceSecurity | None:
    result = await db.execute(
        select(WorkspaceSecurity).where(WorkspaceSecurity.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none()


async def create_security(
    db: AsyncSession,
    workspace_id: str,
    password_hash: str,
    password_encrypted_dek: str,
    recovery_key_hash: str,
    recovery_encrypted_dek: str,
) -> WorkspaceSecurity:
    ws = WorkspaceSecurity(
        workspace_id=workspace_id,
        password_hash=password_hash,
        password_encrypted_dek=password_encrypted_dek,
        recovery_key_hash=recovery_key_hash,
        recovery_encrypted_dek=recovery_encrypted_dek,
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return ws


async def update_security(db: AsyncSession, ws: WorkspaceSecurity, **fields) -> None:
    for key, value in fields.items():
        setattr(ws, key, value)
    ws.updated_at = datetime.now(timezone.utc)
    await db.commit()


async def get_draft(
    db: AsyncSession, workspace_id: str, form_type: str
) -> EncryptedDraft | None:
    result = await db.execute(
        select(EncryptedDraft).where(
            EncryptedDraft.workspace_id == workspace_id,
            EncryptedDraft.form_type == form_type,
        )
    )
    return result.scalar_one_or_none()


async def upsert_draft(
    db: AsyncSession, workspace_id: str, form_type: str, encrypted_content: str
) -> EncryptedDraft:
    draft = await get_draft(db, workspace_id, form_type)
    if draft is None:
        draft = EncryptedDraft(
            workspace_id=workspace_id,
            form_type=form_type,
            encrypted_content=encrypted_content,
        )
        db.add(draft)
    else:
        draft.encrypted_content = encrypted_content
        draft.last_saved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(draft)
    return draft
```

---

## Task 3: `app/api/dependencies.py` — Auth guards

**Files:**
- Create: `backend/app/api/dependencies.py`

### Design notes

- `require_auth` reads the `session` cookie, verifies it with `URLSafeTimedSerializer(settings.SECRET_KEY, salt="session")`, and returns the `workspace_id` embedded in the token payload. Raises 401 if missing, expired, or tampered.
- `require_unlock` reads `workspace_id` from the query string, loads `WorkspaceSecurity`, checks `unlock_session_expires > now`, decrypts `unlock_session_token` with the server secret, and returns the raw DEK bytes. Routes declare `dek: bytes = Depends(require_unlock)`.
- Session payload: `{"w": workspace_id}` (short key keeps the cookie compact).
- `sign_session` is exported so auth routes can mint cookies without importing itsdangerous directly.

- [ ] **Step 1: Create `backend/app/api/dependencies.py`**

```python
from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException, Query
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.base import get_db
from app.errors import error_response
from app.repositories import auth as auth_repo
from app.security import extract_dek_from_token


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt="session")


def sign_session(workspace_id: str) -> str:
    return _serializer().dumps({"w": workspace_id})


def verify_session_token(token: str) -> str:
    """Returns workspace_id or raises HTTPException 401."""
    max_age = settings.SESSION_MAX_AGE_DAYS * 86400
    try:
        data = _serializer().loads(token, max_age=max_age)
        return data["w"]
    except SignatureExpired:
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "session_expired",
                "Your session has expired. Please log in again.",
                retryable=False,
            ),
        )
    except (BadSignature, KeyError):
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "invalid_session",
                "Invalid session. Please log in again.",
                retryable=False,
            ),
        )


async def require_auth(session: str | None = Cookie(default=None)) -> str:
    """Returns workspace_id. Raises 401 if not authenticated."""
    if not session:
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "not_authenticated", "Authentication required.", retryable=False
            ),
        )
    return verify_session_token(session)


async def require_unlock(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
) -> bytes:
    """Returns raw DEK bytes. Raises 401 if unlock session absent or expired."""
    ws = await auth_repo.get_security(db, workspace_id)
    if not ws or not ws.unlock_session_token or not ws.unlock_session_expires:
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "not_unlocked",
                "Workspace is locked. Please unlock first.",
                retryable=False,
            ),
        )
    expires = ws.unlock_session_expires
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "unlock_expired",
                "Unlock session expired. Please unlock again.",
                retryable=False,
            ),
        )
    try:
        return extract_dek_from_token(ws.unlock_session_token, settings.SECRET_KEY)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "unlock_invalid", "Unlock session is invalid.", retryable=False
            ),
        )
```

---

## Task 4: Auth endpoints + integration tests

**Files:**
- Modify: `backend/app/api/routes/auth.py` (replace existing stub completely)
- Modify: `backend/tests/conftest.py` (append fixtures — do not remove existing ones)
- Modify: `backend/tests/test_auth.py` (append integration tests after crypto unit tests)

### Login flow detail

1. Query for any existing `Workspace`. If one exists, load its `WorkspaceSecurity`.
2. If `WorkspaceSecurity.password_hash` is populated, verify the incoming password against it.
3. If no `WorkspaceSecurity` exists yet (pre-setup state), fall back to `settings.APP_PASSWORD_HASH`. If that is also empty, return 503 with a message to generate a hash via `make shell-be`.
4. On success, sign a session cookie containing `{"w": workspace_id}`.

Cookie attributes: `httponly=True`, `secure=True` in production only (so dev browser can read it over HTTP), `samesite="strict"`, `max_age=SESSION_MAX_AGE_DAYS * 86400`.

- [ ] **Step 1: Append auth fixtures to `backend/tests/conftest.py`**

Add the following to the bottom of the existing file. Import `bcrypt` and `pytest_asyncio` are already present.

```python
import bcrypt

TEST_PASSWORD = "test-password-m2"


@pytest.fixture
def patch_password(monkeypatch):
    """Patch APP_PASSWORD_HASH and SECRET_KEY for deterministic tests."""
    from app.config import settings
    hashed = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    monkeypatch.setattr(settings, "APP_PASSWORD_HASH", hashed)
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-key-for-unit-tests")


@pytest_asyncio.fixture
async def auth_client(client, patch_password):
    """HTTP client with a valid session cookie (post-setup state)."""
    setup_resp = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert setup_resp.status_code == 200, setup_resp.text
    client.workspace_id = setup_resp.json()["workspace_id"]
    client.recovery_key = setup_resp.json()["recovery_key"]

    login_resp = await client.post(
        "/api/v1/auth/login", json={"password": TEST_PASSWORD}
    )
    assert login_resp.status_code == 200, login_resp.text
    yield client
```

- [ ] **Step 2: Append integration tests to `backend/tests/test_auth.py`**

```python
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
async def test_logout_clears_cookie(auth_client):
    resp = await auth_client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert resp.cookies.get("session") in (None, "")


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

    unlock = await auth_client.post(
        "/api/v1/auth/unlock",
        json={"password": TEST_PASSWORD, "workspace_id": workspace_id},
    )
    assert unlock.status_code == 200

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

    resp = await auth_client.get(
        f"/api/v1/drafts/tax_profile?workspace_id={workspace_id}"
    )
    assert resp.status_code == 401
```

- [ ] **Step 3: Run tests — confirm integration tests fail (stub routes return wrong shapes)**

```bash
make test-file FILE=tests/test_auth.py
```

Expected: crypto unit tests pass; integration tests fail.

- [ ] **Step 4: Replace `backend/app/api/routes/auth.py` with full implementation**

```python
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth, sign_session
from app.config import settings
from app.db.base import get_db
from app.db.models import Workspace
from app.errors import error_response
from app.repositories import auth as auth_repo
from app.security import (
    decrypt_dek,
    encrypt_dek,
    generate_dek,
    generate_recovery_key,
    make_unlock_token,
    normalize_recovery_key,
)

router = APIRouter()


def _cookie_secure() -> bool:
    return settings.ENVIRONMENT == "production"


class LoginRequest(BaseModel):
    password: str


class SetupRequest(BaseModel):
    password: str
    financial_year: str = "2024-25"


class UnlockRequest(BaseModel):
    password: str
    workspace_id: str


class RecoverRequest(BaseModel):
    recovery_key: str
    new_password: str
    workspace_id: str


@router.post("/auth/login")
async def login(
    body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    workspace = (await db.execute(select(Workspace).limit(1))).scalar_one_or_none()

    password_ok = False
    workspace_id_for_session = workspace.id if workspace else ""

    if workspace:
        ws_sec = await auth_repo.get_security(db, workspace.id)
        if ws_sec and ws_sec.password_hash:
            password_ok = bcrypt.checkpw(
                body.password.encode(), ws_sec.password_hash.encode()
            )

    if not password_ok:
        if not settings.APP_PASSWORD_HASH:
            raise HTTPException(
                status_code=503,
                detail=error_response(
                    "not_configured",
                    "No password configured. Run 'make shell-be' then: "
                    "python -c \"import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())\" "
                    "and set APP_PASSWORD_HASH in .env",
                    retryable=False,
                ),
            )
        if not bcrypt.checkpw(
            body.password.encode(), settings.APP_PASSWORD_HASH.encode()
        ):
            raise HTTPException(
                status_code=401,
                detail=error_response(
                    "invalid_password", "Incorrect password.", retryable=False
                ),
            )
        password_ok = True

    max_age = settings.SESSION_MAX_AGE_DAYS * 86400
    response.set_cookie(
        "session",
        sign_session(workspace_id_for_session),
        max_age=max_age,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        path="/",
    )
    return {"status": "ok", "workspace_id": workspace_id_for_session}


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("session", path="/")
    return {"status": "ok"}


@router.get("/auth/session")
async def session_status(workspace_id: str = Depends(require_auth)):
    return {"authenticated": True, "workspace_id": workspace_id}


@router.post("/auth/setup")
async def setup(
    body: SetupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    existing = (await db.execute(select(Workspace).limit(1))).scalar_one_or_none()
    if existing:
        sec = await auth_repo.get_security(db, existing.id)
        if sec and sec.password_encrypted_dek:
            raise HTTPException(
                status_code=409,
                detail=error_response(
                    "already_setup", "Workspace already configured.", retryable=False
                ),
            )

    workspace = Workspace(
        name="My Tax Return",
        financial_year=body.financial_year,
        status="active",
    )
    db.add(workspace)
    await db.flush()

    dek = generate_dek()
    password_hash = bcrypt.hashpw(
        body.password.encode(), bcrypt.gensalt(rounds=12)
    ).decode()
    password_encrypted_dek = encrypt_dek(dek, body.password)
    recovery_key = generate_recovery_key()
    normalized_rk = normalize_recovery_key(recovery_key)
    recovery_key_hash = bcrypt.hashpw(
        normalized_rk.encode(), bcrypt.gensalt(rounds=12)
    ).decode()
    recovery_encrypted_dek = encrypt_dek(dek, normalized_rk)

    await auth_repo.create_security(
        db,
        workspace_id=workspace.id,
        password_hash=password_hash,
        password_encrypted_dek=password_encrypted_dek,
        recovery_key_hash=recovery_key_hash,
        recovery_encrypted_dek=recovery_encrypted_dek,
    )

    max_age = settings.SESSION_MAX_AGE_DAYS * 86400
    response.set_cookie(
        "session",
        sign_session(workspace.id),
        max_age=max_age,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        path="/",
    )
    return {"status": "ok", "workspace_id": workspace.id, "recovery_key": recovery_key}


@router.post("/auth/unlock")
async def unlock(
    body: UnlockRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    ws = await auth_repo.get_security(db, body.workspace_id)
    if not ws or not ws.password_hash or not ws.password_encrypted_dek:
        raise HTTPException(
            status_code=404,
            detail=error_response(
                "workspace_not_found",
                "Workspace security record not found.",
                retryable=False,
            ),
        )
    if not bcrypt.checkpw(body.password.encode(), ws.password_hash.encode()):
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "invalid_password", "Incorrect password.", retryable=False
            ),
        )
    dek = decrypt_dek(ws.password_encrypted_dek, body.password)
    unlock_token = make_unlock_token(dek, settings.SECRET_KEY)
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.UNLOCK_SESSION_MINUTES
    )
    await auth_repo.update_security(
        db, ws, unlock_session_token=unlock_token, unlock_session_expires=expires
    )
    return {"status": "ok", "expires_at": expires.isoformat()}


@router.post("/auth/recover")
async def recover(body: RecoverRequest, db: AsyncSession = Depends(get_db)):
    ws = await auth_repo.get_security(db, body.workspace_id)
    if not ws or not ws.recovery_key_hash or not ws.recovery_encrypted_dek:
        raise HTTPException(
            status_code=404,
            detail=error_response(
                "workspace_not_found", "Workspace not found.", retryable=False
            ),
        )
    normalized = normalize_recovery_key(body.recovery_key)
    if not bcrypt.checkpw(normalized.encode(), ws.recovery_key_hash.encode()):
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "invalid_recovery_key",
                "Recovery key is incorrect.",
                retryable=False,
            ),
        )
    dek = decrypt_dek(ws.recovery_encrypted_dek, normalized)
    new_hash = bcrypt.hashpw(
        body.new_password.encode(), bcrypt.gensalt(rounds=12)
    ).decode()
    new_encrypted_dek = encrypt_dek(dek, body.new_password)
    await auth_repo.update_security(
        db,
        ws,
        password_hash=new_hash,
        password_encrypted_dek=new_encrypted_dek,
    )
    return {"status": "ok"}
```

- [ ] **Step 5: Run all tests**

```bash
make test
```

Expected: all 5 original tests pass + new auth tests pass. No regressions.

---

## Task 5: Draft endpoints

**Files:**
- Create: `backend/app/api/routes/drafts.py`
- Modify: `backend/app/api/__init__.py`

### Design notes

Both draft endpoints take `workspace_id` as a query parameter. This allows `require_unlock` (which also takes `workspace_id` from the query string) to validate the unlock session without needing to parse the request body. The route handler and the dependency both receive `workspace_id` independently from the query string — FastAPI deduplicates this cleanly.

- [ ] **Step 1: Append draft tests to `backend/tests/test_auth.py`**

```python
@pytest.mark.asyncio
async def test_draft_save_and_retrieve(auth_client, patch_password):
    workspace_id = auth_client.workspace_id

    await auth_client.post(
        "/api/v1/auth/unlock",
        json={"password": TEST_PASSWORD, "workspace_id": workspace_id},
    )

    content = {"name": "Allan", "income": 95000}

    save_resp = await auth_client.post(
        f"/api/v1/drafts/tax_profile?workspace_id={workspace_id}",
        json={"content": content},
    )
    assert save_resp.status_code == 200

    get_resp = await auth_client.get(
        f"/api/v1/drafts/tax_profile?workspace_id={workspace_id}"
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["content"] == content


@pytest.mark.asyncio
async def test_draft_requires_unlock(auth_client):
    workspace_id = auth_client.workspace_id
    resp = await auth_client.get(
        f"/api/v1/drafts/tax_profile?workspace_id={workspace_id}"
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_draft_invalid_form_type_returns_422(auth_client, patch_password):
    workspace_id = auth_client.workspace_id
    await auth_client.post(
        "/api/v1/auth/unlock",
        json={"password": TEST_PASSWORD, "workspace_id": workspace_id},
    )
    resp = await auth_client.post(
        f"/api/v1/drafts/invalid_type?workspace_id={workspace_id}",
        json={"content": {}},
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run draft tests to confirm they fail (router not registered)**

```bash
make test-file FILE=tests/test_auth.py
```

Expected: draft tests fail with 404.

- [ ] **Step 3: Create `backend/app/api/routes/drafts.py`**

```python
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_unlock
from app.db.base import get_db
from app.errors import error_response
from app.repositories import auth as auth_repo
from app.security import decrypt_from_draft, encrypt_for_draft

router = APIRouter()

_VALID_FORM_TYPES = {"tax_profile", "interview", "manual_entry"}


class SaveDraftRequest(BaseModel):
    content: dict[str, Any]


@router.post("/drafts/{form_type}")
async def save_draft(
    form_type: str,
    body: SaveDraftRequest,
    workspace_id: str = Query(...),
    dek: bytes = Depends(require_unlock),
    db: AsyncSession = Depends(get_db),
):
    if form_type not in _VALID_FORM_TYPES:
        raise HTTPException(
            status_code=422,
            detail=error_response(
                "invalid_form_type",
                f"form_type must be one of: {', '.join(sorted(_VALID_FORM_TYPES))}",
                retryable=False,
            ),
        )
    encrypted = encrypt_for_draft(body.content, dek)
    await auth_repo.upsert_draft(db, workspace_id, form_type, encrypted)
    return {"status": "ok"}


@router.get("/drafts/{form_type}")
async def get_draft(
    form_type: str,
    workspace_id: str = Query(...),
    dek: bytes = Depends(require_unlock),
    db: AsyncSession = Depends(get_db),
):
    draft = await auth_repo.get_draft(db, workspace_id, form_type)
    if not draft or not draft.encrypted_content:
        return {"status": "ok", "content": None}
    content = decrypt_from_draft(draft.encrypted_content, dek)
    return {"status": "ok", "content": content}
```

- [ ] **Step 4: Register drafts router in `backend/app/api/__init__.py`**

Replace the entire file:

```python
from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.drafts import router as drafts_router
from app.api.routes.events import router as events_router
from app.api.routes.export import router as export_router
from app.api.routes.health import router as health_router
from app.api.routes.interview import router as interview_router
from app.api.routes.readiness import router as readiness_router
from app.api.routes.review import router as review_router
from app.api.routes.workspaces import router as workspaces_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(workspaces_router)
api_router.include_router(documents_router)
api_router.include_router(drafts_router)
api_router.include_router(interview_router)
api_router.include_router(events_router)
api_router.include_router(readiness_router)
api_router.include_router(review_router)
api_router.include_router(export_router)
```

- [ ] **Step 5: Run full test suite**

```bash
make test
```

Expected: all tests pass — 5 original + crypto unit tests + auth integration tests + draft tests.

---

## Task 6: Frontend login page

**Files:**
- Modify: `frontend/app/(auth)/login/page.tsx` (replace stub)

Spec: minimal and functional — no design tokens yet. Password input + submit, calls `POST /api/v1/auth/login`, redirects to `/readiness` on success, shows error on failure.

- [ ] **Step 1: Replace `frontend/app/(auth)/login/page.tsx`**

```tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const router = useRouter()
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
        credentials: 'include',
      })
      if (res.ok) {
        router.push('/readiness')
      } else {
        const body = await res.json().catch(() => ({}))
        setError(body?.detail?.message ?? 'Login failed. Check your password.')
      }
    } catch {
      setError('Cannot reach server. Is it running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ padding: '2rem', maxWidth: '400px', margin: '0 auto' }}>
      <h1>Tax Return AI</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="password">Password</label>
          <br />
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoFocus
            style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem' }}
          />
        </div>
        {error && (
          <p role="alert" style={{ color: 'red', marginTop: '0.5rem' }}>
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading}
          style={{ marginTop: '1rem', padding: '0.5rem 1.5rem' }}
        >
          {loading ? 'Logging in…' : 'Log in'}
        </button>
      </form>
    </main>
  )
}
```

- [ ] **Step 2: Verify frontend build**

```bash
make dev-build
```

Expected: TypeScript compiles cleanly, no errors.

---

## Spec Coverage Check

| Spec requirement | Task | Covered |
|---|---|---|
| `POST /auth/login` — bcrypt verify, httpOnly cookie | Task 4 | ✅ |
| `POST /auth/logout` — clear cookie | Task 4 | ✅ |
| `GET /auth/session` — session status | Task 4 | ✅ |
| `app/repositories/auth.py` — WorkspaceSecurity DB access | Task 2 | ✅ |
| `app/api/dependencies.py` — `require_auth`, `require_unlock` | Task 3 | ✅ |
| First-run: `APP_PASSWORD_HASH` empty → 503 with message | Task 4 | ✅ |
| Cookie: `httpOnly`, `secure`, `samesite=strict`, correct `max_age` | Task 4 | ✅ |
| `POST /auth/setup` — workspace + DEK + recovery key | Task 4 | ✅ |
| `POST /auth/unlock` — decrypt DEK, store unlock token | Task 4 | ✅ |
| `POST /auth/recover` — verify recovery key, re-encrypt DEK | Task 4 | ✅ |
| DEK never in plaintext, never logged, never in response | Task 1 + 4 | ✅ |
| `POST /drafts/{form_type}` + `GET /drafts/{form_type}` | Task 5 | ✅ |
| Valid form types: `tax_profile`, `interview`, `manual_entry` | Task 5 | ✅ |
| Test: login correct → cookie set | Task 4 | ✅ |
| Test: login wrong → 401, no cookie | Task 4 | ✅ |
| Test: logout → cookie cleared | Task 4 | ✅ |
| Test: session authenticated → 200 | Task 4 | ✅ |
| Test: session unauthenticated → 401 | Task 4 | ✅ |
| Test: setup → WorkspaceSecurity created, DEK fields populated | Task 4 | ✅ |
| Test: recover → DEK re-encrypted, login works with new password | Task 4 | ✅ |
| Test: unlock expired → sensitive endpoint returns 401 | Task 4 | ✅ |
| Frontend login page — minimal, password input, redirect on success | Task 6 | ✅ |
| No tax logic, no document handling, no workspace creation UI | all | ✅ |
