# Evidence Freshness Trust Audit

Milestone: 13B-3A  
Goal: design the minimum trust/freshness UX required so users understand whether Evidence Intelligence and Readiness information is current, stale, reconciling, or failed.

This is an audit/design document only. No runtime behavior changes are included.

Inputs reviewed:

- Evidence Intelligence implementation from 11B
- Readiness 2.0 implementation from 12B
- Explanation Layer implementation from 12C
- Export Evidence Preview from 12E
- `docs/SESSION_RESILIENCE_ACCEPTANCE.md`
- `docs/BETA_BLOCKERS.md`
- `backend/app/services/evidence_reconcile.py`
- `backend/app/api/routes/evidence.py`
- `backend/app/api/routes/readiness.py`
- `backend/app/api/routes/export.py`
- `frontend/app/(dashboard)/readiness/page.tsx`
- `frontend/app/(dashboard)/readiness/checklist/page.tsx`
- `frontend/app/(dashboard)/export/page.tsx`
- `frontend/lib/api/evidence.ts`
- `frontend/lib/api/types.ts`

## Executive Summary

Evidence freshness is partially implemented in the backend but not yet trustworthy enough in the user experience.

Current backend state already tracks:

- `Workspace.evidence_reconciled_at`
- `Workspace.evidence_reconcile_status`
- `Workspace.evidence_reconcile_meta`
- manual reconcile telemetry
- debounce skip metadata
- reconcile failure counters

Current frontend surfaces evidence counts and evidence warnings, but it does not consistently explain whether those counts are fresh, stale, currently reconciling, or based on a failed reconcile. This creates the exact Beta Blocker #3 risk: users can see evidence checklist/readiness/export differences and not know which surface to trust.

Minimum Beta requirement:

1. Expose the same evidence freshness payload consistently on Readiness, Evidence Checklist, and Export Eligibility.
2. Render a shared freshness badge with four states: Fresh, Reconciling, Stale, Failed.
3. Show last reconciled timestamp and concise status guidance.
4. Provide one-click forced reconcile with visible in-progress and error feedback.
5. Treat stale/failed freshness as a warning layer, not export hard-blocking yet.

## 1. Current Freshness Signals

## Evidence Checklist

Backend:

- `GET /api/v1/evidence/obligations` returns:
  - `obligations`
  - `freshness.evidence_reconciled_at`
  - `freshness.evidence_reconcile_status`
- `POST /api/v1/evidence/reconcile` returns:
  - `status`
  - `obligations_count`
  - `telemetry`
  - `freshness`

Frontend:

- `frontend/lib/api/evidence.ts` types include `freshness`.
- `frontend/app/(dashboard)/readiness/checklist/page.tsx` currently queries only `r.data.data.obligations`, discarding the backend `freshness` payload.
- The checklist page shows `Last refreshed` based on React Query `dataUpdatedAt`, which means “when this browser fetched data”, not “when Evidence Intelligence last reconciled.”
- Manual `Refresh checklist` exists and calls reconcile, but the UX does not distinguish:
  - reconcile currently running
  - reconcile skipped by debounce
  - reconcile failed
  - checklist fetched from stale obligations

Assessment:

- Backend freshness signal exists.
- Frontend trust signal is insufficient.

## Readiness Page

Backend:

- `GET /api/v1/readiness` returns:
  - legacy readiness fields
  - `evidence_obligation_summary`
  - `evidence_freshness`
  - `readiness_2_0`
- `evidence_freshness` includes:
  - `evidence_reconciled_at`
  - `evidence_reconcile_status`
  - `evidence_reconcile_meta`

Frontend:

- `frontend/lib/api/types.ts` includes `evidence_freshness`.
- `frontend/app/(dashboard)/readiness/page.tsx` renders readiness dimensions and evidence counts.
- The page currently does not render a clear freshness badge or last-evidence-reconciled timestamp.
- The page has legacy readiness stale handling through `data.is_stale`, but that is readiness score freshness, not evidence obligation freshness.

Assessment:

- Readiness has the backend data needed for MVP freshness UX.
- The UI needs to separate:
  - “overall readiness score updating”
  - “evidence obligations last reconciled”

## Export Eligibility

Backend:

- `GET /api/v1/export/eligibility` returns evidence preview counts:
  - required missing
  - required partially matched
  - required matched
  - recommended missing
  - blocking evidence obligations
  - `evidence_export_status`
- It does not currently include evidence freshness metadata.

Frontend:

- `frontend/app/(dashboard)/export/page.tsx` renders `Evidence Preview`.
- It explains evidence is a soft warning layer and links to `/readiness/checklist`.
- It does not tell the user whether export preview counts are based on a fresh or failed/stale reconcile.

Assessment:

- Export is the largest API gap for freshness trust.
- Export preview should include the same `evidence_freshness` shape as readiness/checklist.

## Reconcile Endpoints

Backend:

- `EvidenceReconcileService.trigger(...)` is the central service entry point.
- Trigger sources are tracked.
- Debounce/coalescing exists.
- Reconcile status transitions include `running`, `succeeded`, and `failed`.
- Telemetry tracks duration, created obligations/matches, skipped debounce runs, and failures.
- `POST /api/v1/evidence/reconcile` forces a full reconcile and returns rich telemetry.

Frontend:

- Evidence Checklist has a refresh button.
- Readiness page does not expose a direct evidence reconcile action.
- Export page does not expose a direct evidence reconcile action.
- Reconcile errors are not presented as a first-class freshness state.

Assessment:

- Backend service is strong enough for MVP.
- Frontend needs to surface status and failure paths consistently.

## Timestamps Already Exposed

Available today:

- `evidence_reconciled_at`
- React Query `dataUpdatedAt`
- readiness `calculated_at`
- readiness `readiness_2_0.last_calculated_at`
- reconcile telemetry `previous_reconciled_at`

Important distinction:

- `dataUpdatedAt` means browser fetch time.
- `calculated_at` means legacy readiness score time.
- `readiness_2_0.last_calculated_at` means response assembly time.
- `evidence_reconciled_at` means evidence obligations/matches were actually reconciled.

The UI must not treat these as interchangeable.

## 2. User Trust Gaps

## Stale Data Ambiguity

Gap:

- Users can see evidence counts without knowing whether obligations/matches were reconciled after the latest Journey answer, upload, manual item, or match decision.

Impact scenario:

- User uploads a donation receipt. Checklist still shows donation receipt missing because reconcile is stale or has not completed. User assumes the system is wrong.

MVP need:

- Show `Stale` when evidence state is known to be outdated or has never reconciled.
- Provide “Refresh evidence status” action.

## Reconcile In Progress Ambiguity

Gap:

- Backend can set status to `running`, but frontend does not render a “Reconciling” trust state.

Impact scenario:

- User clicks refresh and immediately sees unchanged counts. They do not know whether refresh is still running, skipped, failed, or complete.

MVP need:

- Show `Reconciling` while manual reconcile mutation is pending or backend status is `running`.
- Disable duplicate refresh clicks while pending.
- Show clear “Checking evidence matches…” copy.

## Reconcile Failure Ambiguity

Gap:

- Backend records failed status and failure telemetry, but UI does not consistently present failure as evidence freshness risk.

Impact scenario:

- A reconcile failure leaves stale obligations in place. Readiness/export still show counts, but users cannot tell that the counts may be unreliable.

MVP need:

- Show `Failed` when `evidence_reconcile_status === "failed"`.
- Include safe copy: “Evidence status could not be refreshed. Try again.”
- Provide retry.

## Export Preview Freshness Ambiguity

Gap:

- Export eligibility has evidence counts but no freshness status.

Impact scenario:

- User sees “Export is allowed, but evidence may be incomplete” and cannot tell whether the evidence preview reflects their latest upload/review action.

MVP need:

- Add `evidence_freshness` to export eligibility response.
- Render it next to Evidence Preview.
- If stale/failed, make export preview visibly cautionary without hard-blocking export yet.

## 3. Recommended States

## Fresh

Definition:

- `evidence_reconcile_status === "succeeded"`
- `evidence_reconciled_at` exists
- no current frontend reconcile mutation is pending
- optional MVP age threshold has not been exceeded

User copy:

- “Evidence status is current.”
- “Last checked: {timestamp}”

Visual treatment:

- Ready/sage badge.
- Compact and reassuring.

Beta behavior:

- Counts can be treated as trustworthy for review/export preview purposes.

## Reconciling

Definition:

- backend status is `running`, or
- frontend manual reconcile mutation is pending, or
- route-triggered reconcile has been initiated and API reports running

User copy:

- “Checking evidence status…”
- “We are updating checklist matches.”

Visual treatment:

- Amber/review badge with subtle pulse.
- No alarming red state.

Beta behavior:

- Counts can remain visible but should be labelled as updating.

## Stale

Definition:

- `evidence_reconciled_at` is null, or
- status is `idle` with no successful reconciliation, or
- freshness metadata indicates debounce/previous timestamp but relevant mutations happened since last reconcile if this is exposed later, or
- optional MVP age threshold is exceeded.

User copy:

- “Evidence status may be out of date.”
- “Refresh evidence status to check the latest uploads and tax items.”

Visual treatment:

- Amber/review badge.
- Show refresh action.

Beta behavior:

- Do not hard-block export yet.
- Make the trust warning visible on Readiness, Checklist, and Export.

## Failed

Definition:

- `evidence_reconcile_status === "failed"`

User copy:

- “Evidence status could not be refreshed.”
- “Your existing checklist is still visible, but it may be out of date.”

Visual treatment:

- Risk border/text, but calm copy.
- Show retry action.

Beta behavior:

- Do not hard-block export yet unless future policy changes.
- Export preview should include an explicit freshness warning.

## 4. Recommended UX Surfaces

## Readiness Page

Required MVP additions:

- Add evidence freshness badge near the `Evidence readiness` card.
- Show:
  - Fresh/Reconciling/Stale/Failed
  - last checked timestamp if available
  - concise explanation
  - link/button to Evidence Checklist
- If failed/stale:
  - show `Refresh evidence status`
  - keep readiness counts visible but label them as potentially stale

Recommended placement:

- Inside the `Readiness dimensions` panel, under or within the Evidence readiness card.
- Do not replace the legacy readiness ring.

Why:

- Users read readiness as the main trust surface.
- Evidence freshness must be visible where evidence can block readiness_2_0.

## Evidence Checklist

Required MVP additions:

- Use the full `GET /evidence/obligations` response instead of discarding freshness.
- Replace React Query `Last refreshed` with:
  - “Evidence last checked: {evidence_reconciled_at}”
  - plus optional “Page refreshed: {dataUpdatedAt}” only if needed for diagnostics
- Refresh button should show:
  - running state
  - success/fresh state
  - failed retry state
  - debounce skipped state as “Recently checked” if telemetry exposes it

Why:

- The checklist is where users inspect missing/matched evidence.
- It must distinguish “data fetched” from “evidence reconciled.”

## Export Eligibility Page

Required MVP additions:

- Add freshness metadata to export eligibility response.
- Render freshness status inside the Evidence Preview section.
- If stale/failed:
  - show warning copy: “Export is allowed, but this evidence preview may be out of date.”
  - link to checklist
  - optionally provide a refresh action if low-risk

Why:

- Export is the handoff point.
- Users and accountants need to know whether evidence warnings reflect the latest workspace state.

## 5. API Gaps

## Available Today

Backend already exposes:

- `GET /api/v1/evidence/obligations.data.freshness`
- `POST /api/v1/evidence/reconcile.data.freshness`
- `POST /api/v1/evidence/reconcile.data.telemetry`
- `GET /api/v1/readiness.data.evidence_freshness`
- workspace fields:
  - `evidence_reconciled_at`
  - `evidence_reconcile_status`
  - `evidence_reconcile_meta`

Frontend types already include:

- evidence obligations `freshness`
- readiness `evidence_freshness`

## Missing / Weak

## Export Eligibility Freshness

Gap:

- `GET /api/v1/export/eligibility` does not include `evidence_freshness`.

Recommended additive shape:

```json
{
  "evidence_freshness": {
    "evidence_reconciled_at": "2026-06-02T10:00:00+00:00",
    "evidence_reconcile_status": "succeeded",
    "evidence_reconcile_meta": {
      "trigger_source": "manual_reconcile",
      "reconcile_duration_ms": 42,
      "reconcile_failures": 0
    }
  }
}
```

## Freshness State Derivation

Gap:

- The frontend has to infer Fresh/Reconciling/Stale/Failed from raw fields.

Recommendation:

- MVP can derive on the frontend via shared helper:
  - `failed` if status is `failed`
  - `reconciling` if status is `running` or mutation pending
  - `stale` if no timestamp or status is `idle`
  - `fresh` if status is `succeeded` and timestamp exists
- Phase 2 can expose a backend-normalized `freshness_state`.

## Last Mutation Since Reconcile

Gap:

- Backend records last reconcile time, but does not expose a simple “workspace evidence inputs changed after last reconcile” boolean.

Recommendation:

- For MVP, rely on status/timestamp and route-triggered reconciles.
- Phase 2 should add an explicit stale detector using max updated time from Journey/document/event/match sources.

## Reconcile Failure Details

Gap:

- `evidence_reconcile_meta` is generic and may include operational fields, but frontend needs safe user-facing failure guidance.

Recommendation:

- MVP UI should avoid technical failure details.
- Backend can later add `last_error_code` / `last_error_message_safe`.

## 6. MVP Implementation Order

## Backend

1. Add `evidence_freshness` to `GET /api/v1/export/eligibility`.
   - Reuse `Workspace.evidence_reconciled_at`, `evidence_reconcile_status`, and `evidence_reconcile_meta`.
   - Add tests that export eligibility includes freshness metadata.

2. Confirm readiness and evidence APIs keep returning freshness.
   - Add tests if not already explicit.

3. Do not change readiness score or export gating.

## Frontend

1. Add shared helper/component:
   - `EvidenceFreshnessBadge` or equivalent.
   - Input: freshness payload + optional `isReconciling`.
   - Output states: Fresh, Reconciling, Stale, Failed.

2. Evidence Checklist:
   - Query full payload, not only obligations.
   - Render freshness badge and last checked time.
   - Tie manual reconcile pending/error/success into badge state.

3. Readiness Page:
   - Render freshness badge in Evidence readiness card.
   - Show stale/failed copy and link to checklist.

4. Export Page:
   - Render freshness badge in Evidence Preview.
   - If stale/failed, show “Export is allowed, but evidence preview may be out of date.”

## Tests

Backend:

- `GET /export/eligibility` includes `evidence_freshness`.
- Freshness status reflects workspace fields.
- Existing export eligibility behavior remains unchanged.

Frontend:

- Evidence Checklist renders Fresh with timestamp.
- Evidence Checklist renders Reconciling while refresh is pending.
- Evidence Checklist renders Stale when no timestamp/status idle.
- Evidence Checklist renders Failed with retry guidance.
- Readiness Evidence card renders freshness status.
- Export Evidence Preview renders freshness status.
- Stale/failed export freshness does not disable export button.

## Must Fix Before Beta

1. **Evidence freshness badge on Readiness page**
   - Users must know whether evidence readiness counts are current.

2. **Evidence freshness badge on Evidence Checklist**
   - Users must distinguish page refresh from evidence reconciliation.

3. **Export Evidence Preview freshness**
   - Export evidence risk must show whether counts are based on current evidence state.

4. **Clear failed reconcile state**
   - Failed reconcile must be visible, retryable, and not silently treated as fresh.

5. **Clear stale state**
   - Never-reconciled or idle/no timestamp state must be labelled as stale/not yet checked.

## Recommended After Beta

1. Backend-derived `freshness_state`.
2. Explicit “inputs changed since last reconcile” detector.
3. Per-source freshness details:
   - Journey
   - documents
   - manual events
   - match decisions
4. Reconcile duration/history panel for support.
5. Background reconcile queue for heavier workspaces.

## Risks

## Confusing Freshness With Readiness Score

Risk:

- Users may see legacy readiness `is_stale` and evidence freshness as the same concept.

Mitigation:

- Label evidence freshness as “Evidence status last checked.”
- Keep legacy readiness score language separate.

## Over-warning Users

Risk:

- Too many badges can make the product feel broken.

Mitigation:

- Fresh state should be compact.
- Stale/failed state should be visible but calm and action-oriented.

## False Freshness

Risk:

- Status can be `succeeded` even if a mutation happens immediately after.

Mitigation:

- Route-triggered reconcile and debounce reduce this risk today.
- Phase 2 should add explicit input-change tracking.

## Final Recommendation

Proceed with Milestone 13B-3B: Evidence Freshness MVP.

Recommended implementation sequence:

1. Backend export eligibility freshness payload.
2. Shared frontend freshness badge/helper.
3. Evidence Checklist integration.
4. Readiness page integration.
5. Export page integration.
6. Focused backend/frontend tests.

This is a Must Fix Before Beta item because evidence obligations now influence Readiness 2.0 and Export Evidence Preview. Users must be able to trust whether those surfaces are current before using the platform in a real Beta workflow.
