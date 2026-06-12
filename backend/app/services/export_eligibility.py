from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EvidenceObligation
from app.services.explanations import build_evidence_obligation_explanation


@dataclass
class ExportEligibilityPreview:
    evidence_total: int
    evidence_required_total: int
    evidence_required_blocking_total: int
    evidence_required_missing_total: int
    evidence_required_partial_total: int
    evidence_required_matched_total: int
    evidence_recommended_missing_total: int
    evidence_recommended_partial_total: int
    evidence_recommended_matched_total: int
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
                )
            )
        ).scalars().all()

        required = [o for o in obligations if o.required_level == "required"]
        recommended = [o for o in obligations if o.required_level == "recommended"]
        required_missing = [o for o in required if o.status == "missing"]
        required_partial = [o for o in required if o.status == "partially_matched"]
        required_matched = [o for o in required if o.status == "matched"]
        recommended_missing = [o for o in recommended if o.status == "missing"]
        recommended_partial = [o for o in recommended if o.status == "partially_matched"]
        recommended_matched = [o for o in recommended if o.status == "matched"]
        blocking = required_missing + required_partial
        blocking_rows = [
            {
                "id": o.id,
                "obligation_key": o.obligation_key,
                "label": o.label,
                "description": o.description,
                "category": o.category,
                "required_level": o.required_level,
                "status": o.status,
                "reason": o.reason,
                "rule_version": o.rule_version,
                "explanation": build_evidence_obligation_explanation(
                    target_id=o.id,
                    obligation_key=o.obligation_key,
                    obligation_category=o.category,
                    rule_version=o.rule_version,
                    source="rule",
                ),
            }
            for o in blocking
        ]

        return ExportEligibilityPreview(
            evidence_total=len(obligations),
            evidence_required_total=len(required),
            evidence_required_blocking_total=len(blocking),
            evidence_required_missing_total=len(required_missing),
            evidence_required_partial_total=len(required_partial),
            evidence_required_matched_total=len(required_matched),
            evidence_recommended_missing_total=len(recommended_missing),
            evidence_recommended_partial_total=len(recommended_partial),
            evidence_recommended_matched_total=len(recommended_matched),
            blocking_evidence_obligations=blocking_rows,
            would_block_export=len(blocking) > 0,
        )
