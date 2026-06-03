# Review Auditability Audit

Milestone: 13B-4A  
Goal: determine whether users can safely understand, trace, and recover from Review decisions.

This is an audit-only document. No runtime behavior changes are included.

Inputs reviewed:

- `backend/app/db/models.py`
- `backend/app/api/routes/review.py`
- `backend/app/api/routes/events.py`
- `backend/app/api/routes/evidence.py`
- `backend/app/engines/review.py`
- `backend/app/repositories/audit.py`
- `frontend/app/(dashboard)/review/page.tsx`
- `frontend/components/review/ReviewCard.tsx`
- `frontend/components/review/BulkActionBar.tsx`
- `frontend/components/review/AmendForm.tsx`
- `frontend/components/readiness/EvidenceChecklist.tsx`
- `docs/PRODUCT_HARDENING_AUDIT.md`
- `docs/BETA_BLOCKERS.md`

## Executive Summary

Review auditability is partially implemented but not yet strong enough to close the next Beta risk.

The backend records some audit events and preserves some amended amount history. The frontend provides explanation sidecars, confidence indicators, and clear review actions. However, user-facing recovery is weak: users cannot inspect a decision timeline, undo a confirmation/rejection-style action, or compare previous and current values after edits.

Main finding:

- The system is auditable enough for developer/database investigation.
- It is not yet auditable enough for normal users to understand and recover from review decisions without support.

Beta decision:

- Beta Blocker #4 status: partially unresolved.
- Recommended: implement Review Auditability MVP before broader Beta.
- Invite-only Beta can proceed only with narrow user cohort and support caveat if this is deferred.

## 1. Review Workflow Map

## Review Queue

Backend:

- `GET /api/v1/review/queue`
- Powered by `ReviewEngine.get_queue`.
- Groups items into:
  - `agent_required`
  - `high_risk`
  - `needs_review`
  - `confirmed`

Frontend:

- `frontend/app/(dashboard)/review/page.tsx`
- Renders filter tabs:
  - All
  - Income
  - Deductions
  - Investments
  - Confirmed
- Renders `ReviewCard` for each item.

Auditability today:

- Queue response includes current item state, explanation sidecar, dates, amount/category, confidence, and status.
- It does not include prior decisions or change history.

## Confirm

Backend:

- `POST /api/v1/review/{item_id}/action` with `action = confirmed`.
- `ReviewEngine.process_action` sets:
  - `ReviewItem.status = confirmed`
  - `ReviewItem.user_action = confirmed`
  - `ReviewItem.reviewed_at`
  - `ReviewItem.review_duration_seconds`
  - linked `TaxEvent.status = confirmed`
  - linked `TaxEvent.review_status = user_confirmed`
- Writes `AuditLog(action="confirmed", actor="user")`.

Frontend:

- `ReviewCard` button: `Looks right`.
- After click, local `confirmed` state immediately shows: `Thanks for reviewing. We've noted your input.`

Auditability risk:

- Confirmation is single-click.
- No explicit “undo” or “view decision” action.
- Local UI flips to confirmed before server refetch completes.

## Reject / Flag

Current behavior:

- There is no user-facing `Reject` button on `ReviewCard`.
- Backend supports `UserAction.FLAGGED`, mapped to `needs_agent_review`.
- Frontend does not expose a primary flag action in the current `ReviewCard`; the visible alternatives are `Change this` and `Ask Claude`.

Auditability risk:

- Product language and backend semantics are not fully aligned:
  - backend supports `flagged`
  - Review UI does not expose it as a first-class decision
  - Readiness/export may still treat `needs_agent_review` as warning/blocking depending context

## Inline Edit / Amend

Backend:

- `action = amended`.
- Stores:
  - `ReviewItem.amended_amount`
  - `ReviewItem.amended_category`
  - `ReviewItem.user_note`
  - `ReviewItem.status = confirmed`
  - `ReviewItem.user_action = amended`
  - `TaxEvent.correction_history` entry for amount changes only
  - `AuditLog(action="amended", field="amount", old_value, new_value, note)`

Frontend:

- `ReviewCard` -> `Change this` -> `AmendForm`.
- User can edit:
  - amount
  - category
  - note

Auditability risk:

- Amount history is stored on `TaxEvent.correction_history`.
- Category changes are not fully captured in correction history.
- UI does not show previous value after save.
- UI does not show who/when/why an amendment was made.

## Bulk Actions

Backend:

- `POST /api/v1/review/bulk-action`.
- Currently only supports `confirmed`.
- Calls `process_action` for each item.
- Writes one `AuditLog(action="confirmed")` per item.

Frontend:

- `BulkActionBar` displays grouped items sharing the same description.
- Button: `Confirm all`.

Auditability risk:

- Bulk confirm is one click.
- No confirmation dialog.
- No preview of exact items being confirmed beyond count/group label.
- No undo bulk action.
- Backend audit logs individual item confirmations but does not record a bulk action group id.

## Ask AI

Backend:

- `POST /api/v1/review/{item_id}/ask`.
- `ReviewEngine.ask_claude` returns adapter answer or fallback disclaimer.
- AI adapter has audit logging for AI calls in repository code, but route-level review question context is not exposed as a user-facing decision timeline.

Frontend:

- `ReviewCard` opens `AskClaudeDrawer`.
- Explanation sidecars are deterministic and separate from Ask AI.

Auditability risk:

- User cannot later see what they asked or what answer influenced a review decision.
- No “this decision followed AI answer” linkage.

## Manual Entry

Backend:

- `POST /api/v1/events/manual`.
- Validates tax-specific metadata for several categories.
- Creates `TaxEvent` and associated `ReviewItem`.
- Triggers evidence reconcile.

Frontend:

- `Review -> Add item manually`.
- Uses manual-entry wizard and tax-specific subforms for several categories.

Auditability risk:

- Manual entries are marked by `TaxEvent.source = manual_entry`.
- There is no visible manual-entry history/timeline beyond the resulting review item.
- Edits after manual entry use the same amend path and inherit its limitations.

## Evidence Match Decisions

Backend:

- `PATCH /api/v1/evidence/matches/{match_id}` accepts:
  - `accepted`
  - `rejected`
- Updates `EvidenceMatch.status`.
- Recalculates parent `EvidenceObligation.status`.
- Reconcile preserves accepted/rejected decisions.

Frontend:

- Evidence Checklist shows:
  - `Accept match`
  - `Reject match`
  - `Matched by`
  - `Rejected match`

Auditability risk:

- Accepted/rejected status is persisted.
- There is no explicit actor, decision timestamp, previous status, or visible decision history.
- Mistaken evidence decisions require another action if a candidate remains visible; there is no clear undo/history affordance.

## 2. Existing Auditability

## Audit Logs

Implemented:

- `AuditLog` model exists with:
  - `workspace_id`
  - `tax_event_id`
  - `action`
  - `actor`
  - `field`
  - `old_value`
  - `new_value`
  - `note`
  - AI metadata fields
  - `created_at`
- Review engine writes audit logs for:
  - confirmed
  - amended
  - flagged
  - skipped
  - inline_answer
- Bulk confirm writes one confirm log per item.

Weakness:

- No public review audit API.
- No user-facing timeline component.
- No bulk action correlation id.
- Evidence match decisions do not appear to write `AuditLog` rows.

## Timestamps

Implemented:

- `ReviewItem.created_at`
- `ReviewItem.reviewed_at`
- `ReviewItem.skipped_until`
- `TaxEvent.created_at`
- `EvidenceMatch.created_at`
- `EvidenceMatch.updated_at`
- `AuditLog.created_at`

Weakness:

- Review UI shows item date but not review decision timestamp.
- Evidence UI shows match status but not decision timestamp.

## Actor Attribution

Implemented:

- `AuditLog.actor` supports values such as `user`, `ai`, `system`.
- Review actions write `actor="user"`.

Weakness:

- Actor attribution is not exposed in Review UI.
- There is no distinction between current user identities if multi-user is later introduced.

## Previous Value Retention

Implemented:

- `TaxEvent.correction_history` stores amount corrections.
- `AuditLog.old_value` / `new_value` stores amended amount.
- `ReviewItem.amended_amount` and `ReviewItem.amended_category` preserve effective changes separately from original item fields.

Weakness:

- Category changes are not fully recorded in `correction_history`.
- Confirm/flag/skip transitions do not store old status/new status as structured fields.
- Evidence match accepted/rejected transitions do not preserve previous status in a visible timeline.

## Evidence Match Decisions

Implemented:

- `EvidenceMatch.status` records candidate/accepted/rejected.
- Reconcile preserves accepted/rejected decisions.
- UI labels candidate, accepted, and rejected states.

Weakness:

- No decision actor field.
- No decision timestamp distinct from generic `updated_at`.
- No reason/note from user on rejection.
- No timeline or undo.

## 3. User Risks

## Accidental Confirm

Severity: High

Scenario:

- User taps `Looks right` on the wrong item, especially on tablet/mobile.
- Item moves to confirmed state and export/estimate now treats it as reviewed.

Current behavior:

- Single-click confirmation.
- No confirm dialog.
- No undo.
- Audit log exists but not surfaced to user.

Recommended fix:

- Add immediate undo affordance after confirm.
- Add decision timeline showing confirmed by user with timestamp.

Beta requirement:

- Must Fix Before Beta for broad Beta.

## Accidental Reject / Agent Flag

Severity: Medium

Scenario:

- User marks an item as needing agent review or rejects an evidence match accidentally.

Current behavior:

- Review flag path exists in backend but is not a visible first-class ReviewCard action.
- Evidence match rejection is visible but has no undo/timeline.

Recommended fix:

- Add evidence decision history and undo/reconsider action.
- Align review flag/reject terminology in product UI.

Beta requirement:

- Recommended Before Beta.

## Accidental Bulk Action

Severity: High

Scenario:

- User clicks `Confirm all` for grouped items that share a description, but one item in the group is wrong.

Current behavior:

- One-click bulk confirm.
- No item preview modal.
- No bulk action group id in audit logs.
- No undo.

Recommended fix:

- Add bulk confirmation dialog listing affected items and totals.
- Add bulk action id to audit trail.
- Add undo bulk action while still in current session if feasible.

Beta requirement:

- Must Fix Before Beta.

## Accidental Edit

Severity: Medium

Scenario:

- User changes amount/category and later cannot remember original extracted value.

Current behavior:

- Amount previous value is captured in audit/correction history.
- Category previous value is not captured equivalently.
- UI does not show previous value after save.

Recommended fix:

- Capture all amended fields in a structured review decision history.
- Show “Changed from X to Y” in ReviewCard details.

Beta requirement:

- Must Fix Before Beta for amount/category edits.

## Evidence Match Mistakes

Severity: Medium

Scenario:

- User accepts the wrong receipt as evidence for an obligation.

Current behavior:

- Match status changes to accepted.
- Parent obligation may become matched.
- Reconcile preserves accepted decisions.
- No visible decision history or undo.

Recommended fix:

- Add evidence match decision history.
- Add `Undo decision` / `Change decision` for accepted/rejected matches.

Beta requirement:

- Recommended Before Beta.

## No Recovery Path

Severity: High

Scenario:

- User confirms several items, later realizes the wrong document or amount was used.

Current behavior:

- Recovery MVP can restore workspace backups, but Review workflow does not have local decision recovery.
- User must manually amend or rely on support/database inspection.

Recommended fix:

- Add review decision history and undo for recent actions.
- Preserve previous status/value snapshots.

Beta requirement:

- Must Fix Before Beta for confirmation and bulk confirmation.

## 4. Visibility Gaps

## What Changed?

Current:

- Current status and amended values are visible.
- Some original values remain implicitly present.

Gap:

- UI does not show a concise “changed from -> to” summary.
- Bulk confirmations do not show grouped decision metadata.

## Who Changed It?

Current:

- `AuditLog.actor` exists.

Gap:

- UI does not show actor.
- Future multi-user identity is not modeled.

## When Changed?

Current:

- `reviewed_at`, `AuditLog.created_at`, and `updated_at` fields exist.

Gap:

- Review UI does not show decision timestamp.
- Evidence UI does not show match decision timestamp.

## Previous Value?

Current:

- Amount amendment history is stored.

Gap:

- Category/status/match decision previous values are not consistently stored or exposed.

## Why Changed?

Current:

- Amend notes can be stored.
- AuditLog note can store some values.

Gap:

- Confirm and bulk confirm have no rationale.
- Evidence match rejection has no optional reason.
- Ask AI influence is not linked to later decisions.

## 5. Recommended MVP Improvements

## A. Review Decision History

Priority: Must Fix Before Beta

Scope:

- Add first-class decision history for ReviewItem changes.
- Minimum fields:
  - `id`
  - `workspace_id`
  - `review_item_id`
  - `tax_event_id`
  - `action`
  - `actor`
  - `previous_status`
  - `new_status`
  - `changed_fields`
  - `note`
  - `created_at`
  - optional `bulk_action_id`

Why:

- Gives users and support a reliable timeline without parsing generic audit logs.

Implementation effort: Medium

## B. ReviewCard Change Timeline

Priority: Must Fix Before Beta

Scope:

- Add compact expandable “Review history” section to ReviewCard.
- Show:
  - confirmed/amended/skipped/flagged decisions
  - timestamp
  - changed fields
  - note if present

Why:

- Users can answer “what changed, when, and why?” without leaving Review.

Implementation effort: Medium

## C. Undo Recent Review Decision

Priority: Must Fix Before Beta

Scope:

- Add undo for:
  - confirm
  - amend
  - bulk confirm
- Undo should restore previous item/event status and amended fields.
- Keep undo itself audited.

Why:

- Reduces the highest user-risk action: accidental confirmation.

Implementation effort: Medium

## D. Bulk Action Confirmation

Priority: Must Fix Before Beta

Scope:

- Before `Confirm all`, show modal/dialog listing:
  - count
  - item titles
  - amounts
  - dates
  - total amount if sensible
- Require explicit confirmation.

Why:

- Bulk confirm currently has the largest mistake blast radius.

Implementation effort: Small

## E. Evidence Decision History

Priority: Recommended Before Beta

Scope:

- Add actor/timestamp/reason for EvidenceMatch status decisions.
- Add visible history under matched/rejected match rows.
- Add change/undo decision action if feasible.

Why:

- Evidence decisions can change readiness/export evidence posture.

Implementation effort: Medium

## F. Ask AI Traceability

Priority: Nice To Have Before Beta

Scope:

- Store review item ask/answer interactions as audit timeline entries.
- Show that an answer was advisory/helpful context, not final advice.

Why:

- Useful for support and user trust, but less critical than confirm/undo.

Implementation effort: Medium

## 6. Beta Assessment

## Must Fix Before Beta

1. Bulk action confirmation dialog.
2. Undo recent single-item confirm.
3. Undo recent bulk confirm or equivalent “move confirmed items back to review” action.
4. Structured amendment history for all changed fields, not amount only.
5. User-visible review decision timestamp/history.

## Nice To Have Before Beta

1. Evidence match decision history.
2. Evidence match undo/change decision.
3. Review ask/answer audit display.
4. Review timeline filters in Settings/Admin.
5. Optional confirm note for high-value items.

## Post-Beta

1. Unified cross-workspace audit timeline combining Journey, Review, Evidence, Readiness, Recovery, and Export.
2. Multi-user actor identity model.
3. Signed immutable audit event stream.
4. Accountant-facing review decision audit artifact in export package.

## 7. Production Readiness Impact

Current estimate after Evidence Freshness Trust MVP: 89/100.

Review Auditability current state:

- Backend traceability: moderate
- User-facing auditability: weak to moderate
- Recovery from review mistakes: weak

Estimated readiness if Review Auditability MVP is implemented:

- 91/100 to 92/100

Rationale:

- Recovery, session resilience, and evidence freshness have reduced platform-level risk.
- The remaining risk is user decision safety.
- Undo/history/bulk confirmation would materially reduce Beta support burden and accidental tax-fact confirmation risk.

## 8. Final Recommendation

Recommendation: implement Review Auditability MVP before broader Beta.

Minimum acceptable MVP:

1. Bulk confirmation dialog.
2. Undo recent confirm/bulk confirm.
3. Review decision history/timeline visible on each card.
4. Structured changed-field history for amount/category/status.

Invite-only Beta can proceed without the full version only if:

- cohort is small,
- users are explicitly told Review decisions can be corrected manually,
- support has access to backend audit logs,
- bulk confirm is disabled or guarded.

