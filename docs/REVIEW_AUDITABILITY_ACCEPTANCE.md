# Review Auditability Acceptance Audit

Milestone: 13B-4E  
Goal: assess whether the Review Auditability MVP is complete enough to satisfy Beta Blocker #4.

This is an audit-only document. No runtime behavior changes are included.

Inputs reviewed:

- `docs/REVIEW_AUDITABILITY_AUDIT.md`
- `backend/app/db/models.py`
- `backend/app/engines/review.py`
- `backend/app/repositories/review.py`
- `backend/app/api/routes/review.py`
- `backend/tests/test_review.py`
- `backend/tests/http/test_http_review.py`
- `frontend/components/review/BulkActionBar.tsx`
- `frontend/components/review/ReviewCard.tsx`
- `frontend/app/(dashboard)/review/page.tsx`
- `frontend/__tests__/BulkActionBar.test.tsx`
- `frontend/__tests__/ReviewCard.test.tsx`
- `frontend/__tests__/review-page.test.tsx`
- `frontend/__tests__/review-api.test.ts`

## Executive Summary

Review Auditability MVP is complete enough to resolve Beta Blocker #4 for invite-only Beta.

The platform now provides:

- explicit confirmation before bulk review confirmation
- first-class review decision history
- structured field-level change history
- user-visible review history with timestamps
- item-level undo for recent confirmation and amendment decisions
- bulk undo for recent bulk confirmations
- backend workspace scoping and conservative latest-decision-only undo rules
- `AuditLog` entries alongside `ReviewDecisionHistory`

The remaining gaps are important, but they are no longer Beta-blocking for the recommended invite-only Beta profile because they mostly concern less common or more advanced workflows: flagged/skipped undo, inline-answer undo, arbitrary historical rollback, and evidence match decision history/undo.

Decision:

- Beta Blocker #4: resolved at MVP level.
- Production readiness estimate after this milestone: 89/100.
- Recommendation: proceed to the next Beta-readiness blocker, with review auditability residuals tracked as Phase 2 hardening.

## Assessment Matrix

## 1. Bulk Confirmation Safeguards

Status: yes.

Evidence in code/tests:

- `frontend/components/review/BulkActionBar.tsx`
- `frontend/__tests__/BulkActionBar.test.tsx`
- Tests cover:
  - dialog opens before confirm
  - cancel closes without confirming
  - explicit Confirm All triggers existing bulk action
  - item count is displayed
  - item titles, amounts, dates, and total amount render
  - warning copy is shown

Remaining gap:

- The dialog does not require typed confirmation. This is acceptable for MVP because the user must explicitly review a modal with item details before confirming.

Beta risk:

- Low. The primary accidental mass-confirm risk identified in `REVIEW_AUDITABILITY_AUDIT.md` is mitigated.

## 2. Review Decision History

Status: yes.

Evidence in code/tests:

- `ReviewDecisionHistory` model in `backend/app/db/models.py`
- Migration: `backend/alembic/versions/c4d5e6f7a8b9_add_review_decision_history.py`
- History writes in `backend/app/engines/review.py`
- History reads in `backend/app/repositories/review.py`
- API sidecar and endpoint in `backend/app/api/routes/review.py`
- Tests:
  - `backend/tests/test_review.py`
  - `backend/tests/http/test_http_review.py`

Implemented actions:

- `confirmed`
- `amended`
- `flagged`
- `skipped`
- `inline_answer` when it changes review completion state
- `undo`

Remaining gap:

- History is attached to Review items, not yet exposed as a standalone workspace-wide timeline.

Beta risk:

- Low. Item-level history is sufficient for user-facing Beta recovery and traceability.

## 3. Structured Changed-Field History

Status: yes.

Evidence in code/tests:

- `ReviewDecisionHistory.changed_fields`
- `ReviewEngine._add_change`
- Tests assert structured old/new values for:
  - status
  - user_action
  - amount
  - category
  - note
  - questions_complete

Remaining gap:

- Changed fields are structured but not schema-versioned. This is acceptable because the field set is simple and only additive.

Beta risk:

- Low.

## 4. User-Visible Timestamps and History

Status: yes.

Evidence in code/tests:

- `ReviewCard` renders expandable `Review history`.
- History entries show action, timestamp, changed fields, note, and bulk marker.
- Tests:
  - `frontend/__tests__/ReviewCard.test.tsx`

Remaining gap:

- Timestamp formatting is compact and card-level only. There is no dedicated history drawer or global timeline.

Beta risk:

- Low. Card-level history is enough for users to inspect the item they are reviewing.

## 5. Undo Single Confirm

Status: yes.

Evidence in code/tests:

- Backend:
  - `ReviewEngine.undo_latest_decision`
  - `POST /api/v1/review/{item_id}/undo`
  - `backend/tests/test_review.py::test_undo_confirmed_restores_previous_status`
  - `backend/tests/http/test_http_review.py::test_undo_confirmed_action_restores_review_item`
- Frontend:
  - `undoReviewDecision`
  - `ReviewCard` Undo last decision action
  - `ReviewPage` mutation/refetch success/error handling

Behavior:

- Restores prior `ReviewItem.status`.
- Restores prior `ReviewItem.user_action`.
- Restores linked `TaxEvent.status` and `TaxEvent.review_status`.
- Writes `ReviewDecisionHistory(action="undo")`.
- Writes `AuditLog(action="undo")`.

Remaining gap:

- Only the latest undoable decision can be undone.

Beta risk:

- Low. Latest-only is the correct conservative MVP rule.

## 6. Undo Amend

Status: yes.

Evidence in code/tests:

- `backend/tests/test_review.py::test_undo_amended_restores_previous_amount_category_and_note`
- `ReviewEngine._undo_history_entry`

Behavior:

- Restores status.
- Clears/restores `user_action`.
- Restores visible amount/category back to prior values.
- Restores note.
- Restores linked `TaxEvent.status` and `TaxEvent.review_status`.
- Writes undo history and audit log.

Remaining gap:

- TaxEvent `correction_history` remains append-only and is not compacted when an amendment is undone. This is acceptable because it preserves an audit trail.

Beta risk:

- Low.

## 7. Undo Bulk Confirm

Status: yes.

Evidence in code/tests:

- Backend:
  - `ReviewEngine.undo_bulk_decision`
  - `POST /api/v1/review/bulk-action/{bulk_action_id}/undo`
  - `backend/tests/test_review.py::test_bulk_undo_restores_grouped_confirmations`
  - `backend/tests/http/test_http_review.py::test_bulk_undo_restores_items`
- Frontend:
  - `undoBulkReviewDecision`
  - `ReviewCard` dispatches bulk undo when latest history has `bulk_action_id`.
  - `frontend/__tests__/ReviewCard.test.tsx`
  - `frontend/__tests__/review-page.test.tsx`

Behavior:

- Uses the shared `bulk_action_id` from the original bulk confirmation.
- Prevalidates all grouped items before mutating.
- Refuses bulk undo if any item has a newer decision.
- Writes one undo history row per restored item.

Remaining gap:

- No dedicated bulk undo banner/list view. The affordance appears from each affected card's review history.

Beta risk:

- Low.

## 8. AuditLog Integration

Status: yes.

Evidence in code/tests:

- `ReviewEngine.process_action` writes audit logs for:
  - confirmed
  - amended
  - flagged
  - skipped
  - inline_answer
- `ReviewEngine._undo_history_entry` writes `AuditLog(action="undo")`.
- Existing review tests assert confirm/amend audit logging.

Remaining gap:

- AuditLog is not user-visible. User-facing visibility is provided through `ReviewDecisionHistory`.
- Evidence match decisions do not yet write equivalent review decision history.

Beta risk:

- Medium for evidence matching, low for Review item decisions.

## Remaining Unsupported Cases

## Flagged

Status: partial.

Current behavior:

- `flagged` writes `ReviewDecisionHistory`.
- `flagged` writes `AuditLog`.
- Undo is intentionally not supported yet because `flagged` maps to `needs_agent_review`, and product semantics around reversing that decision need more explicit UX.

Remaining gap:

- No user-facing undo for `flagged`.

Beta risk:

- Medium. The Review UI does not currently make flagged a primary user decision, so this is not a Beta blocker for the current UI.

## Skipped

Status: partial.

Current behavior:

- `skipped` writes `ReviewDecisionHistory`.
- `skipped` writes `AuditLog`.
- Undo is not supported yet.

Remaining gap:

- No direct undo for skipped review decisions.

Beta risk:

- Low to medium. This should be addressed before broader Beta if skip becomes a prominent review action.

## Inline Answer

Status: partial.

Current behavior:

- Inline answer writes `AuditLog`.
- If inline answers complete a review item, `ReviewDecisionHistory(action="inline_answer")` is recorded.
- Undo is not supported.

Remaining gap:

- No rollback of inline answers stored in InterviewSession answers.

Beta risk:

- Medium. This is more complex because inline answer state is shared with the interview/session answer model.

## Arbitrary Older-History Undo

Status: no.

Current behavior:

- Only latest undoable decisions are supported.
- Attempts to undo when the latest action is unsupported return a clear error.

Remaining gap:

- No arbitrary timeline rollback.

Beta risk:

- Low. Latest-only is intentionally conservative and avoids state-machine ambiguity.

## Evidence Match Decision Undo/History

Status: partial.

Current behavior:

- Evidence match accept/reject decisions are persisted.
- Evidence reconcile preserves accepted/rejected decisions.
- Evidence Checklist shows accepted/rejected/candidate states.

Remaining gap:

- No `EvidenceDecisionHistory`.
- No user-visible evidence match decision timeline.
- No evidence match undo action.

Beta risk:

- Medium. This is the most important remaining auditability gap, but it belongs to Evidence Checklist hardening rather than Review item auditability.

## Test Coverage Summary

Backend coverage:

- `backend/tests/test_review.py`
  - confirm writes decision history
  - amend writes structured changed fields
  - flag writes history
  - skip writes history
  - bulk confirm writes shared `bulk_action_id`
  - undo confirm restores prior state
  - undo amend restores prior values
  - non-latest/unsupported undo is rejected
  - bulk undo restores grouped confirmations
- `backend/tests/http/test_http_review.py`
  - review action responses include `decision_history`
  - history endpoint is workspace scoped
  - item undo endpoint works
  - item undo is workspace scoped
  - bulk undo endpoint works

Frontend coverage:

- `frontend/__tests__/BulkActionBar.test.tsx`
  - confirmation modal behavior
  - cancel path
  - explicit confirm path
  - item preview and totals
- `frontend/__tests__/ReviewCard.test.tsx`
  - history empty state
  - structured changed-field rendering
  - bulk action marker
  - undo button
  - bulk undo callback selection
- `frontend/__tests__/review-page.test.tsx`
  - review mutation error handling
  - undo mutation success/error handling
  - bulk undo mutation success handling
- `frontend/__tests__/review-api.test.ts`
  - item undo API client
  - bulk undo API client

Last known validation before this audit:

- `make test`: 368 passed
- `make test-fe`: 61 suites passed, 436 tests passed

No tests were rerun for this documentation-only acceptance audit.

## Beta Blocker #4 Decision

Beta Blocker #4 is resolved at MVP level.

Rationale:

- The highest-risk Review workflow problem was accidental confirmation, especially bulk confirmation.
- Bulk confirmation now requires explicit confirmation with item details.
- Users can inspect what changed, when, and in which bulk action.
- Users can undo accidental single confirmations, amendments, and bulk confirmations when they are still the latest decision.
- Backend rules are conservative and workspace scoped.
- Audit logs remain available for developer/operator investigation.

This is sufficient for invite-only Beta users handling simple to moderately complex PAYG/investment workflows.

## Updated Production Readiness Estimate

Previous product hardening baseline: 78/100.

After completed MVP blockers:

- Recovery MVP: critical recovery blocker resolved.
- Session Resilience MVP: long-session loss risk materially reduced.
- Evidence Freshness Trust: users can see evidence freshness state.
- Review Auditability MVP: accidental review decision risk materially reduced.

Updated estimate: 89/100.

Rationale:

- Core user data recovery and review recovery risks are now addressed.
- Remaining gaps are more about breadth, edge cases, mobile polish, and advanced auditability rather than core safety.

## Recommended Next Step

Recommended next blocker/beta-readiness step:

1. Evidence Match Decision Auditability
   - Add evidence match decision history.
   - Show who accepted/rejected a match and when.
   - Add latest evidence match undo if safe.

2. Beta Dry-Run Scenario Pack
   - Run seeded end-to-end user scenarios:
     - simple PAYG
     - PAYG + WFH
     - PAYG + bank interest
     - PAYG + donations/work expenses
     - PAYG + small investment/crypto sample
   - Confirm Journey, Evidence, Review, Readiness, and Export outputs remain coherent.

3. Mobile/Tablet Review Pass
   - Verify Review history, Evidence Checklist, and Export flow on iPad-sized viewports.

Final recommendation:

- Proceed toward invite-only Beta after a Beta Dry-Run Scenario Pack.
- Do not broaden beyond invite-only Beta until evidence match auditability and mobile/tablet review are complete.
