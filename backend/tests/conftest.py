import os

# Must be set before any app module is imported.
# Prevents lifespan from running alembic upgrade in tests.
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, get_db
from app.main import app

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        _TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_engine):
    session_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            ac.app = app
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def missing_storage_settings(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "STORAGE_PATH", "/nonexistent/path/that/does/not/exist")
    yield


import bcrypt

TEST_PASSWORD = "test-password-m2"


@pytest.fixture
def patch_password(monkeypatch):
    """Patch APP_PASSWORD_HASH and SECRET_KEY for deterministic tests."""
    from app.config import settings
    hashed = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    monkeypatch.setattr(settings, "APP_PASSWORD_HASH", hashed)
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-key-for-unit-tests")
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "SESSION_MAX_AGE_DAYS", 1)


@pytest_asyncio.fixture
async def auth_client(client, patch_password):
    """
    HTTP client in the post-setup, confirmed, logged-in state.
    Carries a valid session cookie. Does NOT carry an unlock_session cookie.
    """
    from app.security import normalize_recovery_key

    setup_resp = await client.post(
        "/api/v1/auth/setup",
        json={"password": TEST_PASSWORD, "financial_year": "2024-25"},
    )
    assert setup_resp.status_code == 200, setup_resp.text
    client.workspace_id = setup_resp.json()["data"]["workspace_id"]
    client.recovery_key = setup_resp.json()["data"]["recovery_key"]

    # Confirm setup (required before require_auth allows through)
    last_8 = normalize_recovery_key(client.recovery_key)[-8:]
    confirm_resp = await client.post(
        "/api/v1/auth/setup/confirm",
        json={"confirmation": f"{last_8[:4]}-{last_8[4:]}"},
    )
    assert confirm_resp.status_code == 200, confirm_resp.text

    login_resp = await client.post(
        "/api/v1/auth/login", json={"password": TEST_PASSWORD}
    )
    assert login_resp.status_code == 200, login_resp.text
    yield client


@pytest_asyncio.fixture
async def workspace_id(auth_client) -> str:
    """Return the workspace_id for the current auth_client session."""
    return auth_client.workspace_id
