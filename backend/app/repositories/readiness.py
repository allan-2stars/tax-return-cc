from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ReadinessScore, Workspace


async def get_score(db: AsyncSession, workspace_id: str) -> ReadinessScore | None:
    result = await db.execute(
        select(ReadinessScore).where(ReadinessScore.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none()


async def save_score(
    db: AsyncSession,
    workspace_id: str,
    financial_year: str,
    percentage: int,
    breakdown: list,
    missing_items: list,
    review_items: list,
    agent_items: list,
) -> ReadinessScore:
    existing = await get_score(db, workspace_id)
    if existing:
        existing.percentage = float(percentage)
        existing.breakdown = breakdown
        existing.missing_items = missing_items
        existing.review_items = review_items
        existing.agent_items = agent_items
        existing.is_stale = False
        existing.calculated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        return existing

    record = ReadinessScore(
        workspace_id=workspace_id,
        financial_year=financial_year,
        percentage=float(percentage),
        breakdown=breakdown,
        missing_items=missing_items,
        review_items=review_items,
        agent_items=agent_items,
        is_stale=False,
        calculated_at=datetime.now(timezone.utc),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def mark_stale(db: AsyncSession, workspace_id: str) -> None:
    record = await get_score(db, workspace_id)
    if record:
        record.is_stale = True
        await db.commit()
