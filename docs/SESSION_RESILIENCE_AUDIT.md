# Session Resilience Design Audit

Milestone: 13B-2A  
Goal: audit and design the minimum session resilience improvements required for invite-only Beta.

Context:

- Recovery MVP has been accepted at MVP level.
- The next major Beta risk is interruption during long-running tax preparation sessions.
- This document is design-only. No runtime behavior changes are included.

Inputs reviewed:

- `backend/app/api/routes/auth.py`
- `backend/app/api/dependencies.py`
- `backend/app/config.py`
- `backend/app/api/routes/drafts.py`
- `frontend/lib/api/client.ts`
- `frontend/lib/api/auth.ts`
- `frontend/lib/hooks/useAuth.ts`
- `frontend/components/shared/Providers.tsx`
- `frontend/components/shared/NetworkBanner.tsx`
- `frontend/app/(dashboard)/layout.tsx`
- `frontend/app/(dashboard)/journey/page.tsx`
- `frontend/components/review/ManualEntryForm.tsx`
- `frontend/components/review/investment/*Form.tsx`
- `frontend/components/evidence/UploadZone.tsx`
- `frontend/app/(dashboard)/evidence/page.tsx`
- `frontend/app/(dashboard)/review/page.tsx`
- `frontend/app/(dashboard)/readiness/checklist/page.tsx`
- `frontend/app/(dashboard)/export/page.tsx`

## Executive Summary

Current state is recoverable after most successful server mutations because Journey answers, review actions, document uploads, evidence match decisions, and export jobs persist server-side. However, the product is still weak for interruption before submission or during session expiry:

- Long manual-entry forms hold unsaved data only in React component state.
- Session expiry is detected only when an API request fails.
- There is no global 401/session-expired handling in the API client.
- There is no user-facing “session restored” or “please sign in again, then retry” flow.
- Uploads can recover from missed SSE ready/failed events, but not from browser refresh during active upload.
- The encrypted draft backend exists but is not wired into manual-entry forms.

Minimum Beta direction:

1. Add explicit session status/restored UX.
2. Add global session-expiry handling for API calls.
3. Wire encrypted draft protection into manual-entry forms.
4. Add beforeunload protection only for dirty long forms and active uploads.
5. Improve mutation error copy and retry affordances for critical workflows.
6. Add idle/unlock warning if feasible without broad auth redesign.

## 1. Current Auth And Session Behavior

### Session Cookie

Implementation:

- `backend/app/api/routes/auth.py`
- `backend/app/api/dependencies.py`
- `settings.SESSION_MAX_AGE_DAYS`

Behavior:

- Login sets an HTTP-only `session` cookie.
- Default session max age is `1` day.
- Cookie is signed with `itsdangerous.URLSafeTimedSerializer`.
- `require_session` decodes the cookie with `SESSION_MAX_AGE_DAYS * 86400`.
- Expired cookie returns `401` with error code `session_expired`.
- Invalid cookie returns `401` with error code `invalid_session`.
- Missing cookie returns `401` with error code `not_authenticated`.
- `/api/v1/auth/session` deletes invalid cookies if the referenced workspace or security record is missing.

Beta implication:

- A taxpayer can work for a long session within one day, but a next-day tab resume will fail on the next request and redirect to login.
- There is no sliding session refresh endpoint or “extend session” behavior.

### Unlock Session

Implementation:

- `settings.UNLOCK_SESSION_MINUTES`
- `require_unlock`
- `POST /api/v1/auth/unlock`

Behavior:

- Default unlock lifetime is `30` minutes.
- Unlock is checked through both signed `unlock_session` cookie and server-side expiry/token state.
- Draft endpoints require unlock because drafts are encrypted/decrypted with the workspace DEK.
- Most workflow endpoints use `require_auth`, not `require_unlock`.

Beta implication:

- Most day-to-day workflow operations continue after unlock expiry.
- Encrypted draft save/load will fail with `not_unlocked` or `unlock_expired` unless the user unlocks again.

### Frontend Auth Check

Implementation:

- `frontend/lib/hooks/useAuth.ts`
- `frontend/app/(dashboard)/layout.tsx`

Behavior:

- Dashboard layout calls `useAuth()` once on mount.
- `useAuth()` calls `/api/v1/auth/session`.
- Success populates Zustand workspace/auth/unlock state.
- Failure routes to `/setup` for setup errors, otherwise `/login`.

Current gaps:

- No periodic session poll.
- No global handler for session expiry during mutations.
- No “session restored” banner after refresh/reload.
- No preservation of pending route/action after login.
- No shared session-expired modal.

### Workspace Session Behavior

Behavior:

- Session cookie payload contains the workspace ID.
- Workspace switching/new FY updates frontend Zustand state after successful mutation.
- Auth endpoint validates that cookie workspace still exists.

Current gaps:

- If a workspace is archived/deleted in another tab, stale pages only discover it on next API request.
- No cross-tab session/workspace sync.

## 2. Long-Running Workflow Risks

### Tax Journey

Current behavior:

- `answerQuestion`, `skipQuestion`, `goBack`, `cancelEdit`, and `completeInterview` are server mutations.
- Successful answers/skip actions update React Query cache and invalidate derived Journey, Readiness, and Export eligibility data.
- A browser refresh after a successful mutation reloads server session state.

Risks:

- If session expires during answer submit, the current question answer is not persisted.
- User sees page-local error copy, but not a clear re-login/retry path.
- Answer input for the current question is not draft-protected before submit.
- Back/cancel/edit mutations have limited error display.

MVP risk level: Medium.

### Manual Entry Forms

Current behavior:

- `ManualEntryForm` and investment subforms store all form state in React component state.
- Submit creates a TaxEvent/ReviewItem via `/api/v1/events/manual`.
- Error handling usually shows generic “Something went wrong. Please try again.”
- Existing backend encrypted draft endpoints support `manual_entry`, but frontend does not use them.

Risks:

- Browser refresh loses unsaved manual entry.
- Closing modal loses unsaved manual entry.
- Session expiry during submit may lose user-entered data unless the component remains mounted.
- Network drop during submit can leave user uncertain whether item was created.
- Generic errors hide whether the user needs to sign in again, reconnect, unlock, or retry.

MVP risk level: High.

### File Upload

Current behavior:

- Upload validates file type/size client-side.
- Upload starts with `/api/v1/documents/upload`.
- SSE tracks document processing.
- Polling fallback checks document summary when SSE errors/timeouts.
- Successful ready/failed state clears upload overlay.

Risks:

- Browser refresh during upload loses active upload UI state.
- Network drop during initial POST may leave an ambiguous “did upload complete?” situation.
- Upload state is local to component and not resumable.
- If session expires before upload POST, selected file is not recoverable after redirect.
- If session expires during SSE/polling, user sees generic failure/retry behavior rather than session-specific guidance.

MVP risk level: Medium.

### Review Actions

Current behavior:

- Review queue is server-loaded via React Query.
- Individual actions and bulk actions persist server-side.
- Success invalidates review queue.
- Inline answer directly calls API and invalidates queue.

Risks:

- Accidental action clicks are persisted immediately.
- Session expiry during action yields page-local or implicit mutation error with no global recovery path.
- Bulk action failure can leave uncertainty if some work completed server-side, depending backend atomicity.
- No session restored/refetch UX after reconnect.

MVP risk level: Medium.

### Evidence Checklist Decisions

Current behavior:

- Evidence obligations load through React Query.
- Accept/reject match decisions are server mutations.
- Success invalidates the obligations query.
- Manual refresh/reconcile button exists.

Risks:

- Session expiry during accept/reject is not handled globally.
- Failed decisions may be unclear.
- Stale checklist after reconnect depends on query refetch behavior, not explicit recovery UI.

MVP risk level: Low/Medium.

### Export Generation

Current behavior:

- Export generation creates a backend export job.
- Frontend polls status every 2 seconds while status is `generating`.
- Backend marks long-running interrupted jobs failed after stale threshold and returns safe “generate again” messaging.
- Export password is cleared from local state immediately after submit.

Risks:

- If session expires after job starts, polling/download can fail and send the user to login without preserving context.
- If user refreshes during generation, active export ID in component state is lost, though export history may show the record.
- Password cannot be retried automatically by design.

MVP risk level: Low/Medium.

## 3. Current Protection Mechanisms

### Server Persistence

Strong:

- Journey answers/skips persist server-side on each successful mutation.
- Review actions persist server-side.
- Manual event creation persists TaxEvents/ReviewItems.
- Uploaded documents persist on successful POST and processing state continues backend-side.
- Evidence decisions persist server-side.
- Export generation uses persisted export/job records.

Weak:

- Unsaved manual-entry data is not persisted.
- Current unsent Journey answer is not persisted.
- Active upload file selection is not recoverable after refresh.

### Frontend Cache Invalidation

Strong:

- Journey mutations invalidate session, summary, readiness, and export eligibility.
- Review mutations invalidate review queue.
- Evidence decisions invalidate obligation checklist.
- Upload completion invalidates documents.

Weak:

- Reconnect/refocus is not presented as a “restored” state.
- Some mutation errors do not invalidate or refetch after failure.
- No global cache invalidation after auth restoration.

### Local Component State

Strong:

- Forms retain input while component stays mounted after a failed submit.

Weak:

- Refresh, route change, modal close, or unmount loses local state.
- No reusable dirty-form tracking.
- No beforeunload protection.

### Retry Behavior

Current:

- React Query provider sets query retry to `1`.
- Mutations generally do not retry.
- NetworkBanner polls health every 5 seconds and shows an offline banner.
- Upload has explicit SSE timeout and polling fallback.

Weak:

- No mutation retry affordance pattern.
- No distinction between offline, expired session, validation error, and unknown failure in most forms.

### Autosave

Current:

- Backend encrypted draft endpoints exist for `tax_profile`, `interview`, and `manual_entry`.
- They require `require_unlock`.
- Frontend does not appear to use these endpoints in current long forms.

Weak:

- The most important long user-entered form, manual entry, has no autosave.
- Draft save failure on unlock expiry needs dedicated UX.

## 4. Gaps

## Gap 1: Global Session Expiry Handling

Problem:

- API client is a plain axios instance with no response interceptor.
- `useAuth()` checks only on dashboard mount.
- Pages individually handle errors inconsistently.

Impact:

- A user can fill a form, submit after expiry, and receive generic error copy.
- The app may redirect to login without explaining what happened or how to continue.

Beta severity: High.

## Gap 2: No Session Restored UX

Problem:

- Refresh/reconnect that successfully reloads server state has no visible acknowledgement.

Impact:

- Users do not know whether the app recovered their latest state after a network drop or browser refresh.

Beta severity: Medium.

## Gap 3: Manual Entry Draft Loss

Problem:

- Manual-entry forms are local state only.
- Existing encrypted draft API is unused.

Impact:

- Refresh, route change, or accidental close can lose several minutes of structured tax entry.

Beta severity: High.

## Gap 4: No Dirty Form / beforeunload Protection

Problem:

- Long forms do not mark dirty state globally.
- Browser/tab close and route navigation are not guarded.

Impact:

- User can lose unsaved data accidentally.

Beta severity: High for manual entry, Medium elsewhere.

## Gap 5: Upload Interruption Ambiguity

Problem:

- Upload state is local.
- The list refetches after successful completion, but a refresh mid-upload loses local status.

Impact:

- User may not know whether to retry or wait.

Beta severity: Medium.

## Gap 6: Inconsistent Mutation Error UX

Problem:

- Many mutations catch errors as generic failure.
- Session/unlock/offline/validation conditions are not normalized.

Impact:

- Users do not get reliable recovery instructions.

Beta severity: Medium/High.

## Gap 7: No Idle Or Expiry Warning

Problem:

- Session TTL and unlock TTL are known server-side, but frontend does not warn before expiry.

Impact:

- User can lose draft-save ability after unlock expiry, and can lose auth after full session expiry.

Beta severity: Medium.

## 5. MVP Recommendations

## Must Fix Before Beta

1. **Global API session-expiry handling**
   - Add axios response interceptor or shared API error normalizer.
   - Detect `session_expired`, `invalid_session`, `not_authenticated`, `unlock_expired`, and `not_unlocked`.
   - Show app-level session banner/modal instead of silently leaving page-local generic failures.
   - Preserve current route and attempted workflow context where practical.

2. **Manual-entry draft protection**
   - Reuse `/api/v1/drafts/manual_entry`.
   - Autosave dirty manual-entry state after debounce.
   - Restore draft when reopening manual entry.
   - Offer “Continue draft” and “Discard draft.”
   - Handle unlock expiry with clear “Unlock to save draft” copy.

3. **Dirty-form beforeunload protection**
   - Add a small reusable dirty-state hook for long forms.
   - Apply first to manual entry and investment subforms.
   - Apply to active upload state if a file is being uploaded/processed.
   - Do not add broad prompts to every page.

4. **Critical mutation error UX**
   - Standardize mutation error messages for Journey answer/skip, manual event create, upload, review action, evidence match decision, and export generate.
   - Show “Sign in again”, “Reconnect and retry”, or validation details where applicable.
   - Avoid automatic duplicate resubmission for non-idempotent actions.

5. **Session restored banner**
   - On dashboard mount after successful session check, show a compact banner when returning from refresh/reconnect/login redirect:
     - “Session restored. We reloaded your latest workspace state.”
   - Invalidate key server-state queries after restoration.

## Recommended Before Beta

1. **Idle/unlock expiry warning**
   - Warn when unlock is near expiry if encrypted drafts are enabled.
   - Optionally warn when full session is likely near expiry.

2. **Upload recovery hint**
   - After page load, if documents include processing items, show “Some uploads are still processing.”
   - Add explicit retry/reload guidance if upload POST fails.

3. **Export generation resume**
   - If export history contains a `generating` export after page refresh, automatically set it as active or show “Export in progress.”

4. **Cross-tab auth sync**
   - Use `storage` event or periodic session check to detect logout/workspace change across tabs.

## Post-Beta

1. Full offline mutation queue is not recommended for MVP because tax workflow mutations are not all idempotent.
2. Rich draft conflict resolution across devices/tabs.
3. Persistent upload session recovery with resumable upload protocol.
4. Sliding session renewal policy, if security posture allows.

## 6. Proposed MVP Architecture

### Session Event State

Add a frontend-only session resilience store:

- `status`: `ok | expired | unauthenticated | unlock_expired | offline | restored`
- `lastRestoredAt`
- `pendingPath`
- `lastErrorCode`

This can live in Zustand alongside the workspace store or as a small React context.

### API Error Normalizer

Add a helper around axios errors:

- `getApiErrorCode(error)`
- `getApiErrorMessage(error)`
- `isAuthError(error)`
- `isUnlockError(error)`
- `isNetworkError(error)`

Use it from:

- axios interceptor for global session state
- page-level mutation `onError`
- long-form submit handlers

### Session Restoration

On dashboard load:

1. call `/api/v1/auth/session`
2. update workspace store
3. invalidate or refetch critical queries:
   - `['interview', 'session']`
   - `['interview', 'summary']`
   - `['review-queue']`
   - `['documents']`
   - `['evidence', 'obligations']`
   - `['readiness']`
   - `['export-eligibility']`
4. show restored banner if previous state indicated interruption, refresh, reconnect, or post-login return

### Draft Protection

Use existing encrypted draft endpoints first:

- `POST /api/v1/drafts/manual_entry`
- `GET /api/v1/drafts/manual_entry`

Frontend approach:

- create `frontend/lib/api/drafts.ts`
- create `useEncryptedDraft(formType, value, dirty)`
- debounce save every 1-2 seconds
- save only non-empty dirty drafts
- load on modal open
- clear draft after successful manual event create

Unlock caveat:

- If `unlock_expired` occurs, keep local state and show inline “Unlock to keep saving draft.”
- Do not block form submission if `/events/manual` itself does not require unlock.

### Dirty Form Protection

Create `useBeforeUnload(enabled, message?)`.

Apply to:

- `ManualEntryForm`
- investment subforms
- active upload state in `UploadZone`

Do not apply to:

- Journey single-question answers, unless text/number inputs become long-form.
- Review one-click actions.
- Evidence match decisions.

## 7. Implementation Order

## Milestone 13B-2B: Session Error Foundation

Objective:

- Add shared API error normalization and global session/unlock state.

Backend changes:

- None expected.
- Optional: include absolute expiry timestamps in `/auth/session` if low-risk:
  - `session_expires_at`
  - `unlock_expires_at`

Frontend changes:

- Add API error helper.
- Add session resilience store/context.
- Add axios response interceptor or central mutation error adapter.
- Add app-level session expired/unlock expired banner.

Tests:

- API helper maps backend error shapes.
- 401 `session_expired` sets session expired state.
- 401 `not_authenticated` routes/prompts login.
- 401 `unlock_expired` shows unlock-specific message.
- Existing auth tests remain green.

Acceptance:

- Expired session during any API call produces a clear app-level recovery prompt.
- Page-local errors no longer hide auth expiry behind generic messages.

Estimated effort: Small/Medium.

## Milestone 13B-2C: Session Restored UX

Objective:

- Make refresh/reconnect recovery visible and refetch critical state.

Backend changes:

- None expected.

Frontend changes:

- Add `SessionRestoredBanner`.
- Update `useAuth()` or dashboard layout to mark restored state after successful session check.
- Invalidate critical queries after restoration.
- Preserve intended route after login if redirected due to expiry.

Tests:

- Dashboard shows restored banner after simulated restored state.
- Critical query invalidation runs after session restore.
- Login redirect returns to intended dashboard route when safe.

Acceptance:

- User sees a concise “session restored” signal after refresh/reconnect/login return.

Estimated effort: Small.

## Milestone 13B-2D: Manual Entry Draft Protection

Objective:

- Prevent unsaved manual-entry loss.

Backend changes:

- Prefer none, reuse existing `/drafts/manual_entry`.
- If current draft API response shape is inconsistent with frontend conventions, add additive `data` wrapper only if necessary.

Frontend changes:

- Add `frontend/lib/api/drafts.ts`.
- Add `useEncryptedDraft`.
- Serialize ManualEntryForm state, including nested investment forms.
- Restore draft on modal open.
- Clear draft on successful submit.
- Add beforeunload dirty protection.

Tests:

- Manual entry autosaves dirty state.
- Manual entry restores saved draft.
- Successful submit clears draft.
- Unlock expiry keeps local state and shows inline warning.
- beforeunload handler is installed only when dirty.

Acceptance:

- Refresh or modal reopen can recover in-progress manual entry when unlocked.

Estimated effort: Medium.

## Milestone 13B-2E: Critical Mutation Retry/Error UX

Objective:

- Standardize user recovery paths for failed mutations.

Backend changes:

- None expected.

Frontend changes:

- Add `MutationErrorInline` or shared message helper.
- Update Journey answer/skip/back/cancel errors.
- Update manual event forms.
- Update review action and bulk action errors.
- Update evidence match decision errors.
- Update export generate/status error handling.

Tests:

- Journey session-expired submit shows sign-in guidance.
- Manual entry network error keeps form data and offers retry.
- Review action failure shows item-level error.
- Evidence decision failure shows local retry copy.
- Export generate session expiry does not keep password in state.

Acceptance:

- Critical mutations fail visibly with actionable recovery copy.

Estimated effort: Medium.

## Milestone 13B-2F: Upload And Export Resume Hints

Objective:

- Reduce ambiguity after refresh/reconnect around upload/export processing.

Backend changes:

- None expected.

Frontend changes:

- Evidence page: show processing document hint from document list.
- UploadZone: beforeunload while uploading/processing.
- Export page: detect `generating` export in history and show in-progress state.

Tests:

- Processing document hint renders.
- beforeunload active during upload.
- Export page resumes in-progress export from history.

Acceptance:

- Refresh during processing workflows gives users a clear status path.

Estimated effort: Small/Medium.

## 8. Backend Change Summary

Minimum required backend changes:

- None strictly required for MVP because existing session errors and encrypted draft APIs already exist.

Optional backend additions:

- Add `session_expires_at` and `unlock_expires_at` to `/auth/session` for precise warnings.
- Add `DELETE /api/v1/drafts/{form_type}` to clear drafts explicitly after successful submit.
- Normalize draft API response into `{status, data}` shape if frontend integration needs consistency.

Avoid for MVP:

- Changing cookie TTL policy.
- Sliding sessions.
- Offline mutation queue.
- Resumable upload protocol.

## 9. Frontend Change Summary

Highest-impact frontend changes:

1. Global API error normalization/session state.
2. Session expired/unlock expired banners.
3. Session restored banner and critical query refetch.
4. Manual-entry encrypted draft autosave.
5. Dirty-form beforeunload protection.
6. Standard mutation error UX.
7. Upload/export resume hints.

## 10. Test Matrix

| Area | Test |
| --- | --- |
| Auth/session | Expired session response is detected globally. |
| Auth/session | Invalid session routes to login with preserved return path. |
| Auth/session | Unlock expiry shows unlock-specific warning, not generic failure. |
| Session restore | Successful session check after interruption shows restored banner. |
| Session restore | Critical queries are invalidated/refetched after restoration. |
| Manual entry drafts | Dirty form autosaves to draft endpoint. |
| Manual entry drafts | Existing draft restores on open. |
| Manual entry drafts | Successful submit clears draft. |
| Manual entry drafts | Unlock expiry does not wipe local state. |
| beforeunload | Prompt active only for dirty manual entry. |
| Journey | Answer submit session expiry shows sign-in/retry guidance. |
| Review | Review action failure shows item-level error. |
| Evidence checklist | Match decision failure keeps candidate visible and shows retry copy. |
| Upload | Active upload registers beforeunload guard. |
| Upload | Processing document list shows recovery hint after refresh. |
| Export | In-progress export is visible after refresh through history/status polling. |

## 11. Beta Readiness Impact

Current post-Recovery estimate: **88/100**.

After 13B-2B and 13B-2C:

- Estimated readiness: **89/100**
- Reason: session expiry and restoration become understandable.

After 13B-2D:

- Estimated readiness: **90/100**
- Reason: highest-risk unsaved form loss is addressed.

After 13B-2E and 13B-2F:

- Estimated readiness: **91/100**
- Reason: interruption recovery becomes consistent across core workflows.

## 12. Final Recommendation

**Recommendation: Implement Session Resilience MVP before invite-only Beta.**

Must Fix Before Beta:

1. global session-expiry handling
2. session restored banner
3. manual-entry encrypted draft protection
4. dirty-form beforeunload protection for manual entry
5. critical mutation error UX

Recommended Before Beta:

1. upload processing recovery hints
2. export generation resume hints
3. idle/unlock expiry warning

Post-Beta:

1. full offline mutation queue
2. resumable uploads
3. rich cross-tab draft conflict handling
4. sliding session renewal, if security policy allows
