from fastapi import APIRouter, Depends
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.db.models import Document, EvidenceMatch, EvidenceObligation, TaxEvent, TaxProfile, Workspace
from app.errors import error_response
from app.services.evidence_freshness import build_evidence_freshness
from app.services.evidence_reconcile import EvidenceReconcileService
from app.services.explanations import build_evidence_obligation_explanation
from app.services.evidence_rules import CURRENT_EVIDENCE_RULE_VERSION

router = APIRouter()
_reconcile_service = EvidenceReconcileService()


class MatchDecisionRequest(BaseModel):
    status: str


def _to_dict(
    obligation: EvidenceObligation,
    matches: list[EvidenceMatch],
    doc_map: dict[str, Document],
    event_map: dict[str, TaxEvent],
) -> dict:
    match_items: list[dict] = []
    for match in matches:
        doc = doc_map.get(match.document_id) if match.document_id else None
        event = event_map.get(match.tax_event_id) if match.tax_event_id else None
        match_items.append(
            {
                "id": match.id,
                "match_type": match.match_type,
                "status": match.status,
                "confidence": match.confidence,
                "reason": match.reason,
                "document": (
                    {
                        "id": doc.id,
                        "original_filename": doc.original_filename,
                        "document_type": doc.document_type,
                        "status": doc.status,
                    }
                    if doc
                    else None
                ),
                "tax_event": (
                    {
                        "id": event.id,
                        "event_type": event.event_type,
                        "category": event.category,
                        "status": event.status,
                    }
                    if event
                    else None
                ),
            }
        )
    return {
        "id": obligation.id,
        "workspace_id": obligation.workspace_id,
        "financial_year": obligation.financial_year,
        "source_type": obligation.source_type,
        "source_id": obligation.source_id,
        "obligation_key": obligation.obligation_key,
        "category": obligation.category,
        "label": obligation.label,
        "description": obligation.description,
        "required_level": obligation.required_level,
        "status": obligation.status,
        "reason": obligation.reason,
        "rule_version": obligation.rule_version,
        "explanation": build_evidence_obligation_explanation(
            target_id=obligation.id,
            obligation_key=obligation.obligation_key,
            obligation_category=obligation.category,
            rule_version=obligation.rule_version,
            source="rule",
        ),
        "matches": match_items,
        "metadata_json": obligation.metadata_json or {},
        "created_at": obligation.created_at.isoformat() if obligation.created_at else None,
        "updated_at": obligation.updated_at.isoformat() if obligation.updated_at else None,
    }


async def _resolve_financial_year(workspace_id: str, db: AsyncSession) -> str:
    profile = await db.scalar(select(TaxProfile).where(TaxProfile.workspace_id == workspace_id))
    if profile:
        return profile.financial_year
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    return workspace.financial_year if workspace else "2024-25"


@router.post("/evidence/reconcile")
async def reconcile(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    outcome = await _reconcile_service.trigger(
        workspace_id=workspace_id,
        trigger_source="manual_reconcile",
        force=True,
        db=db,
        raise_on_error=False,
    )
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    financial_year = outcome.get("financial_year") or (workspace.financial_year if workspace else None)
    obligations_by_rule_version: dict[str, int] = {}
    if financial_year:
        rows = (
            await db.execute(
                select(
                    EvidenceObligation.rule_version,
                    func.count(EvidenceObligation.id),
                ).where(
                    EvidenceObligation.workspace_id == workspace_id,
                    EvidenceObligation.financial_year == financial_year,
                ).group_by(EvidenceObligation.rule_version)
            )
        ).all()
        obligations_by_rule_version = {
            (rule_version if rule_version is not None else "unknown"): int(count)
            for rule_version, count in rows
        }
    return {
        "data": {
            "status": outcome.get("status", "ok"),
            "obligations_count": int(outcome.get("obligations_count", 0)),
            "telemetry": {
                "financial_year": outcome.get("financial_year"),
                "reconcile_duration_ms": outcome.get("reconcile_duration_ms"),
                "obligations_created": outcome.get("obligations_created", 0),
                "matches_created": outcome.get("matches_created", 0),
                "reconcile_failures": outcome.get("reconcile_failures", 0),
                "skipped": outcome.get("skipped", False),
                "skip_reason": outcome.get("skip_reason"),
                "debounce_window_seconds": outcome.get("debounce_window_seconds"),
                "previous_reconciled_at": outcome.get("previous_reconciled_at"),
                "current_rule_version": CURRENT_EVIDENCE_RULE_VERSION,
                "obligations_by_rule_version": obligations_by_rule_version,
            },
            "freshness": build_evidence_freshness(workspace),
        }
    }


@router.get("/evidence/obligations")
async def list_obligations(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    financial_year = await _resolve_financial_year(workspace_id, db)
    obligations: list[EvidenceObligation] = (
        await db.execute(
            select(EvidenceObligation)
            .where(
                EvidenceObligation.workspace_id == workspace_id,
                EvidenceObligation.financial_year == financial_year,
            )
            .order_by(EvidenceObligation.created_at.asc())
        )
    ).scalars().all()
    obligation_ids = [o.id for o in obligations]

    matches: list[EvidenceMatch] = []
    if obligation_ids:
        matches = (
            await db.execute(
                select(EvidenceMatch).where(
                    EvidenceMatch.workspace_id == workspace_id,
                    EvidenceMatch.obligation_id.in_(obligation_ids),
                )
            )
        ).scalars().all()
    matches_by_obligation: dict[str, list[EvidenceMatch]] = {}
    for match in matches:
        matches_by_obligation.setdefault(match.obligation_id, []).append(match)

    doc_ids = sorted({m.document_id for m in matches if m.document_id})
    event_ids = sorted({m.tax_event_id for m in matches if m.tax_event_id})

    docs = []
    if doc_ids:
        docs = (
            await db.execute(
                select(Document).where(
                    Document.workspace_id == workspace_id,
                    Document.financial_year == financial_year,
                    Document.id.in_(doc_ids),
                )
            )
        ).scalars().all()
    events = []
    if event_ids:
        events = (
            await db.execute(
                select(TaxEvent).where(
                    TaxEvent.workspace_id == workspace_id,
                    TaxEvent.financial_year == financial_year,
                    TaxEvent.id.in_(event_ids),
                )
            )
        ).scalars().all()

    doc_map = {d.id: d for d in docs}
    event_map = {e.id: e for e in events}

    return {
        "data": {
            "obligations": [
                _to_dict(
                    o,
                    matches_by_obligation.get(o.id, []),
                    doc_map,
                    event_map,
                )
                for o in obligations
            ],
            "freshness": build_evidence_freshness(workspace),
        }
    }


@router.patch("/evidence/matches/{match_id}")
async def decide_match(
    match_id: str,
    body: MatchDecisionRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    status = (body.status or "").strip().lower()
    if status not in {"accepted", "rejected"}:
        raise HTTPException(
            status_code=422,
            detail=error_response(
                "invalid_match_status",
                "Status must be accepted or rejected.",
                retryable=False,
            ),
        )

    financial_year = await _resolve_financial_year(workspace_id, db)

    match = await db.scalar(
        select(EvidenceMatch).where(
            EvidenceMatch.id == match_id,
            EvidenceMatch.workspace_id == workspace_id,
        )
    )
    if match is None:
        raise HTTPException(
            status_code=404,
            detail=error_response("match_not_found", "Evidence match not found.", retryable=False),
        )

    obligation = await db.scalar(
        select(EvidenceObligation).where(
            EvidenceObligation.id == match.obligation_id,
            EvidenceObligation.workspace_id == workspace_id,
            EvidenceObligation.financial_year == financial_year,
        )
    )
    if obligation is None:
        raise HTTPException(
            status_code=404,
            detail=error_response("match_not_found", "Evidence match not found.", retryable=False),
        )

    match.status = status
    await db.flush()

    all_matches = (
        await db.execute(
            select(EvidenceMatch).where(
                EvidenceMatch.workspace_id == workspace_id,
                EvidenceMatch.obligation_id == obligation.id,
            )
        )
    ).scalars().all()

    has_accepted = any(m.status == "accepted" for m in all_matches)
    has_candidate = any(m.status == "candidate" for m in all_matches)
    if has_accepted:
        obligation.status = "matched"
    elif has_candidate:
        obligation.status = "partially_matched"
    else:
        obligation.status = "missing"

    await db.commit()
    await db.refresh(match)
    await db.refresh(obligation)

    return {
        "data": {
            "match": {
                "id": match.id,
                "status": match.status,
            },
            "obligation": {
                "id": obligation.id,
                "status": obligation.status,
            },
        }
    }
