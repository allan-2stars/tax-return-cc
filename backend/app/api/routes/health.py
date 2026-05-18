from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.base import get_db
from app.repositories import health as health_repo

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "ok" if await health_repo.ping(db) else "error"
    try:
        storage_status = "ok" if Path(settings.STORAGE_PATH).exists() else "error"
    except OSError:
        storage_status = "error"

    return {"status": "ok", "db": db_status, "storage": storage_status}
