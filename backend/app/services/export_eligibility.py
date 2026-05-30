from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EvidenceObligation


@dataclass
class ExportEligibilityPreview:
    evidence_required_total: int
    evidence_required_blocking_total: int
    evidence_required_missing_total: int
    evidence_required_partial_total: int
    blocking_evidence_obligations: list[dict]
    would_block_export: bool


class ExportEligibilityService:
    async def build_preview(
        self,
        *,
        workspace_id: str,
        financial_year: str,
        db: AsyncSession,
    ) -> ExportEligibilityPreview:
        obligations = (
            await db.execute(
                select(EvidenceObligation).where(
                    EvidenceObligation.workspace_id == workspace_id,
                    EvidenceObligation.financial_year == financial_year,
                    EvidenceObligation.required_level == "required",
                )
            )
        ).scalars().all()

        missing = [o for o in obligations if o.status == "missing"]
        partial = [o for o in obligations if o.status == "partially_matched"]
        blocking = missing + partial
        blocking_rows = [
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
            for o in blocking
        ]

        return ExportEligibilityPreview(
            evidence_required_total=len(obligations),
            evidence_required_blocking_total=len(blocking),
            evidence_required_missing_total=len(missing),
            evidence_required_partial_total=len(partial),
            blocking_evidence_obligations=blocking_rows,
            would_block_export=len(blocking) > 0,
        )
