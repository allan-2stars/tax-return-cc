from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.base import get_db
from app.errors import error_response
from app.repositories import auth as auth_repo
from app.security import extract_dek_from_token


def _session_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt="session")


def _unlock_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt="unlock")


def sign_session(workspace_id: str) -> str:
    return _session_serializer().dumps({"w": workspace_id})


def sign_unlock_session(workspace_id: str) -> str:
    return _unlock_serializer().dumps({"w": workspace_id})


def decode_session_cookie(token: str, max_age: int) -> str:
    """Decode a signed session cookie, return workspace_id, raise 401 on any failure.

    The payload is signed (HMAC) but not encrypted — workspace_id is readable by
    the cookie holder. This is accepted for a single-user personal app where
    workspace_id is not a secret (it also appears in API URLs). The signature
    prevents forgery.
    """
    try:
        data = _session_serializer().loads(token, max_age=max_age)
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


def _decode_unlock_cookie(token: str, max_age: int) -> str:
    """Decode a signed unlock_session cookie, return workspace_id, raise 401 on any failure."""
    try:
        data = _unlock_serializer().loads(token, max_age=max_age)
        return data["w"]
    except SignatureExpired:
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "unlock_expired",
                "Unlock session expired. Please unlock again.",
                retryable=False,
            ),
        )
    except (BadSignature, KeyError):
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "unlock_invalid", "Invalid unlock session.", retryable=False
            ),
        )


async def require_session(session: str | None = Cookie(default=None)) -> str:
    """Returns workspace_id from session cookie. Does NOT check setup_confirmed."""
    if not session:
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "not_authenticated", "Authentication required.", retryable=False
            ),
        )
    return decode_session_cookie(session, max_age=settings.SESSION_MAX_AGE_DAYS * 86400)


async def require_auth(
    workspace_id: str = Depends(require_session),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Returns workspace_id. Raises 403 if setup has not been confirmed yet."""
    if workspace_id:  # empty string = pre-setup bootstrap login (no workspace yet)
        ws = await auth_repo.get_security(db, workspace_id)
        if ws and not ws.setup_confirmed:
            raise HTTPException(
                status_code=403,
                detail=error_response(
                    "setup_not_confirmed",
                    "Please save your recovery key and confirm before continuing.",
                    action="confirm_setup",
                    retryable=False,
                ),
            )
    return workspace_id


async def require_unlock(
    unlock_session: str | None = Cookie(default=None),
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> bytes:
    """
    Returns raw DEK bytes. Raises 401 if:
    - unlock_session cookie is absent, expired, or tampered
    - Server-side unlock_session_expires has passed
    - unlock_session_token cannot be decrypted
    """
    if not unlock_session:
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "not_unlocked",
                "Workspace is locked. Please unlock first.",
                retryable=False,
            ),
        )

    # Verify cookie signature and embedded workspace_id
    max_age = settings.UNLOCK_SESSION_MINUTES * 60
    cookie_workspace_id = _decode_unlock_cookie(unlock_session, max_age=max_age)

    # Ensure the unlock cookie belongs to the authenticated workspace
    if cookie_workspace_id != workspace_id:
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "unlock_mismatch", "Unlock session does not match authenticated workspace.", retryable=False
            ),
        )

    # Check server-side expiry and retrieve the encrypted DEK
    ws = await auth_repo.get_security(db, workspace_id)
    if not ws or not ws.unlock_session_token or not ws.unlock_session_expires:
        raise HTTPException(
            status_code=401,
            detail=error_response(
                "not_unlocked", "Workspace is locked.", retryable=False
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
