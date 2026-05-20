from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TaxEvent


async def get_by_workspace(db: AsyncSession, workspace_id: str) -> list[TaxEvent]:
    result = await db.execute(
        select(TaxEvent).where(TaxEvent.workspace_id == workspace_id)
    )
    return list(result.scalars().all())
