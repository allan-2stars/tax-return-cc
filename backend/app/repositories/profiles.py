from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TaxProfile


async def get_by_workspace(db: AsyncSession, workspace_id: str) -> TaxProfile | None:
    result = await db.execute(
        select(TaxProfile).where(TaxProfile.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none()


async def get_or_create(
    db: AsyncSession, workspace_id: str, financial_year: str
) -> TaxProfile:
    profile = await get_by_workspace(db, workspace_id)
    if profile is None:
        profile = TaxProfile(
            workspace_id=workspace_id,
            financial_year=financial_year,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def update_fields(
    db: AsyncSession, profile: TaxProfile, fields: dict
) -> TaxProfile:
    for key, value in fields.items():
        setattr(profile, key, value)
    await db.commit()
    await db.refresh(profile)
    return profile
