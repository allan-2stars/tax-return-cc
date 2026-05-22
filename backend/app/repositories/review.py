from datetime import timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ReviewItem, TaxEvent


def _normalize_datetimes(item: ReviewItem) -> ReviewItem:
    """SQLite strips timezone info; restore UTC so callers get timezone-aware datetimes."""
    for attr in ("created_at", "reviewed_at", "skipped_until"):
        val = getattr(item, attr, None)
        if val is not None and val.tzinfo is None:
            setattr(item, attr, val.replace(tzinfo=timezone.utc))
    return item


async def create(db: AsyncSession, event: TaxEvent) -> ReviewItem:
    item = ReviewItem(
        workspace_id=event.workspace_id,
        tax_event_id=event.id,
        title=event.description,
        category=event.category,
        amount=event.amount,
        date=event.date,
        skill_id=event.skill_id,
        risk_level=event.risk_level,
        ai_reasoning=event.ai_reasoning,
        confidence=event.confidence,
        status="needs_user_review",
        questions_complete=False,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _normalize_datetimes(item)


async def get_by_id(db: AsyncSession, item_id: str) -> ReviewItem | None:
    result = await db.execute(
        select(ReviewItem)
        .where(ReviewItem.id == item_id)
        .options(selectinload(ReviewItem.tax_event))
    )
    return result.scalar_one_or_none()


async def get_by_event_id(db: AsyncSession, event_id: str) -> ReviewItem | None:
    result = await db.execute(
        select(ReviewItem).where(ReviewItem.tax_event_id == event_id)
    )
    return result.scalar_one_or_none()


async def get_queue(db: AsyncSession, workspace_id: str) -> list[ReviewItem]:
    result = await db.execute(
        select(ReviewItem)
        .where(ReviewItem.workspace_id == workspace_id)
        .options(selectinload(ReviewItem.tax_event))
    )
    return list(result.scalars().all())


async def update(db: AsyncSession, item: ReviewItem) -> ReviewItem:
    await db.commit()
    # Re-query with selectinload to restore relationship after commit expires it
    result = await db.execute(
        select(ReviewItem)
        .where(ReviewItem.id == item.id)
        .options(selectinload(ReviewItem.tax_event))
    )
    refreshed = result.scalar_one_or_none()
    if refreshed is None:
        raise ValueError(f"ReviewItem {item.id} not found after update")
    return _normalize_datetimes(refreshed)
