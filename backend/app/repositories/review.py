from datetime import timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ReviewDecisionHistory, ReviewItem, TaxEvent


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
        status=event.status,
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


async def get_history_for_item(
    db: AsyncSession,
    review_item_id: str,
) -> list[ReviewDecisionHistory]:
    result = await db.execute(
        select(ReviewDecisionHistory)
        .where(ReviewDecisionHistory.review_item_id == review_item_id)
        .order_by(ReviewDecisionHistory.created_at.desc())
    )
    return list(result.scalars().all())


async def get_history_by_item_ids(
    db: AsyncSession,
    review_item_ids: list[str],
) -> dict[str, list[ReviewDecisionHistory]]:
    if not review_item_ids:
        return {}
    result = await db.execute(
        select(ReviewDecisionHistory)
        .where(ReviewDecisionHistory.review_item_id.in_(review_item_ids))
        .order_by(ReviewDecisionHistory.created_at.desc())
    )
    grouped: dict[str, list[ReviewDecisionHistory]] = {item_id: [] for item_id in review_item_ids}
    for history in result.scalars().all():
        grouped.setdefault(history.review_item_id, []).append(history)
    return grouped


async def get_latest_history_for_item(
    db: AsyncSession,
    review_item_id: str,
) -> ReviewDecisionHistory | None:
    result = await db.execute(
        select(ReviewDecisionHistory)
        .where(ReviewDecisionHistory.review_item_id == review_item_id)
        .order_by(ReviewDecisionHistory.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_histories_for_bulk_action(
    db: AsyncSession,
    workspace_id: str,
    bulk_action_id: str,
) -> list[ReviewDecisionHistory]:
    result = await db.execute(
        select(ReviewDecisionHistory)
        .where(
            ReviewDecisionHistory.workspace_id == workspace_id,
            ReviewDecisionHistory.bulk_action_id == bulk_action_id,
            ReviewDecisionHistory.action != "undo",
        )
        .order_by(ReviewDecisionHistory.created_at.asc())
    )
    return list(result.scalars().all())
