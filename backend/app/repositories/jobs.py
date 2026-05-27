from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BackgroundJob


async def create_job(
    db: AsyncSession,
    workspace_id: str,
    job_type: str,
    payload: dict | None = None,
) -> BackgroundJob:
    job = BackgroundJob(
        workspace_id=workspace_id,
        job_type=job_type,
        status="pending",
        payload=payload or {},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def update_status(
    db: AsyncSession,
    job_id: str,
    status: str,
    result: dict | None = None,
    error: str | None = None,
) -> BackgroundJob:
    res = await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))
    job = res.scalar_one()
    job.status = status
    if result is not None:
        job.result = result
    if error is not None:
        job.error = error
    await db.commit()
    await db.refresh(job)
    return job


async def list_export_jobs_before(db: AsyncSession, cutoff) -> list[BackgroundJob]:
    result = await db.execute(
        select(BackgroundJob).where(
            BackgroundJob.job_type == "export_generate",
            BackgroundJob.status.in_(["pending", "running"]),
            BackgroundJob.created_at <= cutoff,
        )
    )
    return list(result.scalars().all())
