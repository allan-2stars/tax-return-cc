import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings

logger = logging.getLogger(__name__)


async def _run_alembic_upgrade() -> None:
    # The local alembic/ directory shadows the installed package, so we use
    # the subprocess approach. cwd="/app" is explicit to avoid working-dir assumptions.
    proc = await asyncio.create_subprocess_exec(
        "alembic", "upgrade", "head",
        cwd="/app",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Alembic migration failed: {stderr.decode()}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT != "test":
        await _run_alembic_upgrade()
        from app.db.base import AsyncSessionLocal
        from app.engines.export import ExportEngine
        async with AsyncSessionLocal() as db:
            expired = await ExportEngine().cleanup_expired(db)
            if expired:
                logger.info("Cleaned up %d expired export(s) on startup", expired)
    yield


app = FastAPI(title="Tax Return AI", lifespan=lifespan)

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
