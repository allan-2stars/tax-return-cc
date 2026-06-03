# Evidence Freshness Acceptance Audit

Milestone: 13B-3D  
Goal: determine whether Evidence Freshness Trust is complete enough to satisfy Beta Blocker #3.

Inputs reviewed:

- `docs/EVIDENCE_FRESHNESS_AUDIT.md`
- `backend/app/services/evidence_freshness.py`
- `backend/app/api/routes/evidence.py`
- `backend/app/api/routes/readiness.py`
- `backend/app/api/routes/export.py`
- `frontend/components/shared/EvidenceFreshnessBadge.tsx`
- `frontend/app/(dashboard)/readiness/checklist/page.tsx`
- `frontend/app/(dashboard)/readiness/page.tsx`
- `frontend/app/(dashboard)/export/page.tsx`
- backend freshness tests
- frontend freshness tests

## Executive Summary

Evidence Freshness Trust is complete enough for invite-only Beta.

The platform now has a deterministic backend freshness model and visible frontend freshness states on the three user trust surfaces:

- Evidence Checklist
- Readiness
- Export Evidence Preview

Users can now see whether evidence status is current, being refreshed, stale, or failed. They can manually refresh the checklist and receive in-progress, success, and failure feedback. Export remains unchanged as a soft-warning workflow; stale/failed evidence freshness warns the user but does not block export.

Decision:

- Beta Blocker #3: Resolved for MVP Beta
- Residual risk: Medium
- Recommended next step: improve automatic freshness detection and background refresh after Beta stabilization

## 1. Freshness States

## Fresh

Implemented: Yes

Evidence:

- Backend maps `evidence_reconcile_status == "succeeded"` plus `evidence_reconciled_at` to `fresh`.
- Frontend badge renders `Fresh`.
- Tests cover fresh state in backend service and Evidence Checklist UI.

User impact:

- Users can see when evidence status is current.
- Evidence counts on checklist/readiness/export preview are easier to trust.

Remaining gap:

- Fresh does not yet include an age threshold or input-change detector.

Beta risk: Low

## Reconciling

Implemented: Yes

Evidence:

- Backend maps `running` to `reconciling`.
- Evidence Checklist refresh button renders `Reconciling...` while manual reconcile is pending.
- Tests cover backend reconciling state and checklist pending feedback.

User impact:

- Users no longer see a static checklist while the system is actively checking evidence.

Remaining gap:

- Readiness and Export pages show backend-reported reconciling state if returned, but they do not initiate their own reconcile action.

Beta risk: Low

## Stale

Implemented: Yes

Evidence:

- Backend maps missing/idle/no successful reconcile state to `stale`.
- Frontend badge renders `Stale`.
- Readiness shows: `Evidence status may not be current.`
- Export shows: `Export preview may be using stale evidence status.`
- Tests cover stale display on Checklist, Readiness, and Export.

User impact:

- Users can tell when evidence information may not reflect the latest workspace state.

Remaining gap:

- There is no age-based staleness rule yet.
- There is no explicit “inputs changed since last reconcile” detector yet.

Beta risk: Medium

## Failed

Implemented: Yes

Evidence:

- Backend maps `failed` to `failed`.
- Backend gives safe freshness reason text.
- Frontend badge renders `Failed`.
- Evidence Checklist manual refresh failure shows retryable feedback.
- Readiness and Export show caution copy for failed freshness.
- Tests cover backend failed state and frontend failed display.

User impact:

- Users can tell when evidence status could not be refreshed instead of assuming the checklist is authoritative.

Remaining gap:

- Failure reason is intentionally generic.
- No structured user-safe failure code is exposed yet.

Beta risk: Medium

## 2. API Coverage

## Evidence Obligations and Reconcile

Implemented: Yes

API coverage:

- `GET /api/v1/evidence/obligations` includes `freshness`.
- `POST /api/v1/evidence/reconcile` includes `freshness`.

Freshness payload includes:

- `freshness_state`
- `last_reconciled_at`
- `last_attempted_at`
- `last_failure_at`
- `trigger_source`
- `freshness_reason`
- backward-compatible raw fields:
  - `evidence_reconciled_at`
  - `evidence_reconcile_status`
  - `evidence_reconcile_meta`

Tests:

- `backend/tests/http/test_http_evidence.py`
- `backend/tests/test_evidence_reconcile_service.py`

Beta risk: Low

## Readiness

Implemented: Yes

API coverage:

- `GET /api/v1/readiness` includes `evidence_freshness`.
- Legacy readiness fields remain present.
- Readiness 2.0 scoring is unchanged.

Tests:

- `backend/tests/http/test_http_readiness.py`
- `frontend/__tests__/readiness-page.test.tsx`

Beta risk: Low

## Export Eligibility

Implemented: Yes

API coverage:

- `GET /api/v1/export/eligibility` includes `evidence_freshness`.
- Existing export eligibility fields remain present.
- Export gating is unchanged.

Tests:

- `backend/tests/http/test_http_export.py`
- `frontend/__tests__/export-page.test.tsx`

Beta risk: Low

## 3. UI Coverage

## Evidence Checklist

Implemented: Yes

User-visible behavior:

- Shows Fresh / Reconciling / Stale / Failed badge.
- Shows last reconciled, last attempted, and last failed timestamps when available.
- Keeps existing checklist content visible.
- Manual refresh shows:
  - `Reconciling...`
  - `Checklist refreshed.`
  - `Unable to refresh evidence checklist. Try again.`

Tests:

- `frontend/__tests__/evidence-checklist-page.test.tsx`

Beta risk: Low

## Readiness Page

Implemented: Yes

User-visible behavior:

- Evidence readiness card shows freshness badge.
- Stale/failed states show: `Evidence status may not be current.`
- Legacy readiness ring and score remain.
- Readiness 2.0 scoring is unchanged.

Tests:

- `frontend/__tests__/readiness-page.test.tsx`

Beta risk: Low

## Export Page

Implemented: Yes

User-visible behavior:

- Evidence Preview section shows freshness badge.
- Stale/failed states show: `Export preview may be using stale evidence status.`
- Export button is not disabled by evidence freshness.
- Existing evidence soft-block warning remains.

Tests:

- `frontend/__tests__/export-page.test.tsx`

Beta risk: Low

## 4. User Trust Assessment

## Can user see when evidence status is current?

Yes.

Fresh state is visible on the Evidence Checklist, Readiness evidence card, and Export Evidence Preview.

## Can user see when evidence status is stale?

Yes.

Stale state is visible and is paired with caution copy on Readiness and Export.

## Can user refresh/reconcile manually?

Yes, on the Evidence Checklist.

The checklist has the safest manual reconcile action because it is the evidence-specific surface. Readiness and Export link the user back to the checklist rather than introducing duplicate reconcile controls.

## Can user understand failed reconcile?

Mostly yes.

Failed state is visible and checklist refresh failure is retryable. The message is intentionally non-technical. Users can understand that evidence status could not be refreshed, but they do not yet get detailed remediation beyond retry/checklist review.

Beta risk: Medium

## 5. Remaining Gaps

## No Auto-Reconcile From UI

Severity: Medium

Current behavior:

- Manual refresh exists on Evidence Checklist.
- Backend workflow triggers exist for core mutations.
- Readiness/Export do not automatically force reconcile from the UI.

Risk:

- Users may still need to open the checklist and refresh if they distrust a stale warning.

Recommendation:

- Post-Beta: add a controlled background refresh when Readiness or Export sees stale/failed evidence freshness, with debounce and visible progress.

## No Age-Based Staleness

Severity: Medium

Current behavior:

- Freshness is based on reconcile lifecycle status, not wall-clock age.

Risk:

- A successful reconcile from days ago can still appear fresh if no lifecycle status changed.

Recommendation:

- Add a configurable evidence freshness age policy, for example “fresh for 24 hours unless workspace inputs changed.”

## No Input-Change Staleness Detector

Severity: Medium

Current behavior:

- Backend reconcile triggers keep state fresh after known mutations, but the freshness model does not calculate max updated time across Journey, Documents, Review, Events, EvidenceMatch decisions, and restore.

Risk:

- If a trigger is missed or a mutation bypasses the service path, the UI may show Fresh even though derived evidence state should be refreshed.

Recommendation:

- Add a backend freshness detector comparing `evidence_reconciled_at` with latest relevant input update timestamp.

## No Frontend Background Polling

Severity: Low

Current behavior:

- Checklist refresh provides explicit user feedback.
- Existing React Query fetches update when pages load/refetch.

Risk:

- Long-running reconcile state may not update live on all surfaces.

Recommendation:

- Add lightweight polling only while freshness is `reconciling`.

## Generic Failure Details

Severity: Low

Current behavior:

- User-safe failed state is visible.
- Technical error details are not exposed.

Risk:

- Users may not know whether to retry, upload evidence again, or contact support.

Recommendation:

- Add safe error code categories later:
  - temporary_error
  - document_processing_pending
  - reconcile_service_error

## 6. Test Coverage Summary

## Backend Freshness Tests

Covered:

- fresh state
- stale state
- reconciling state
- failed state
- evidence obligations API includes freshness
- evidence reconcile API includes freshness
- readiness API includes freshness
- export eligibility API includes freshness
- restore-triggered reconcile updates freshness with `trigger_source = restore_apply`

Key files:

- `backend/tests/test_evidence_reconcile_service.py`
- `backend/tests/http/test_http_evidence.py`
- `backend/tests/http/test_http_readiness.py`
- `backend/tests/http/test_http_export.py`
- `backend/tests/http/test_http_recovery.py`

Latest known backend validation:

- `make test` passed during 13B-3B: 360 tests passed.

## Frontend Freshness Tests

Covered:

- Evidence Checklist renders Fresh / Reconciling / Stale / Failed.
- Evidence Checklist manual reconcile shows progress.
- Evidence Checklist manual reconcile shows success.
- Evidence Checklist manual reconcile shows failure.
- Readiness renders stale/failed warning.
- Export renders stale/failed warning.
- Existing evidence/review/export UI behavior remains green.

Key files:

- `frontend/__tests__/evidence-checklist-page.test.tsx`
- `frontend/__tests__/readiness-page.test.tsx`
- `frontend/__tests__/export-page.test.tsx`

Latest known frontend validation:

- `make test-fe` passed during 13B-3C: 61 suites passed, 423 tests passed.

## 7. Beta Blocker Decision

Decision: Yes, Beta Blocker #3 is resolved for MVP Beta.

Rationale:

- The system now has deterministic evidence freshness states.
- The main backend APIs expose freshness consistently.
- The main user trust surfaces render freshness consistently.
- Users can refresh evidence manually from the checklist.
- Stale/failed evidence status is visible before readiness/export decisions.
- Export remains allowed, which matches the current soft-block policy.

Residual risk:

- Medium, because freshness does not yet include age-based or input-change-based stale detection.

Beta condition:

- Acceptable for invite-only Beta with simple-to-moderate users.
- Beta support/docs should tell users to use the Evidence Checklist refresh if evidence status is stale or failed.

## 8. Updated Production Readiness Estimate

Previous estimate after Recovery MVP and Session Resilience MVP: approximately 86/100.

Updated estimate after Evidence Freshness Trust MVP:

- 89/100

Rationale:

- Major user trust ambiguity around Evidence Intelligence is now addressed.
- Readiness and Export no longer present evidence counts without a freshness signal.
- Remaining risk is mostly automation quality, not core user visibility.

Recommended next blocker:

- Review workflow auditability and accidental confirmation recovery.

Why:

- Recovery and session resilience now reduce data-loss risk.
- Evidence freshness now reduces trust ambiguity.
- The next highest Beta risk is users confirming or rejecting extracted tax items without enough guardrails, undo history, or audit clarity.
