# Evidence Intelligence (11B)

This document describes the current additive Evidence Intelligence architecture.

## Data model

### EvidenceObligation
- Represents expected supporting evidence generated from profile/journey/tax events.
- Key lifecycle statuses:
  - `missing`
  - `partially_matched`
  - `matched`
  - `waived`
  - `not_applicable`

### EvidenceMatch
- Links obligations to candidate or manual decisions against:
  - `document`
  - `tax_event`
  - `manual`
- Match statuses:
  - `candidate`
  - `accepted`
  - `rejected`

## Reconciliation lifecycle

Main entrypoint:
- `reconcile_evidence_obligations(workspace_id, financial_year, db)`

Safe wrapper for trigger points:
- `reconcile_for_workspace_safe(workspace_id, db)`

Behavior:
1. Build expected obligations from deterministic rules.
2. Remove obligations no longer applicable.
3. Rebuild candidate matches idempotently.
4. Preserve manual decisions (`accepted` / `rejected`).
5. Recalculate obligation status from match states.

## Reconcile trigger points

Reconcile is triggered after successful mutations in:

- Journey:
  - answer
  - skip
  - cancel edit
  - complete
- Documents:
  - extraction finalize (`ready`/`failed`) in background task
  - document archive/delete
- Manual Events:
  - manual event create
  - attach receipt
- Review:
  - item action
  - bulk action

Evidence decision endpoint (`PATCH /evidence/matches/{match_id}`) recalculates the parent obligation directly and does not require a full reconcile.

## Current limitations (intentional)

- Deterministic matching only (no LLM evidence matching).
- Readiness is dual-run:
  - Existing readiness score unchanged.
  - Evidence obligation summary exposed separately.
- Export eligibility is unchanged by Evidence Intelligence in this phase.
- No manual document picker/rule authoring yet.

## Operational notes

- `reconcile_for_workspace_safe` logs failures with:
  - `workspace_id`
  - resolved `financial_year` (when available)
- Reconcile errors do not fail user mutations; they are logged for investigation.
