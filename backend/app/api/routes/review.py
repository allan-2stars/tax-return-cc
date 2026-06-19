from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.db.models import ReviewItem
from app.engines.review import ReviewEngine, UserAction
from app.errors import error_response
from app.repositories import documents as doc_repo
from app.repositories import interview as interview_repo
from app.repositories import profiles as profile_repo
from app.repositories import review as review_repo
from app.services.evidence_reconcile import EvidenceReconcileService
from app.services.explanations import build_tax_item_explanation

router = APIRouter()

_engine = ReviewEngine()
_reconcile_service = EvidenceReconcileService()


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

def _history_dict(history) -> dict:
    created_at = history.created_at
    return {
        "id": history.id,
        "workspace_id": history.workspace_id,
        "review_item_id": history.review_item_id,
        "tax_event_id": history.tax_event_id,
        "action": history.action,
        "actor": history.actor,
        "previous_status": history.previous_status,
        "new_status": history.new_status,
        "changed_fields": history.changed_fields or {},
        "note": history.note,
        "bulk_action_id": history.bulk_action_id,
        "created_at": created_at.isoformat() if created_at else None,
    }


def _source_document_dict(document) -> dict | None:
    if document is None:
        return None
    return {
        "document_id": document.id,
        "original_filename": document.original_filename,
    }


def _item_dict(
    item: ReviewItem,
    decision_history: list | None = None,
    source_document=None,
) -> dict:
    explanation_category = (item.category or (item.tax_event.category if item.tax_event else None))
    event = item.tax_event
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
        "group_id": item.tax_event.group_id if item.tax_event else None,
        "group_display": item.tax_event.group_display if item.tax_event else None,
        "source": event.source if event else None,
        "event_metadata": event.event_metadata if event else None,
        "source_document": _source_document_dict(source_document),
        "decision_history": [_history_dict(h) for h in (decision_history or [])],
        "explanation": build_tax_item_explanation(
            target_type="review_item",
            target_id=item.id,
            category=explanation_category,
            source="review",
        ),
    }


# ── GET /review/queue ─────────────────────────────────────────────────────────

@router.get("/review/queue")
async def get_review_queue(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    queue = await _engine.get_queue(workspace_id, db)
    all_items = queue.agent_required + queue.high_risk + queue.needs_review + queue.confirmed
    history_by_item = await review_repo.get_history_by_item_ids(db, [item.id for item in all_items])
    document_ids = sorted({
        item.tax_event.document_id
        for item in all_items
        if item.tax_event and item.tax_event.document_id
    })
    documents = await doc_repo.get_by_ids(db, document_ids)
    documents_by_id = {document.id: document for document in documents}
    return {
        "data": {
            "agent_required": {
                "items": [
                    _item_dict(
                        i,
                        history_by_item.get(i.id, []),
                        documents_by_id.get(i.tax_event.document_id) if i.tax_event and i.tax_event.document_id else None,
                    )
                    for i in queue.agent_required
                ],
                "count": len(queue.agent_required),
            },
            "high_risk": {
                "items": [
                    _item_dict(
                        i,
                        history_by_item.get(i.id, []),
                        documents_by_id.get(i.tax_event.document_id) if i.tax_event and i.tax_event.document_id else None,
                    )
                    for i in queue.high_risk
                ],
                "count": len(queue.high_risk),
            },
            "needs_review": {
                "items": [
                    _item_dict(
                        i,
                        history_by_item.get(i.id, []),
                        documents_by_id.get(i.tax_event.document_id) if i.tax_event and i.tax_event.document_id else None,
                    )
                    for i in queue.needs_review
                ],
                "count": len(queue.needs_review),
            },
            "confirmed": {
                "items": [
                    _item_dict(
                        i,
                        history_by_item.get(i.id, []),
                        documents_by_id.get(i.tax_event.document_id) if i.tax_event and i.tax_event.document_id else None,
                    )
                    for i in queue.confirmed
                ],
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
    history = await review_repo.get_history_for_item(db, item.id)
    document = None
    if item.tax_event and item.tax_event.document_id:
        document = await doc_repo.get_by_id(db, item.tax_event.document_id)
    return {"data": _item_dict(item, history, document)}


@router.get("/review/{item_id}/history")
async def get_review_item_history(
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
    history = await review_repo.get_history_for_item(db, item.id)
    return {
        "data": {
            "review_item_id": item.id,
            "history": [_history_dict(h) for h in history],
        }
    }


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
    await _reconcile_service.trigger(workspace_id=workspace_id, trigger_source="event_update", db=db)

    history = await review_repo.get_history_for_item(db, item.id)
    document = None
    if item.tax_event and item.tax_event.document_id:
        document = await doc_repo.get_by_id(db, item.tax_event.document_id)
    return {"data": _item_dict(item, history, document)}


@router.post("/review/{item_id}/undo")
async def undo_review_decision(
    item_id: str,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    item_before = await _engine.get_item(item_id, db)
    if item_before is None or item_before.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail=error_response("item_not_found", "Review item not found.", retryable=False),
        )
    try:
        item = await _engine.undo_latest_decision(item_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=error_response("undo_not_available", str(e), retryable=False),
        )
    await _reconcile_service.trigger(workspace_id=workspace_id, trigger_source="event_update", db=db)
    history = await review_repo.get_history_for_item(db, item.id)
    document = None
    if item.tax_event and item.tax_event.document_id:
        document = await doc_repo.get_by_id(db, item.tax_event.document_id)
    return {"data": _item_dict(item, history, document)}


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
    document = None
    if item.tax_event and item.tax_event.document_id:
        document = await doc_repo.get_by_id(db, item.tax_event.document_id)

    return {
        "data": {
            **_item_dict(item, source_document=document),
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
    await _reconcile_service.trigger(workspace_id=workspace_id, trigger_source="event_update", db=db)
    history_by_item = await review_repo.get_history_by_item_ids(db, [item.id for item in results])
    document_ids = sorted({
        item.tax_event.document_id
        for item in results
        if item.tax_event and item.tax_event.document_id
    })
    documents = await doc_repo.get_by_ids(db, document_ids)
    documents_by_id = {document.id: document for document in documents}

    return {
        "data": {
            "items": [
                _item_dict(
                    i,
                    history_by_item.get(i.id, []),
                    documents_by_id.get(i.tax_event.document_id) if i.tax_event and i.tax_event.document_id else None,
                )
                for i in results
            ],
            "count": len(results),
        }
    }


@router.post("/review/bulk-action/{bulk_action_id}/undo")
async def undo_bulk_review_decision(
    bulk_action_id: str,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    try:
        results = await _engine.undo_bulk_decision(workspace_id, bulk_action_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=error_response("undo_not_available", str(e), retryable=False),
        )
    await _reconcile_service.trigger(workspace_id=workspace_id, trigger_source="event_update", db=db)
    history_by_item = await review_repo.get_history_by_item_ids(db, [item.id for item in results])
    document_ids = sorted({
        item.tax_event.document_id
        for item in results
        if item.tax_event and item.tax_event.document_id
    })
    documents = await doc_repo.get_by_ids(db, document_ids)
    documents_by_id = {document.id: document for document in documents}

    return {
        "data": {
            "items": [
                _item_dict(
                    i,
                    history_by_item.get(i.id, []),
                    documents_by_id.get(i.tax_event.document_id) if i.tax_event and i.tax_event.document_id else None,
                )
                for i in results
            ],
            "count": len(results),
        }
    }


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
