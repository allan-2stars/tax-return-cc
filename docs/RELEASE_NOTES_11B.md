# Release Notes — 11B Evidence Intelligence

## 11B-1 Foundation
- Added `EvidenceObligation` and `EvidenceMatch` persistence.
- Added reconcile endpoint and obligations listing endpoint.
- Added initial deterministic obligation rules.

## 11B-2 Matching Reconciliation
- Added deterministic candidate matching for documents/tax events.
- Reconcile is idempotent and preserves manual accepted/rejected decisions.
- Obligation status derives from match state.

## 11B-3 Checklist API/UI
- Added expanded obligations API payload with match details.
- Added `/readiness/checklist` UI with category grouping and status display.

## 11B-4 Manual Decisions
- Added `PATCH /api/v1/evidence/matches/{match_id}`.
- Users can accept/reject candidates in checklist UI.
- Parent obligation status updates after decision.

## 11B-5 Readiness Dual-Run
- Readiness response now includes `evidence_obligation_summary`.
- Existing readiness score logic remains unchanged.
- Blocking evidence list includes required obligations with `missing`/`partially_matched`.

## 11B-6 Reconcile Triggers
- Added safe reconcile triggers after successful workflow mutations:
  - journey answer/skip/cancel-edit/complete
  - document finalize + archive/delete
  - manual event create + attach receipt
  - review action + bulk action

## 11B-7 Hardening
- Added lifecycle/trigger documentation in `docs/EVIDENCE_INTELLIGENCE.md`.
- Added test coverage for archive/delete behavior with manual decision preservation.
- Added explicit readiness test assertion that recommended obligations are non-blocking.
- Added checklist empty-state test.

## Out of scope (unchanged)
- Export eligibility behavior.
- Final export gating rules.
- Readiness score algorithm.
- LLM-based evidence matching.
