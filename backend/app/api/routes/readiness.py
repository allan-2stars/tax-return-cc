from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.db.models import EvidenceMatch, EvidenceObligation, InterviewSession, TaxEvent, TaxProfile, Workspace
from app.engines.readiness import ReadinessEngine, _get_fy_end_date
from app.engines.interview import BRANCH_QUESTIONS, PLATFORM_QUESTIONS, _QUESTION_BY_ID
from app.repositories import readiness as readiness_repo
from app.services.evidence_freshness import build_evidence_freshness
from app.repositories import profiles as profile_repo
from app.services.evidence_rules import CURRENT_EVIDENCE_RULE_VERSION

router = APIRouter()

_engine = ReadinessEngine()


def _score_to_dict(score) -> dict:
    return {
        "percentage": score.percentage,
        "breakdown": [
            {
                "skill_id": b.skill_id,
                "percentage": b.percentage,
                "achieved_weight": b.achieved_weight,
                "total_weight": b.total_weight,
            }
            for b in score.breakdown
        ],
        "missing_items_count": len(score.missing_items),
        "review_items_count": len(score.review_items),
        "agent_items_count": len(score.agent_items),
        "is_stale": score.is_stale,
        "calculated_at": score.calculated_at.isoformat(),
    }


async def _resolve_financial_year(workspace_id: str, db: AsyncSession) -> str:
    profile = await db.scalar(select(TaxProfile).where(TaxProfile.workspace_id == workspace_id))
    if profile:
        return profile.financial_year
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    return workspace.financial_year if workspace else "2024-25"


async def _evidence_obligation_summary(workspace_id: str, db: AsyncSession) -> dict:
    financial_year = await _resolve_financial_year(workspace_id, db)
    obligations = (
        await db.execute(
            select(EvidenceObligation).where(
                EvidenceObligation.workspace_id == workspace_id,
                EvidenceObligation.financial_year == financial_year,
            )
        )
    ).scalars().all()

    required = [o for o in obligations if o.required_level == "required"]
    recommended = [o for o in obligations if o.required_level == "recommended"]

    def _count(items, status: str) -> int:
        return sum(1 for i in items if i.status == status)

    blocking = [
        {
            "id": o.id,
            "obligation_key": o.obligation_key,
            "label": o.label,
            "category": o.category,
            "required_level": o.required_level,
            "status": o.status,
            "reason": o.reason,
        }
        for o in required
        if o.status in {"missing", "partially_matched"}
    ]

    return {
        "total_obligations": len(obligations),
        "required_missing": _count(required, "missing"),
        "required_partially_matched": _count(required, "partially_matched"),
        "required_matched": _count(required, "matched"),
        "recommended_missing": _count(recommended, "missing"),
        "recommended_partially_matched": _count(recommended, "partially_matched"),
        "recommended_matched": _count(recommended, "matched"),
        "blocking_evidence_obligations": blocking,
    }


def _compute_incomplete_required_questions(session: InterviewSession | None) -> list[dict]:
    if session is None:
        return []

    answers = session.answers or {}
    skipped_ids = [
        (s.get("question_id") if isinstance(s, dict) else s)
        for s in (session.skipped_steps or [])
    ]

    active_conditional_ids: set[str] = set()
    for q in _QUESTION_BY_ID.values():
        if not q.branches:
            continue
        ans = answers.get(q.id)
        if ans is None:
            continue
        selected = q.branches.get(str(ans))
        if selected:
            active_conditional_ids.update(selected)

    incomplete: list[dict] = []
    for qid in skipped_ids:
        if not qid:
            continue
        q = _QUESTION_BY_ID.get(str(qid))
        if q is None:
            continue
        if not q.required:
            continue
        in_scope = (
            q.id in PLATFORM_QUESTIONS
            or q.id in BRANCH_QUESTIONS
            or q.id in active_conditional_ids
        )
        if not in_scope:
            continue
        answered = answers.get(q.id)
        if answered is not None and str(answered).strip() != "":
            continue
        incomplete.append(
            {
                "question_id": q.id,
                "question_label": q.ask,
                "editable": True,
            }
        )
    return incomplete


async def _build_readiness_2_0(workspace_id: str, db: AsyncSession) -> dict:
    financial_year = await _resolve_financial_year(workspace_id, db)

    session = (
        await db.execute(
            select(InterviewSession)
            .where(
                InterviewSession.workspace_id == workspace_id,
                InterviewSession.financial_year == financial_year,
            )
            .order_by(InterviewSession.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    events = (
        await db.execute(
            select(TaxEvent).where(
                TaxEvent.workspace_id == workspace_id,
                TaxEvent.financial_year == financial_year,
            )
        )
    ).scalars().all()
    obligations = (
        await db.execute(
            select(EvidenceObligation).where(
                EvidenceObligation.workspace_id == workspace_id,
                EvidenceObligation.financial_year == financial_year,
            )
        )
    ).scalars().all()
    matches = (
        await db.execute(
            select(EvidenceMatch)
            .join(EvidenceObligation, EvidenceObligation.id == EvidenceMatch.obligation_id)
            .where(
                EvidenceMatch.workspace_id == workspace_id,
                EvidenceObligation.financial_year == financial_year,
            )
        )
    ).scalars().all()

    blocking_reasons: list[str] = []
    warnings: list[str] = []

    # Journey dimension
    journey_complete = session is not None and session.state in {"awaiting_evidence", "complete"}
    incomplete_questions = _compute_incomplete_required_questions(session)
    has_incomplete_questions = len(incomplete_questions) > 0
    journey_blockers = len(incomplete_questions)
    if not journey_complete:
        blocking_reasons.append("Tax Journey is not complete.")
    if journey_blockers > 0:
        blocking_reasons.append("Complete required Tax Journey questions.")
    journey_state = "blocked" if (not journey_complete or journey_blockers > 0) else "ready"

    # Review dimension
    confirmed_count = sum(1 for e in events if e.status == "confirmed")
    needs_user_review_count = sum(1 for e in events if e.status == "needs_user_review")
    needs_agent_review_count = sum(1 for e in events if e.status == "needs_agent_review")
    rejected_or_flagged_count = sum(1 for e in events if e.status in {"rejected", "flagged", "high_risk"})
    unconfirmed_total = max(0, len(events) - confirmed_count)
    review_state = "ready"
    if needs_agent_review_count > 0:
        warnings.append("Some items still need tax agent review.")
        review_state = "warning"
    if needs_user_review_count > 0:
        warnings.append("Some items still need your review.")
        review_state = "warning"
    if rejected_or_flagged_count > 0:
        warnings.append("Some review items are flagged and need attention.")
        review_state = "warning"

    # Evidence dimension
    required = [o for o in obligations if o.required_level == "required"]
    recommended = [o for o in obligations if o.required_level == "recommended"]
    required_missing_count = sum(1 for o in required if o.status == "missing")
    required_partial_count = sum(1 for o in required if o.status == "partially_matched")
    required_matched_count = sum(1 for o in required if o.status == "matched")
    recommended_missing_count = sum(1 for o in recommended if o.status == "missing")
    candidate_match_count = sum(1 for m in matches if m.status == "candidate")
    accepted_match_count = sum(1 for m in matches if m.status == "accepted")
    rejected_match_count = sum(1 for m in matches if m.status == "rejected")
    blocking_obligations = [
        {
            "id": o.id,
            "obligation_key": o.obligation_key,
            "label": o.label,
            "category": o.category,
            "required_level": o.required_level,
            "status": o.status,
            "reason": o.reason,
            "rule_version": o.rule_version,
        }
        for o in required
        if o.status in {"missing", "partially_matched"}
    ]
    if required_missing_count > 0 or required_partial_count > 0:
        blocking_reasons.append("Required evidence is incomplete.")
        evidence_state = "blocked"
    elif recommended_missing_count > 0:
        warnings.append("Some recommended evidence is still missing.")
        evidence_state = "warning"
    else:
        evidence_state = "ready"

    # Scores (readiness_2_0 only)
    journey_score = 100 if journey_state == "ready" else 0
    review_total = max(1, len(events))
    review_score = int(
        round(
            (
                confirmed_count * 1.0
                + needs_user_review_count * 0.5
                + needs_agent_review_count * 0.25
            ) / review_total * 100
        )
    )
    evidence_total_required = max(1, len(required))
    evidence_score = int(
        round(
            (
                required_matched_count * 1.0
                + required_partial_count * 0.5
            ) / evidence_total_required * 100
        )
    )
    overall_score = int(round(journey_score * 0.4 + review_score * 0.3 + evidence_score * 0.3))
    if blocking_reasons:
        overall_state = "blocked"
        overall_label = "Not Ready"
    elif warnings:
        overall_state = "warning"
        overall_label = "Needs Attention"
    else:
        overall_state = "ready"
        overall_label = "Ready"

    return {
        "overall": {
            "state": overall_state,
            "score": overall_score,
            "label": overall_label,
        },
        "journey": {
            "is_complete": journey_complete,
            "has_incomplete_questions": has_incomplete_questions,
            "required_blockers_count": journey_blockers,
            "incomplete_questions": incomplete_questions,
            "state": journey_state,
        },
        "review": {
            "unconfirmed_total": unconfirmed_total,
            "needs_user_review_count": needs_user_review_count,
            "needs_agent_review_count": needs_agent_review_count,
            "confirmed_count": confirmed_count,
            "rejected_or_flagged_count": rejected_or_flagged_count,
            "state": review_state,
        },
        "evidence": {
            "required_missing_count": required_missing_count,
            "required_partial_count": required_partial_count,
            "required_matched_count": required_matched_count,
            "recommended_missing_count": recommended_missing_count,
            "candidate_match_count": candidate_match_count,
            "accepted_match_count": accepted_match_count,
            "rejected_match_count": rejected_match_count,
            "blocking_obligations": blocking_obligations,
            "state": evidence_state,
            "current_rule_version": CURRENT_EVIDENCE_RULE_VERSION,
        },
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "last_calculated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── GET /readiness ────────────────────────────────────────────────────────────

@router.get("/readiness")
async def get_readiness(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    evidence_summary = await _evidence_obligation_summary(workspace_id, db)
    readiness_2_0 = await _build_readiness_2_0(workspace_id, db)
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    freshness = build_evidence_freshness(workspace)
    existing = await readiness_repo.get_score(db, workspace_id)
    if not existing:
        return {
            "data": {
                "percentage": 0,
                "breakdown": [],
                "missing_items_count": 0,
                "review_items_count": 0,
                "agent_items_count": 0,
                "is_stale": True,
                "calculated_at": None,
                "evidence_obligation_summary": evidence_summary,
                "evidence_freshness": freshness,
                "readiness_2_0": readiness_2_0,
            }
        }
    return {
        "data": {
            "percentage": int(existing.percentage),
            "breakdown": existing.breakdown or [],
            "missing_items_count": len(existing.missing_items or []),
            "review_items_count": len(existing.review_items or []),
            "agent_items_count": len(existing.agent_items or []),
            "is_stale": existing.is_stale,
            "calculated_at": (
                existing.calculated_at.isoformat() if existing.calculated_at else None
            ),
            "evidence_obligation_summary": evidence_summary,
            "evidence_freshness": freshness,
            "readiness_2_0": readiness_2_0,
        }
    }


# ── POST /readiness/recalculate ───────────────────────────────────────────────

@router.post("/readiness/recalculate")
async def recalculate_readiness(
    background_tasks: BackgroundTasks,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    await readiness_repo.mark_stale(db, workspace_id)
    background_tasks.add_task(_engine.recalculate, workspace_id)
    return {"data": {"status": "recalculating"}}


# ── GET /readiness/missing ────────────────────────────────────────────────────

@router.get("/readiness/missing")
async def get_missing_items(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await profile_repo.get_by_workspace(db, workspace_id)
    financial_year = profile.financial_year if profile else "2024-25"

    fy_end = _get_fy_end_date(financial_year)
    fy_ended = datetime.now(timezone.utc).date() >= fy_end

    missing = await _engine.get_missing_items(workspace_id, db)

    available_now = []
    available_after_fy = []
    for item in missing:
        if item.available_after_fy and not fy_ended:
            available_after_fy.append({
                "requirement_id": item.requirement_id,
                "display": item.display,
                "weight": item.weight,
                "skill_id": item.skill_id,
                "how_to_get": item.how_to_get,
            })
        else:
            available_now.append({
                "requirement_id": item.requirement_id,
                "display": item.display,
                "weight": item.weight,
                "skill_id": item.skill_id,
                "how_to_get": item.how_to_get,
            })

    return {
        "data": {
            "available_now": available_now,
            "available_after_fy": available_after_fy,
        }
    }
