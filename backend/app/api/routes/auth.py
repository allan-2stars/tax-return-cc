from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth, sign_session, sign_unlock_session
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
    password: str = Field(..., min_length=8)
    financial_year: str = "2024-25"


class UnlockRequest(BaseModel):
    password: str = Field(..., min_length=8)


class RecoverRequest(BaseModel):
    recovery_key: str
    new_password: str = Field(..., min_length=8)
    workspace_id: str


@router.post("/auth/login")
async def login(
    body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    workspace = await auth_repo.get_singleton_workspace(db)

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
    response.delete_cookie("unlock_session", path="/")
    return {"status": "ok"}


@router.get("/auth/session")
async def session_status(workspace_id: str = Depends(require_auth)):
    return {"authenticated": True, "workspace_id": workspace_id}


@router.post("/auth/setup")
async def setup(
    body: SetupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    existing = await auth_repo.get_singleton_workspace(db)
    if existing is not None:
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
    response: Response,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(require_auth),
):
    ws = await auth_repo.get_security(db, workspace_id)
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

    response.set_cookie(
        "unlock_session",
        sign_unlock_session(workspace_id),
        max_age=settings.UNLOCK_SESSION_MINUTES * 60,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        path="/",
    )
    return {"status": "ok"}


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
