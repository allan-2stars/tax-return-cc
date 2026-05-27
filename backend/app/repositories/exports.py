from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExportRecord


async def create(
    db: AsyncSession,
    workspace_id: str,
    financial_year: str,
    readiness_pct: float = 0.0,
    confirmed_count: int = 0,
    review_count: int = 0,
    agent_count: int = 0,
    missing_count: int = 0,
    skills_active: list | None = None,
    expires_at: datetime | None = None,
) -> ExportRecord:
    record = ExportRecord(
        workspace_id=workspace_id,
        financial_year=financial_year,
        readiness_pct=readiness_pct,
        confirmed_count=confirmed_count,
        review_count=review_count,
        agent_count=agent_count,
        missing_count=missing_count,
        skills_active=skills_active or [],
        expires_at=expires_at,
        status="generating",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_by_id(db: AsyncSession, export_id: str) -> ExportRecord | None:
    result = await db.execute(
        select(ExportRecord).where(ExportRecord.id == export_id)
    )
    return result.scalar_one_or_none()


async def get_history(db: AsyncSession, workspace_id: str) -> list[ExportRecord]:
    result = await db.execute(
        select(ExportRecord)
        .where(ExportRecord.workspace_id == workspace_id)
        .order_by(ExportRecord.created_at.desc())
    )
    return list(result.scalars().all())


async def update_status(
    db: AsyncSession,
    export_id: str,
    status: str,
    storage_key: str | None = None,
    file_size_bytes: int | None = None,
) -> ExportRecord:
    result = await db.execute(
        select(ExportRecord).where(ExportRecord.id == export_id)
    )
    record = result.scalar_one()
    record.status = status
    if storage_key is not None:
        record.storage_key = storage_key
    if file_size_bytes is not None:
        record.file_size_bytes = file_size_bytes
    await db.commit()
    await db.refresh(record)
    return record


async def get_expired(db: AsyncSession, retention_hours: int) -> list[ExportRecord]:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await db.execute(
        select(ExportRecord).where(
            ExportRecord.status == "ready",
            ExportRecord.expires_at <= cutoff,
        )
    )
    return list(result.scalars().all())


async def get_generating_before(db: AsyncSession, cutoff: datetime) -> list[ExportRecord]:
    result = await db.execute(
        select(ExportRecord).where(
            ExportRecord.status == "generating",
            ExportRecord.created_at <= cutoff,
        )
    )
    return list(result.scalars().all())
