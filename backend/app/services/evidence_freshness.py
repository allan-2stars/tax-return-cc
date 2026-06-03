from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.db.models import Workspace

EvidenceFreshnessState = Literal["fresh", "reconciling", "stale", "failed"]


def _iso(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def build_evidence_freshness(workspace: Workspace | None) -> dict:
    if workspace is None:
        return {
            "freshness_state": "stale",
            "last_reconciled_at": None,
            "last_attempted_at": None,
            "last_failure_at": None,
            "trigger_source": None,
            "freshness_reason": "Evidence status has not been checked yet.",
            "evidence_reconciled_at": None,
            "evidence_reconcile_status": "idle",
            "evidence_reconcile_meta": None,
        }

    meta = workspace.evidence_reconcile_meta or {}
    raw_status = workspace.evidence_reconcile_status or "idle"
    status = raw_status.lower()
    last_reconciled_at = _iso(workspace.evidence_reconciled_at)
    last_started_at = _iso(meta.get("last_started_at"))
    last_completed_at = _iso(meta.get("last_completed_at"))
    last_failed_at = _iso(meta.get("last_failed_at"))
    last_attempted_at = last_started_at or last_failed_at or last_completed_at or last_reconciled_at

    if status == "running":
        state: EvidenceFreshnessState = "reconciling"
        reason = "Evidence status is being refreshed."
    elif status == "failed":
        state = "failed"
        reason = "Evidence status could not be refreshed. Existing evidence information may be out of date."
    elif status == "succeeded" and last_reconciled_at:
        state = "fresh"
        reason = "Evidence status is current."
    else:
        state = "stale"
        reason = "Evidence status has not been checked yet."

    return {
        "freshness_state": state,
        "last_reconciled_at": last_reconciled_at,
        "last_attempted_at": last_attempted_at,
        "last_failure_at": last_failed_at,
        "trigger_source": meta.get("last_trigger_source"),
        "freshness_reason": reason,
        # Backward-compatible raw fields.
        "evidence_reconciled_at": last_reconciled_at,
        "evidence_reconcile_status": raw_status,
        "evidence_reconcile_meta": meta,
    }
