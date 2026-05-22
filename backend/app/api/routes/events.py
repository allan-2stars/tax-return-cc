from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.engines.evidence import EvidenceEngine
from app.engines.review import ReviewEngine
from app.errors import AppError, error_response
from app.repositories import profiles as profile_repo
from app.storage import get_storage_backend

router = APIRouter()

_review_engine = ReviewEngine()


class _Period(BaseModel):
    months: int
    amount_per_month: float


class ManualEventRequest(BaseModel):
    event_type: str
    category: str
    description: str
    amount: float
    date: str
    frequency: str
    note: str | None = None
    periods: list[_Period] | None = None


def _event_dict(ev) -> dict:
    return {
        "id": ev.id,
        "title": ev.description,
        "category": ev.category,
        "amount": ev.amount,
    }


@router.post("/events/manual")
async def create_manual_event(
    body: ManualEventRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await profile_repo.get_by_workspace(db, workspace_id)
    fy = profile.financial_year if profile else "2024-25"

    try:
        events = await _review_engine.create_manual_event(
            workspace_id=workspace_id,
            financial_year=fy,
            event_type=body.event_type,
            category=body.category,
            description=body.description,
            amount=body.amount,
            date=body.date,
            frequency=body.frequency,
            note=body.note,
            periods=[p.model_dump() for p in body.periods] if body.periods else None,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=error_response("invalid_event", str(e), retryable=False),
        )

    return {"data": {"items": [_event_dict(e) for e in events], "count": len(events)}}


@router.post("/events/{event_id}/attach-receipt")
async def attach_receipt(
    event_id: str,
    file: UploadFile = File(...),
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    file_data = await file.read()
    filename = file.filename or "receipt"
    storage = get_storage_backend()
    engine = EvidenceEngine(db=db, storage=storage)

    try:
        doc = await engine.attach_receipt(
            event_id=event_id,
            workspace_id=workspace_id,
            file_data=file_data,
            filename=filename,
        )
    except (AppError, ValueError) as e:
        code = getattr(e, "error_code", "attach_failed")
        msg = getattr(e, "message", str(e))
        raise HTTPException(
            status_code=422,
            detail=error_response(code, msg, retryable=False),
        )

    return {"data": {"document_id": doc.id}}
