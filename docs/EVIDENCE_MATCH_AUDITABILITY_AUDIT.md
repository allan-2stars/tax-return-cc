# Evidence Match Auditability Audit

## Scope

This audit evaluates whether Evidence Match decisions currently provide enough traceability, visibility, and recoverability for Invite-only Beta.

Reviewed inputs:

- `EvidenceObligation` / `EvidenceMatch` models
- evidence reconcile engine
- evidence accept/reject API flow
- Evidence Checklist UI
- Explanation Layer
- Review Auditability implementation
- [BETA_RC_CHECKLIST.md](./BETA_RC_CHECKLIST.md)

This is an audit only. No runtime behavior was changed.

## Executive Summary

Evidence Match auditability is materially weaker than Review auditability.

Today, the product supports the operational basics:

- candidate matches are shown
- users can accept or reject them
- accepted and rejected decisions persist across reconcile runs
- obligation status updates deterministically

But it does **not** yet provide equivalent history and recovery semantics:

- no first-class decision history
- no actor attribution
- no user-visible timeline
- no undo / revert flow
- no decision note or rationale capture
- no clear stale-decision handling when new evidence arrives later

### Readiness assessment

- **Invite-only Beta:** sufficient, but with explicit operational risk
- **Public Beta:** not sufficient
- **Production:** not sufficient

The current implementation is acceptable only if the invite-only cohort is small, monitored, and supported by operator oversight.

## 1. Current Evidence Match Lifecycle

### Current states

`EvidenceMatch.status` supports:

- `candidate`
- `accepted`
- `rejected`

### Current flow

1. Reconcile generates deterministic candidate matches from documents and tax events.
2. User may accept or reject a candidate match from the Evidence Checklist UI.
3. The backend updates the match row in place.
4. The parent `EvidenceObligation.status` is recalculated:
   - `matched` if any accepted match exists
   - `partially_matched` if no accepted match exists but candidate matches exist
   - `missing` if neither accepted nor candidate matches exist

### Reconcile regeneration behavior

Current reconcile behavior is conservative:

- candidate matches may be rebuilt
- accepted matches are preserved
- rejected matches are preserved
- duplicate candidate recreation is avoided for preserved decisions

This is good for decision persistence, but it is persistence of **current state**, not persistence of **decision history**.

## 2. Existing Auditability

### What exists

- `EvidenceMatch.created_at`
- `EvidenceMatch.updated_at`
- persistent current status (`candidate` / `accepted` / `rejected`)
- obligation-level explanation sidecars
- visible current-state wording in UI:
  - `Possible match found`
  - `Matched by`
  - `Rejected match`

### What does not exist

- no `EvidenceMatchDecisionHistory` or equivalent
- no changed-fields history
- no actor attribution on accept/reject
- no user-supplied note or rationale
- no dedicated evidence-match timeline UI
- no evidence-match audit trail comparable to `ReviewDecisionHistory`
- no explicit evidence-decision audit log surfaced to users

### Assessment

Current auditability is **partial**. The system can show what the current decision is, but not:

- who made it
- when the decision was made in a meaningful user-facing way
- what the previous state was
- why it was changed
- whether it was later reversed

## 3. Existing Recoverability

### What exists

- accepted and rejected decisions persist across reconcile
- the current row can be updated again if surfaced and still present

### What does not exist

- no explicit undo action
- no “restore to candidate” workflow
- no “undo last decision” policy
- no visible prior decisions
- no safety prompt for accidental accept/reject

### Assessment

Recoverability is **weak**.

In practice, a user can only work with the current visible state. There is no formal recovery path equivalent to review-item undo. That is acceptable for a tightly managed invite-only cohort, but not strong enough for broader self-serve use.

## 4. Consistency with Review Auditability

| Capability | Review Auditability | Evidence Match Auditability |
|---|---|---|
| Decision history | Yes | No |
| Structured changed fields | Yes | No |
| Actor attribution | Yes | No |
| User-visible timeline | Yes | No |
| Undo support | Yes, limited | No |
| Bulk safeguard support | Yes | Not applicable today |
| Current-state visibility | Yes | Yes |
| Explanation sidecar | Yes | Yes |

### Assessment

Evidence Match decisions are currently one maturity level behind Review decisions.

Review has crossed the minimum threshold for user-traceable decisions. Evidence Match has not. That inconsistency is acceptable short term only because evidence-match decisions are narrower in scope and still bounded by deterministic reconciliation, but the gap is real.

## 5. User Risks

### High-risk user scenarios

#### 1. Accidental accept

User accepts a candidate match that is only partially correct. The obligation becomes `matched`, but there is no visible history showing when or why that happened.

#### 2. Accidental reject

User rejects a valid candidate match. The obligation remains `missing` or `partially_matched`, but there is no built-in recovery affordance or decision rationale.

#### 3. Stale decision after new evidence arrives

User previously rejected a candidate. A better document arrives later. The user can see a new candidate, but cannot inspect the prior rejection history or compare why the old decision happened.

#### 4. Support / operator traceability gap

During invite-only Beta, support may need to answer: “Why does this obligation show rejected?” Current implementation does not provide enough first-class user-visible provenance.

#### 5. Rationale loss

Because no note/rationale is captured, the system cannot distinguish:

- user rejected because the document was wrong
- user rejected because the document was blurry
- user rejected by mistake

## 6. Recommended MVP Improvements

### Must Fix Before Broader Beta

#### A. Add first-class evidence match decision history

Minimum fields should mirror the review pattern:

- match id
- workspace id
- obligation id
- action
- previous status
- new status
- actor
- optional note
- created_at

Reason: current-state persistence is not enough for traceability.

#### B. Add user-visible evidence match history

Expose a compact timeline in the Evidence Checklist:

- accepted / rejected
- timestamp
- actor
- optional rationale

Reason: supportability and user trust.

#### C. Add latest-decision undo or reset-to-candidate

Conservative scope is sufficient:

- undo latest accepted
- undo latest rejected
- restore to `candidate` if safe

Reason: accidental evidence decisions currently have no clean recovery path.

### Recommended Before Public Beta

#### D. Capture optional user rationale

Short note such as:

- “wrong document”
- “duplicate statement”
- “manual evidence supplied elsewhere”

Reason: reduces support ambiguity.

#### E. Flag potentially stale decisions when new candidate evidence appears

If a previously rejected area receives new candidate matches, surface that clearly.

Reason: evidence workflows evolve over time; static decisions can mislead.

#### F. Add evidence-decision audit log integration

Not necessarily user-facing first, but operationally useful.

Reason: support and incident traceability.

### Post-Beta

#### G. Unified decision timeline across review + evidence

Single cross-domain audit surface for:

- review decisions
- evidence decisions
- export warnings / blockers

#### H. Bulk evidence-match actions, only if checklist volume justifies it

Not needed yet.

## 7. Production Readiness Impact

Current Evidence Match auditability lowers confidence in three ways:

1. **Supportability risk**  
   Current staff cannot easily reconstruct decision intent from product data alone.

2. **User trust risk**  
   Users can see the current result, but not enough provenance to trust or challenge it.

3. **Recovery risk**  
   Mistakes are recoverable only through ad hoc state changes, not deliberate undo semantics.

### Readiness impact

- Invite-only Beta impact: manageable with operator oversight
- Public Beta impact: blocking
- Production impact: blocking

## 8. Final Decision

### Sufficient for invite-only Beta?

**Yes, with conditions.**

Conditions:

- small cohort
- support-assisted rollout
- clear internal runbook for evidence-decision troubleshooting
- explicit acknowledgement that evidence-match history and undo are not yet complete

### Sufficient for public Beta?

**No.**

Public Beta should not rely on current-state-only evidence decisions.

### Sufficient for production?

**No.**

Production requires first-class history, rationale, and recoverability comparable to Review auditability.

## Recommended Next Step

Implement an `EvidenceMatchDecisionHistory` slice modeled closely on `ReviewDecisionHistory`, then add:

1. history API exposure
2. checklist timeline UI
3. conservative undo of the latest evidence decision

That is the shortest path to aligning Evidence Match auditability with the review system already accepted for Beta.
