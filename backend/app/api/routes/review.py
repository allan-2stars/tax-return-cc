from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.db.models import ReviewItem
from app.engines.review import ReviewEngine, UserAction
from app.errors import error_response
from app.repositories import interview as interview_repo
from app.repositories import profiles as profile_repo

router = APIRouter()

_engine = ReviewEngine()


# ── Request bodies ────────────────────────────────────────────────────────────

class ActionRequest(BaseModel):
    action: str
    amount: float | None = None
    category: str | None = None
    note: str | None = None


class InlineAnswerRequest(BaseModel):
    question_id: str
    answer: str
    event_id: str


class BulkActionRequest(BaseModel):
    item_ids: list[str]
    action: str


class AskRequest(BaseModel):
    question: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _item_dict(item: ReviewItem) -> dict:
    return {
        "id": item.id,
        "workspace_id": item.workspace_id,
        "tax_event_id": item.tax_event_id,
        "title": item.title,
        "category": item.category,
        "amount": item.amount,
        "date": item.date,
        "skill_id": item.skill_id,
        "risk_level": item.risk_level,
        "ai_reasoning": item.ai_reasoning,
        "confidence": item.confidence,
        "inline_questions": item.inline_questions or [],
        "questions_complete": item.questions_complete,
        "status": item.status,
        "user_action": item.user_action,
        "user_note": item.user_note,
        "amended_amount": item.amended_amount,
        "amended_category": item.amended_category,
        "skipped_until": item.skipped_until.isoformat() if item.skipped_until else None,
        "created_at": item.created_at.isoformat(),
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
        "review_duration_seconds": item.review_duration_seconds,
    }


# ── GET /review/queue ─────────────────────────────────────────────────────────

@router.get("/review/queue")
async def get_review_queue(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    queue = await _engine.get_queue(workspace_id, db)
    return {
        "data": {
            "agent_required": {
                "items": [_item_dict(i) for i in queue.agent_required],
                "count": len(queue.agent_required),
            },
            "high_risk": {
                "items": [_item_dict(i) for i in queue.high_risk],
                "count": len(queue.high_risk),
            },
            "needs_review": {
                "items": [_item_dict(i) for i in queue.needs_review],
                "count": len(queue.needs_review),
            },
            "confirmed": {
                "items": [_item_dict(i) for i in queue.confirmed],
                "count": len(queue.confirmed),
            },
            "total": queue.total,
            "pending": queue.pending,
        }
    }


# ── GET /review/{item_id} ─────────────────────────────────────────────────────

@router.get("/review/{item_id}")
async def get_review_item(
    item_id: str,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    item = await _engine.get_item(item_id, db)
    if item is None or item.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail=error_response("item_not_found", "Review item not found.", retryable=False),
        )
    return {"data": _item_dict(item)}


# ── POST /review/{item_id}/action ─────────────────────────────────────────────

@router.post("/review/{item_id}/action")
async def take_action(
    item_id: str,
    body: ActionRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    try:
        action = UserAction(body.action)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=error_response(
                "invalid_action",
                f"Unknown action {body.action!r}. Must be one of: confirmed, amended, flagged, skipped.",
                retryable=False,
            ),
        )

    payload = {
        "amount": body.amount,
        "category": body.category,
        "note": body.note,
    }

    try:
        item = await _engine.process_action(item_id, action, payload, db)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=error_response("item_not_found", str(e), retryable=False),
        )

    return {"data": _item_dict(item)}


# ── POST /review/{item_id}/inline-answer ──────────────────────────────────────

@router.post("/review/{item_id}/inline-answer")
async def submit_inline_answer(
    item_id: str,
    body: InlineAnswerRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    session_before = await interview_repo.get_active_by_workspace(db, workspace_id)
    skills_before = len(session_before.activated_skills or []) if session_before else 0

    try:
        item = await _engine.submit_inline_answer(
            item_id=item_id,
            question_id=body.question_id,
            answer=body.answer,
            event_id=body.event_id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=error_response("item_not_found", str(e), retryable=False),
        )

    session_after = await interview_repo.get_active_by_workspace(db, workspace_id)
    skills_after = len(session_after.activated_skills or []) if session_after else 0

    return {
        "data": {
            **_item_dict(item),
            "new_skill_pending": skills_after > skills_before,
        }
    }


# ── POST /review/bulk-action ──────────────────────────────────────────────────

@router.post("/review/bulk-action")
async def bulk_action(
    body: BulkActionRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    try:
        action = UserAction(body.action)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=error_response(
                "invalid_action",
                f"Unknown action {body.action!r}.",
                retryable=False,
            ),
        )

    try:
        results = await _engine.bulk_action(body.item_ids, action, db)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=error_response("bulk_action_error", str(e), retryable=False),
        )

    return {"data": {"items": [_item_dict(i) for i in results], "count": len(results)}}


# ── POST /review/{item_id}/ask ────────────────────────────────────────────────

@router.post("/review/{item_id}/ask")
async def ask_claude(
    item_id: str,
    body: AskRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await profile_repo.get_by_workspace(db, workspace_id)

    try:
        answer = await _engine.ask_claude(item_id, body.question, profile, db)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=error_response("item_not_found", str(e), retryable=False),
        )

    return {"data": {"answer": answer}}
