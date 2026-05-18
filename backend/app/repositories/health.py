from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def ping(db: AsyncSession) -> bool:
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
