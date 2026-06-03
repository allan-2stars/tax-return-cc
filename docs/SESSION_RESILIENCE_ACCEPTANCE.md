# Session Resilience Acceptance Audit

Milestone: 13B-2F  
Goal: assess whether Session Resilience is complete enough to satisfy Beta Blocker #2 from `BETA_BLOCKERS.md`.

Inputs reviewed:

- `docs/SESSION_RESILIENCE_AUDIT.md`
- `docs/BETA_BLOCKERS.md`
- `frontend/app/(dashboard)/layout.tsx`
- `frontend/lib/api/errors.ts`
- `frontend/components/review/ManualEntryForm.tsx`
- `frontend/components/review/DraftStatus.tsx`
- `frontend/lib/hooks/useSessionDraft.ts`
- `frontend/components/review/investment/*Form.tsx`
- `frontend/components/evidence/UploadZone.tsx`
- Related frontend tests under `frontend/__tests__/`

## Executive Summary

Session Resilience is complete enough for invite-only Beta at MVP level.

Beta Blocker #2 was:

> Session resilience gaps for long-running tax prep sessions.

The highest-risk user flows now have explicit recovery UX:

- dashboard session-restored banner after a successful auth/session reload
- normalized mutation error handling for session expiry, unlock expiry, network failures, and validation errors
- manual-entry draft protection
- investment subform draft protection
- upload interruption, polling fallback, terminal failure, and long-processing guidance

Residual risks remain because this is not a full offline/resumable architecture. The remaining gaps are acceptable for targeted invite-only Beta if the Beta scope excludes offline-first workflows and sets expectations around browser/session limits.

## Acceptance Matrix

## 1. Session Restored UX

- **Implemented:** Yes
- **Evidence in code/tests:**
  - `frontend/app/(dashboard)/layout.tsx` renders: “Session restored. Your workspace data is up to date.”
  - `frontend/__tests__/dashboard-layout.test.tsx` covers restored banner behavior.
- **Remaining gap:**
  - No cross-tab session restoration event.
  - No timestamp in the banner.
  - No sliding session extension flow.
- **Beta risk:** Low

The app now gives users a clear confidence signal after page load/refresh when session state is successfully restored.

## 2. Mutation Error Handling

- **Implemented:** Yes
- **Evidence in code/tests:**
  - `frontend/lib/api/errors.ts` centralizes error normalization.
  - `frontend/app/(dashboard)/journey/page.tsx` uses normalized mutation errors.
  - `frontend/app/(dashboard)/review/page.tsx` and `frontend/app/(dashboard)/readiness/checklist/page.tsx` show retryable/actionable errors.
  - `frontend/__tests__/journey-page.test.tsx`, `frontend/__tests__/review-page.test.tsx`, and `frontend/__tests__/evidence-checklist-page.test.tsx` cover failed mutation UX.
- **Remaining gap:**
  - Not every possible mutation in the product has a sophisticated retry workflow.
  - There is no global mutation retry queue.
- **Beta risk:** Low/Medium

Critical mutations now communicate failures more clearly, but retry remains page-local rather than globally orchestrated.

## 3. 401 / Session-Expired Handling

- **Implemented:** Yes
- **Evidence in code/tests:**
  - `normalizeApiError()` maps `401`, `session_expired`, `invalid_session`, and `not_authenticated` to: “Your session has expired. Sign in again, then try again.”
  - `frontend/__tests__/journey-page.test.tsx` covers Journey 401 behavior.
  - `frontend/__tests__/ManualEntryForm.test.tsx` covers manual-entry 401 behavior while preserving entered values.
  - `frontend/__tests__/UploadZone.test.tsx` covers upload 401 behavior.
- **Remaining gap:**
  - No full re-auth modal preserving an exact retry action.
  - No automatic return-to-action after login.
- **Beta risk:** Medium

Users now get clear session-expired messaging and form data is preserved where draft protection exists. A full re-auth/retry loop remains Phase 2.

## 4. Manual Entry Draft Protection

- **Implemented:** Yes
- **Evidence in code/tests:**
  - `frontend/components/review/ManualEntryForm.tsx`
  - `frontend/lib/hooks/useSessionDraft.ts`
  - `frontend/components/review/DraftStatus.tsx`
  - `frontend/__tests__/ManualEntryForm.test.tsx` covers save, restore, successful-submit clear, failed-submit preserve, discard, beforeunload, and sensitive-field exclusions.
- **Remaining gap:**
  - Drafts are stored in browser `sessionStorage`, not backend encrypted drafts.
  - Drafts are per browser session and are not portable across devices.
- **Beta risk:** Low/Medium

This resolves the main refresh/navigation loss risk for the top-level manual-entry workflow.

## 5. Investment Form Draft Protection

- **Implemented:** Yes
- **Evidence in code/tests:**
  - `frontend/components/review/investment/SharesForm.tsx`
  - `frontend/components/review/investment/CryptoForm.tsx`
  - `frontend/components/review/investment/BankInterestForm.tsx`
  - `frontend/components/review/investment/ManagedFundForm.tsx`
  - `frontend/components/review/investment/ForeignIncomeForm.tsx`
  - `frontend/__tests__/SharesForm.test.tsx`
  - `frontend/__tests__/CryptoForm.test.tsx`
  - `frontend/__tests__/BankInterestForm.test.tsx`
  - `frontend/__tests__/ManagedFundForm.test.tsx`
  - `frontend/__tests__/ForeignIncomeForm.test.tsx`
- **Remaining gap:**
  - Shares and crypto draft keys are scoped to selected transaction subtype; the parent selector state itself is not a separate persisted draft.
  - No encrypted backend storage for these drafts.
- **Beta risk:** Low

The highest-loss investment subforms now survive remount/refresh simulation and preserve data on failed submit.

## 6. Upload Interruption Handling

- **Implemented:** Yes
- **Evidence in code/tests:**
  - `frontend/components/evidence/UploadZone.tsx`
  - `frontend/__tests__/UploadZone.test.tsx`
  - Existing fallback polling through `getDocumentSummary()` remains active after SSE interruption.
  - The upload area now shows “Connection interrupted. We are checking the document status.”
- **Remaining gap:**
  - Browser refresh during the initial upload POST cannot resume the upload.
  - There is no resumable/chunked upload protocol.
  - Retry status check only works when a document ID was returned before failure.
- **Beta risk:** Medium

The UX now handles slow/ambiguous processing better, but true upload resumability is out of scope.

## 7. Long-Processing Upload Guidance

- **Implemented:** Yes
- **Evidence in code/tests:**
  - `UploadZone` shows “Still processing” after the long-processing threshold.
  - `frontend/__tests__/UploadZone.test.tsx` covers long-processing guidance.
- **Remaining gap:**
  - Threshold is frontend-only.
  - No ETA or backend processing-stage duration telemetry.
- **Beta risk:** Low

Users no longer see only an indefinite spinner for long-running extraction.

## 8. Beforeunload Protection

- **Implemented:** Yes
- **Evidence in code/tests:**
  - Shared `useSessionDraft()` attaches `beforeunload` only when draft content exists.
  - `frontend/__tests__/ManualEntryForm.test.tsx` covers dirty vs clean beforeunload behavior.
  - `frontend/__tests__/BankInterestForm.test.tsx` covers representative investment-form beforeunload behavior.
- **Remaining gap:**
  - Browser prompt text is controlled by the browser.
  - Upload-specific beforeunload protection is not separately implemented.
- **Beta risk:** Low/Medium

Critical form data loss risk is reduced. Active upload interruption is handled through status guidance rather than unload prevention.

## 9. Known Exclusions

## No Full Offline Mode

- **Implemented:** No
- **Reason:** Out of scope for Session Resilience MVP.
- **Beta risk:** Medium
- **Mitigation:** Invite-only Beta should clearly require stable internet access and avoid offline-first claims.

## No Resumable Chunk Upload

- **Implemented:** No
- **Reason:** Out of scope for Upload Interruption UX; current upload flow remains single-request.
- **Beta risk:** Medium
- **Mitigation:** Upload UI now handles failure/ambiguity with recovery guidance. Large or flaky uploads remain a known limitation.

## No Backend Encrypted Drafts

- **Implemented:** No
- **Reason:** MVP chose frontend `sessionStorage` for speed and low architecture risk.
- **Beta risk:** Medium
- **Mitigation:** Drafts store only form field values, not auth tokens, recovery keys, or document contents. Backend encrypted drafts should be Phase 2.

## Test Coverage Summary

Recent session-resilience coverage includes:

- session restored banner:
  - `frontend/__tests__/dashboard-layout.test.tsx`
- Journey 401/session-expired handling:
  - `frontend/__tests__/journey-page.test.tsx`
- manual-entry mutation error and draft protection:
  - `frontend/__tests__/ManualEntryForm.test.tsx`
- investment draft protection:
  - `frontend/__tests__/SharesForm.test.tsx`
  - `frontend/__tests__/CryptoForm.test.tsx`
  - `frontend/__tests__/BankInterestForm.test.tsx`
  - `frontend/__tests__/ManagedFundForm.test.tsx`
  - `frontend/__tests__/ForeignIncomeForm.test.tsx`
- upload interruption UX:
  - `frontend/__tests__/UploadZone.test.tsx`
- evidence decision failure UX:
  - `frontend/__tests__/evidence-checklist-page.test.tsx`
- review action failure UX:
  - `frontend/__tests__/review-page.test.tsx`

Last known frontend validation from Milestone 13B-2E:

- `make test-fe`
- 61 suites passed
- 413 tests passed

## Beta Blocker #2 Decision

**Decision: Resolved at MVP level**

Rationale:

- Users now receive an explicit session-restored signal after a successful session reload.
- Critical mutations surface clearer session/network failure messages.
- The most data-loss-prone manual-entry flows have draft save/restore/discard behavior.
- Failed submits preserve drafts.
- Uploads no longer look permanently stuck during missed SSE, slow processing, failed extraction, 401, or network failure cases.

This does not make the product fully interruption-proof. It makes the expected invite-only Beta workflow sufficiently resilient for supported users.

## Updated Production Readiness Estimate

Prior hardening audit baseline: **78/100**  
After Recovery MVP acceptance: approximately **84/100**  
After Session Resilience MVP acceptance: approximately **87/100**

Rationale:

- The two largest operational risks identified for Beta are now covered at MVP level.
- Remaining risk is concentrated in evidence freshness trust, policy/scope clarity, generic manual-entry pockets, and export handoff synthesis.

## Recommended Next Blocker To Address

Recommended next milestone: **Evidence freshness trust signal**

Why:

- It is Beta Blocker #3 in `BETA_BLOCKERS.md`.
- Evidence Intelligence, Readiness 2.0, and Export Evidence Preview already expose much of the needed backend state.
- The remaining risk is primarily user trust and clarity: users need to know whether checklist/readiness evidence state is current, stale, reconciling, or failed.

Suggested next implementation focus:

1. Prominent evidence freshness badge on Readiness and Evidence Checklist.
2. Last reconciled timestamp and reconcile status wording.
3. Clear stale/reconciling/failed states.
4. One-click refresh/reconcile feedback.
5. Tests proving stale/fresh/reconciling/failed states render correctly.

## Final Recommendation

**Beta after remaining Must-Fix blockers**

Session Resilience no longer blocks invite-only Beta by itself. The platform should continue to Beta only after the remaining Must-Fix blockers, especially evidence freshness trust, scope gating, and policy-copy consistency, are addressed.
