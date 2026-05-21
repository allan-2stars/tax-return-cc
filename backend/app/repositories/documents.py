from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document


async def find_by_hash(db: AsyncSession, workspace_id: str, sha256: str) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.workspace_id == workspace_id,
            Document.sha256_hash == sha256,
            Document.archived == False,
        )
    )
    return result.scalar_one_or_none()


async def create(db: AsyncSession, **fields) -> Document:
    doc = Document(**fields)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def update_status(db: AsyncSession, document_id: str, status: str) -> None:
    doc = await get_by_id(db, document_id)
    if doc:
        doc.status = status
        if status == "ready":
            doc.processed_at = datetime.now(timezone.utc)
        await db.commit()


async def update_extraction(
    db: AsyncSession,
    doc: Document,
    extracted_text: str | None,
    extracted_fields: dict | None,
    method: str,
    confidence: float,
) -> None:
    doc.extracted_text = extracted_text
    doc.extracted_fields = extracted_fields
    doc.extraction_method = method
    doc.extraction_confidence = confidence
    await db.commit()


async def get_by_id(db: AsyncSession, document_id: str) -> Document | None:
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    return result.scalar_one_or_none()


async def get_ready_docs(db: AsyncSession, workspace_id: str) -> list[Document]:
    result = await db.execute(
        select(Document).where(
            Document.workspace_id == workspace_id,
            Document.status == "ready",
            Document.archived == False,
        )
    )
    return list(result.scalars().all())


async def list_by_workspace(db: AsyncSession, workspace_id: str) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == workspace_id, Document.archived == False)
        .order_by(Document.uploaded_at.desc())
    )
    return list(result.scalars().all())


async def archive_by_id(db: AsyncSession, document_id: str) -> None:
    doc = await get_by_id(db, document_id)
    if not doc:
        raise ValueError(f"Document {document_id} not found")
    doc.archived = True
    doc.archived_reason = "user_removed"
    await db.commit()
