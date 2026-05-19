from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EncryptedDraft, Workspace, WorkspaceSecurity


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
    recovery_confirm_hash: str,
) -> WorkspaceSecurity:
    ws = WorkspaceSecurity(
        workspace_id=workspace_id,
        password_hash=password_hash,
        password_encrypted_dek=password_encrypted_dek,
        recovery_key_hash=recovery_key_hash,
        recovery_encrypted_dek=recovery_encrypted_dek,
        recovery_confirm_hash=recovery_confirm_hash,
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


async def get_singleton_workspace(db: AsyncSession) -> Workspace | None:
    result = await db.execute(select(Workspace).limit(1))
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
