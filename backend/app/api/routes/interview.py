from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.db.models import InterviewSession
from app.engines.interview import (
    InterviewEngine, InlineQuestion, _QUESTION_BY_ID,
    BRANCH_QUESTIONS, PLATFORM_QUESTIONS,
)
from app.errors import error_response
from app.repositories import auth as auth_repo
from app.repositories import interview as interview_repo
from app.skills.base import Question

router = APIRouter()

_engine = InterviewEngine()


# ── Summary constants ─────────────────────────────────────────────────────────

# Canonical order for "Your situation" answers: platform questions then branch questions
_ORDERED_PLATFORM_IDS: list[str] = (
    [q.id for q in PLATFORM_QUESTIONS] + [q.id for q in BRANCH_QUESTIONS]
)

_QUESTION_DISPLAY_LABELS: dict[str, str] = {
    "fy_confirm":           "Financial year",
    "residency":            "Residency status",
    "employment_type":      "Work situation",
    "family_situation":     "Family situation",
    "lodger_type":          "Lodging method",
    "spouse_income_range":  "Spouse income range",
    "spouse_novated_lease": "Spouse novated lease",
    "spouse_rfba_amount":   "Spouse's reportable fringe benefits",
    "dependent_count":      "Number of dependents",
}

_ANSWER_DISPLAY_LABELS: dict[str, dict[str, str]] = {
    "residency": {
        "resident":     "Australian resident",
        "non_resident": "Non-resident",
        "part_year":    "Part-year resident",
    },
    "employment_type": {
        "employee":    "Employee (PAYG)",
        "sole_trader": "Sole trader",
        "both":        "Both",
    },
    "family_situation": {
        "single_no_dependents": "Single, no dependents",
        "has_spouse":           "Have a spouse",
        "has_dependents":       "Have dependents",
        "both":                 "Spouse and dependents",
    },
    "lodger_type": {
        "self":    "Self-lodging",
        "agent":   "Tax agent",
        "unknown": "Not sure yet",
    },
    "spouse_income_range": {
        "under_18200":  "Under $18,200",
        "18200_45000":  "$18,200 – $45,000",
        "45000_120000": "$45,000 – $120,000",
        "over_120000":  "Over $120,000",
    },
    "spouse_novated_lease": {
        "yes":      "Yes",
        "no":       "No",
        "not_sure": "Not sure",
    },
}

_SKILL_SECTION_TITLES: dict[str, str] = {
    "employee_tax_au": "Your employment",
    "wfh_skill":       "Work from home",
    "crypto_skill_au": "Cryptocurrency",
    "investment_skill": "Investments",
}


# ── Request bodies ────────────────────────────────────────────────────────────

class AnswerRequest(BaseModel):
    question_id: str
    answer: str


class SkipRequest(BaseModel):
    question_id: str
    reason: str = ""


class JumpRequest(BaseModel):
    question_id: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_answer(question_id: str, answer_value: str) -> str:
    labels = _ANSWER_DISPLAY_LABELS.get(question_id, {})
    return labels.get(answer_value, answer_value)


def _q_dict(q: Question | None) -> dict | None:
    if q is None:
        return None
    return {
        "id": q.id,
        "ask": q.ask,
        "type": q.type,
        "options": q.options,
        "branches": q.branches,
        "required": q.required,
        "why": q.why,
        "hint": q.hint,
        "currency": q.currency,
    }


def _current_question(session: InterviewSession) -> dict | None:
    qid = (session.current_step or {}).get("id")
    if not qid:
        return None
    q = _QUESTION_BY_ID.get(qid)
    return _q_dict(q) if q else {"id": qid}


def _progress(session: InterviewSession) -> dict:
    completed = len(session.completed_steps or []) + len(session.skipped_steps or [])
    total = completed + len(session.pending_queue or []) + (1 if session.current_step else 0)
    return {"completed": completed, "total": total}


def _no_session_error() -> HTTPException:
    return HTTPException(
        status_code=409,
        detail=error_response(
            "interview_not_started",
            "No active interview session. Please start the interview first.",
            action="start_interview",
            retryable=False,
        ),
    )



# ── GET /interview/session ────────────────────────────────────────────────────

@router.get("/interview/session")
async def get_session(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    session = await interview_repo.get_active_by_workspace(db, workspace_id)
    if not session:
        return {
            "data": {
                "state": "not_started",
                "current_question": None,
                "progress": {"completed": 0, "total": 0},
            }
        }
    # Auto-complete sessions that finished answering but never called /complete
    if session.state == "in_progress" and not (session.current_step or {}).get("id"):
        session = await _engine.complete(session.id, db)
    return {
        "data": {
            "state": session.state,
            "session_id": session.id,
            "current_question": _current_question(session),
            "answers": session.answers or {},
            "activated_skills": session.activated_skills or [],
            "progress": _progress(session),
        }
    }


# ── POST /interview/start ─────────────────────────────────────────────────────

@router.post("/interview/start")
async def start_interview(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    # Return existing in-progress/paused session rather than creating a duplicate
    existing = await interview_repo.get_active_by_workspace(db, workspace_id)
    if existing and existing.state in ("in_progress", "paused"):
        return {
            "data": {
                "state": existing.state,
                "session_id": existing.id,
                "current_question": _current_question(existing),
                "progress": _progress(existing),
                "resumed": True,
            }
        }

    ws = await auth_repo.get_singleton_workspace(db)
    financial_year = ws.financial_year if ws else "2024-25"
    session, first_q = await _engine.start(workspace_id, financial_year, db)
    return {
        "data": {
            "state": session.state,
            "session_id": session.id,
            "current_question": _q_dict(first_q),
            "progress": _progress(session),
        }
    }


# ── POST /interview/answer ────────────────────────────────────────────────────

@router.post("/interview/answer")
async def answer_question(
    body: AnswerRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    session = await interview_repo.get_active_by_workspace(db, workspace_id)
    if not session:
        raise _no_session_error()

    try:
        session, next_q = await _engine.process_answer(
            session.id, body.question_id, body.answer, db
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=error_response("invalid_answer", str(e), retryable=False),
        )

    return {
        "data": {
            "session_id": session.id,
            "state": session.state,
            "next_question": _q_dict(next_q),
            "activated_skills": session.activated_skills or [],
            "progress": _progress(session),
        }
    }


# ── POST /interview/skip ──────────────────────────────────────────────────────

@router.post("/interview/skip")
async def skip_question(
    body: SkipRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    session = await interview_repo.get_active_by_workspace(db, workspace_id)
    if not session:
        raise _no_session_error()

    session, next_q = await _engine.skip(session.id, body.question_id, body.reason, db)
    return {
        "data": {
            "session_id": session.id,
            "state": session.state,
            "next_question": _q_dict(next_q),
            "progress": _progress(session),
        }
    }


# ── POST /interview/back ──────────────────────────────────────────────────────

@router.post("/interview/back")
async def go_back(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    session = await interview_repo.get_active_by_workspace(db, workspace_id)
    if not session:
        raise _no_session_error()

    try:
        session, prev_q = await _engine.go_back(session.id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=error_response("cannot_go_back", str(e), retryable=False),
        )

    return {
        "data": {
            "session_id": session.id,
            "state": session.state,
            "current_question": _q_dict(prev_q),
            "progress": _progress(session),
        }
    }


# ── POST /interview/complete ──────────────────────────────────────────────────

@router.post("/interview/complete")
async def complete_interview(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    session = await interview_repo.get_active_by_workspace(db, workspace_id)
    if not session:
        raise _no_session_error()

    session = await _engine.complete(session.id, db)
    return {
        "data": {
            "session_id": session.id,
            "state": session.state,
        }
    }


# ── POST /interview/pause ─────────────────────────────────────────────────────

@router.post("/interview/pause")
async def pause_interview(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    session = await interview_repo.get_active_by_workspace(db, workspace_id)
    if not session:
        raise _no_session_error()

    session = await _engine.pause(session.id, db)
    return {
        "data": {
            "session_id": session.id,
            "state": session.state,
        }
    }


# ── GET /interview/summary ────────────────────────────────────────────────────

@router.get("/interview/summary")
async def get_summary(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    session = await interview_repo.get_active_by_workspace(db, workspace_id)
    if not session:
        raise _no_session_error()

    answers = session.answers or {}
    sections = []

    # "Your situation" section: platform + branch questions in canonical order
    situation_answers = []
    for qid in _ORDERED_PLATFORM_IDS:
        val = answers.get(qid)
        if val is not None:
            situation_answers.append({
                "question_id":    qid,
                "question_label": _QUESTION_DISPLAY_LABELS.get(qid, qid),
                "answer_value":   val,
                "answer_label":   _format_answer(qid, val),
                "editable":       True,
            })
    if situation_answers:
        sections.append({"title": "Your situation", "answers": situation_answers})

    # One section per activated skill — use skill registry directly so skill
    # questions are always available even after a server restart (they are not
    # pre-loaded into _QUESTION_BY_ID; they're added lazily during process_answer).
    for skill_id in (session.activated_skills or []):
        skill = _engine._registry.get_skill(skill_id)
        if not skill:
            continue
        skill_q_map = {q.id: q for q in skill.get_questions(None)}
        skill_answers = []
        for qid, val in answers.items():
            if qid in skill_q_map:
                q = skill_q_map[qid]
                skill_answers.append({
                    "question_id":    qid,
                    "question_label": q.ask,
                    "answer_value":   val,
                    "answer_label":   val,
                    "editable":       True,
                })
        if skill_answers:
            title = _SKILL_SECTION_TITLES.get(skill_id, skill_id)
            sections.append({"title": title, "answers": skill_answers})

    return {"data": {"sections": sections}}


# ── POST /interview/jump ──────────────────────────────────────────────────────

@router.post("/interview/jump")
async def jump_to_question(
    body: JumpRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    session = await interview_repo.get_active_by_workspace(db, workspace_id)
    if not session:
        raise _no_session_error()

    try:
        session, q = await _engine.jump(session.id, body.question_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=error_response("question_not_found", str(e), retryable=False),
        )

    return {
        "data": {
            "session_id":       session.id,
            "state":            session.state,
            "current_question": _q_dict(q),
            "progress":         _progress(session),
        }
    }
