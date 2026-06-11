from datetime import timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EvidenceMatchDecisionHistory


def _normalize_created_at(history: EvidenceMatchDecisionHistory) -> EvidenceMatchDecisionHistory:
    if history.created_at is not None and history.created_at.tzinfo is None:
        history.created_at = history.created_at.replace(tzinfo=timezone.utc)
    return history


async def create_match_history(
    db: AsyncSession,
    *,
    workspace_id: str,
    evidence_match_id: str,
    evidence_obligation_id: str,
    action: str,
    actor: str,
    previous_status: str | None,
    new_status: str | None,
    note: str | None = None,
) -> EvidenceMatchDecisionHistory:
    history = EvidenceMatchDecisionHistory(
        workspace_id=workspace_id,
        evidence_match_id=evidence_match_id,
        evidence_obligation_id=evidence_obligation_id,
        action=action,
        actor=actor,
        previous_status=previous_status,
        new_status=new_status,
        note=note,
    )
    db.add(history)
    await db.flush()
    return _normalize_created_at(history)


async def get_history_by_match_ids(
    db: AsyncSession,
    match_ids: list[str],
) -> dict[str, list[EvidenceMatchDecisionHistory]]:
    if not match_ids:
        return {}
    result = await db.execute(
        select(EvidenceMatchDecisionHistory)
        .where(EvidenceMatchDecisionHistory.evidence_match_id.in_(match_ids))
        .order_by(EvidenceMatchDecisionHistory.created_at.desc())
    )
    grouped: dict[str, list[EvidenceMatchDecisionHistory]] = {match_id: [] for match_id in match_ids}
    for history in result.scalars().all():
        grouped.setdefault(history.evidence_match_id, []).append(_normalize_created_at(history))
    return grouped


async def get_latest_history_for_match(
    db: AsyncSession,
    match_id: str,
) -> EvidenceMatchDecisionHistory | None:
    result = await db.execute(
        select(EvidenceMatchDecisionHistory)
        .where(EvidenceMatchDecisionHistory.evidence_match_id == match_id)
        .order_by(EvidenceMatchDecisionHistory.created_at.desc())
        .limit(1)
    )
    history = result.scalar_one_or_none()
    return _normalize_created_at(history) if history is not None else None
