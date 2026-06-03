from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EvidenceMatch, EvidenceObligation, TaxProfile, Workspace
from app.engines.evidence_obligations import reconcile_evidence_obligations

logger = logging.getLogger(__name__)

TriggerSource = Literal[
    "document_upload",
    "document_delete",
    "event_create",
    "event_update",
    "event_delete",
    "manual_reconcile",
    "restore_apply",
]


class EvidenceReconcileService:
    _DEFAULT_DEBOUNCE_SECONDS = 3

    async def trigger(
        self,
        *,
        workspace_id: str,
        financial_year: str | None = None,
        trigger_source: TriggerSource,
        force: bool = False,
        db: AsyncSession,
        raise_on_error: bool = False,
    ) -> dict:
        workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
        if workspace is None:
            logger.warning(
                "Evidence reconcile skipped: workspace not found (workspace_id=%s, source=%s)",
                workspace_id,
                trigger_source,
            )
            return {"status": "skipped", "reason": "workspace_not_found"}

        resolved_fy = financial_year or await self._resolve_financial_year(workspace_id, db, workspace)
        if not resolved_fy:
            workspace.evidence_reconcile_status = "failed"
            workspace.evidence_reconcile_meta = {
                **(workspace.evidence_reconcile_meta or {}),
                "last_trigger_source": trigger_source,
                "last_error": "financial_year_unresolved",
                "reconcile_failures": int((workspace.evidence_reconcile_meta or {}).get("reconcile_failures", 0)) + 1,
            }
            await db.commit()
            logger.warning(
                "Evidence reconcile failed: financial year unresolved (workspace_id=%s, source=%s)",
                workspace_id,
                trigger_source,
            )
            return {"status": "failed", "reason": "financial_year_unresolved"}

        debounce_seconds = self._DEFAULT_DEBOUNCE_SECONDS
        if not force and workspace.evidence_reconciled_at is not None:
            now = datetime.now(timezone.utc)
            last = workspace.evidence_reconciled_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if (now - last).total_seconds() < debounce_seconds:
                workspace.evidence_reconcile_status = "succeeded"
                workspace.evidence_reconcile_meta = {
                    **(workspace.evidence_reconcile_meta or {}),
                    "last_trigger_source": trigger_source,
                    "skipped": True,
                    "skip_reason": "debounce_window",
                    "previous_reconciled_at": last.isoformat(),
                    "debounce_window_seconds": debounce_seconds,
                    "financial_year": resolved_fy,
                }
                await db.commit()
                return {
                    "status": "ok",
                    "skipped": True,
                    "skip_reason": "debounce_window",
                    "financial_year": resolved_fy,
                    "previous_reconciled_at": last.isoformat(),
                    "debounce_window_seconds": debounce_seconds,
                    "reconcile_failures": int((workspace.evidence_reconcile_meta or {}).get("reconcile_failures", 0)),
                }

        workspace.evidence_reconcile_status = "running"
        workspace.evidence_reconcile_meta = {
            **(workspace.evidence_reconcile_meta or {}),
            "last_trigger_source": trigger_source,
            "last_started_at": datetime.now(timezone.utc).isoformat(),
            "financial_year": resolved_fy,
            "skipped": False,
        }
        await db.commit()

        started = perf_counter()
        try:
            before_obligations = await self._count_obligations(workspace_id, resolved_fy, db)
            before_matches = await self._count_matches(workspace_id, db)

            obligations = await reconcile_evidence_obligations(workspace_id, resolved_fy, db)

            after_obligations = await self._count_obligations(workspace_id, resolved_fy, db)
            after_matches = await self._count_matches(workspace_id, db)
            duration_ms = int((perf_counter() - started) * 1000)

            workspace.evidence_reconciled_at = datetime.now(timezone.utc)
            workspace.evidence_reconcile_status = "succeeded"
            workspace.evidence_reconcile_meta = {
                **(workspace.evidence_reconcile_meta or {}),
                "last_trigger_source": trigger_source,
                "financial_year": resolved_fy,
                "reconcile_duration_ms": duration_ms,
                "obligations_created": max(0, after_obligations - before_obligations),
                "matches_created": max(0, after_matches - before_matches),
                "reconcile_failures": int((workspace.evidence_reconcile_meta or {}).get("reconcile_failures", 0)),
                "last_completed_at": datetime.now(timezone.utc).isoformat(),
                "skipped": False,
            }
            await db.commit()
            return {
                "status": "ok",
                "skipped": False,
                "obligations_count": len(obligations),
                "financial_year": resolved_fy,
                "reconcile_duration_ms": duration_ms,
                "obligations_created": max(0, after_obligations - before_obligations),
                "matches_created": max(0, after_matches - before_matches),
                "reconcile_failures": int((workspace.evidence_reconcile_meta or {}).get("reconcile_failures", 0)),
            }
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            workspace.evidence_reconcile_status = "failed"
            workspace.evidence_reconcile_meta = {
                **(workspace.evidence_reconcile_meta or {}),
                "last_trigger_source": trigger_source,
                "financial_year": resolved_fy,
                "reconcile_duration_ms": duration_ms,
                "last_error": str(exc),
                "reconcile_failures": int((workspace.evidence_reconcile_meta or {}).get("reconcile_failures", 0)) + 1,
                "last_failed_at": datetime.now(timezone.utc).isoformat(),
                "skipped": False,
            }
            await db.commit()
            logger.exception(
                "Evidence reconcile failed (workspace_id=%s, financial_year=%s, source=%s)",
                workspace_id,
                resolved_fy,
                trigger_source,
            )
            if raise_on_error:
                raise
            return {
                "status": "failed",
                "financial_year": resolved_fy,
                "reconcile_duration_ms": duration_ms,
                "reconcile_failures": int((workspace.evidence_reconcile_meta or {}).get("reconcile_failures", 0)),
            }

    async def _resolve_financial_year(self, workspace_id: str, db: AsyncSession, workspace: Workspace) -> str | None:
        profile = await db.scalar(select(TaxProfile).where(TaxProfile.workspace_id == workspace_id))
        if profile:
            return profile.financial_year
        return workspace.financial_year

    async def _count_obligations(self, workspace_id: str, financial_year: str, db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(EvidenceObligation.id)).where(
                EvidenceObligation.workspace_id == workspace_id,
                EvidenceObligation.financial_year == financial_year,
            )
        )
        return int(result.scalar_one() or 0)

    async def _count_matches(self, workspace_id: str, db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(EvidenceMatch.id)).where(EvidenceMatch.workspace_id == workspace_id)
        )
        return int(result.scalar_one() or 0)
