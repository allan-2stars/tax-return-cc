from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.drafts import router as drafts_router
from app.api.routes.estimator import router as estimator_router
from app.api.routes.events import router as events_router
from app.api.routes.export import router as export_router
from app.api.routes.health import router as health_router
from app.api.routes.interview import router as interview_router
from app.api.routes.readiness import router as readiness_router
from app.api.routes.review import router as review_router
from app.api.routes.workspaces import router as workspaces_router
from app.api.routes.yoy import router as yoy_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(workspaces_router)
api_router.include_router(documents_router)
api_router.include_router(drafts_router)
api_router.include_router(interview_router)
api_router.include_router(events_router)
api_router.include_router(readiness_router)
api_router.include_router(review_router)
api_router.include_router(export_router)
api_router.include_router(yoy_router)
api_router.include_router(estimator_router)
