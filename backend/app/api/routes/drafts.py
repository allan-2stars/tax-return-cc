from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth, require_unlock
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
    workspace_id: str = Depends(require_auth),
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
    workspace_id: str = Depends(require_auth),
    dek: bytes = Depends(require_unlock),
    db: AsyncSession = Depends(get_db),
):
    draft = await auth_repo.get_draft(db, workspace_id, form_type)
    if not draft or not draft.encrypted_content:
        return {"status": "ok", "content": None}
    content = decrypt_from_draft(draft.encrypted_content, dek)
    return {"status": "ok", "content": content}
