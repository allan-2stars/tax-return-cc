from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TaxEvent


async def get_by_id(db: AsyncSession, event_id: str) -> TaxEvent | None:
    result = await db.execute(select(TaxEvent).where(TaxEvent.id == event_id))
    return result.scalar_one_or_none()


async def get_by_workspace(db: AsyncSession, workspace_id: str) -> list[TaxEvent]:
    result = await db.execute(
        select(TaxEvent).where(TaxEvent.workspace_id == workspace_id)
    )
    return list(result.scalars().all())


async def create_event(
    db: AsyncSession,
    workspace_id: str,
    financial_year: str,
    event_type: str,
    category: str,
    description: str | None,
    amount: float | None,
    date: str | None,
    source: str,
    note: str | None = None,
    group_id: str | None = None,
    group_display: str | None = None,
    is_recurring: bool = False,
    recurrence_index: int | None = None,
) -> TaxEvent:
    event = TaxEvent(
        workspace_id=workspace_id,
        financial_year=financial_year,
        event_type=event_type,
        category=category,
        description=description,
        amount=amount,
        date=date,
        source=source,
        user_note=note,
        group_id=group_id,
        group_display=group_display,
        is_recurring=is_recurring,
        recurrence_index=recurrence_index,
        status="needs_user_review",
        risk_level="low",
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def attach_document(
    db: AsyncSession, event_id: str, document_id: str
) -> TaxEvent:
    result = await db.execute(select(TaxEvent).where(TaxEvent.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise ValueError(f"TaxEvent {event_id!r} not found")
    event.document_id = document_id
    await db.commit()
    await db.refresh(event)
    return event
