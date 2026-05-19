from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SkillVersionLock


async def delete_skill_lock(
    db: AsyncSession, workspace_id: str, skill_id: str
) -> None:
    result = await db.execute(
        select(SkillVersionLock).where(
            SkillVersionLock.workspace_id == workspace_id,
            SkillVersionLock.skill_id == skill_id,
        )
    )
    lock = result.scalar_one_or_none()
    if lock:
        await db.delete(lock)
        await db.commit()


async def lock_activated_skills(
    db: AsyncSession, workspace_id: str, skills: list
) -> None:
    """Create SkillVersionLock records for newly activated skills (idempotent)."""
    for skill in skills:
        result = await db.execute(
            select(SkillVersionLock).where(
                SkillVersionLock.workspace_id == workspace_id,
                SkillVersionLock.skill_id == skill.skill_id,
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(SkillVersionLock(
                workspace_id=workspace_id,
                skill_id=skill.skill_id,
                skill_version=skill.version,
            ))
    await db.commit()


async def get_locked_skills(db: AsyncSession, workspace_id: str) -> list[dict]:
    result = await db.execute(
        select(SkillVersionLock).where(SkillVersionLock.workspace_id == workspace_id)
    )
    return [
        {"skill_id": lock.skill_id, "version": lock.skill_version}
        for lock in result.scalars()
    ]
