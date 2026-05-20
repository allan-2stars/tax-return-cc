from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import YoySuggestion


async def create_suggestions(
    db: AsyncSession, suggestions: list[YoySuggestion]
) -> list[YoySuggestion]:
    for s in suggestions:
        db.add(s)
    await db.commit()
    for s in suggestions:
        await db.refresh(s)
    return suggestions


async def get_pending(db: AsyncSession, workspace_id: str) -> list[YoySuggestion]:
    result = await db.execute(
        select(YoySuggestion).where(
            YoySuggestion.workspace_id == workspace_id,
            YoySuggestion.status == "pending",
        )
    )
    return list(result.scalars().all())


async def update_action(
    db: AsyncSession, suggestion_id: str, action: str
) -> YoySuggestion:
    result = await db.execute(
        select(YoySuggestion).where(YoySuggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one()
    suggestion.status = action
    suggestion.actioned_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(suggestion)
    return suggestion
