# BETA_BLOCKERS

Scope: analysis-only assessment of blockers for safe, successful real-user Beta usage in Australia.

Context baseline:
- 11B Evidence Intelligence complete
- 12A Tax Fact Schema refactor complete
- 12B Readiness 2.0 additive rollout complete
- 12C Explanation Layer complete
- 12D Rule-version provenance complete
- 12E Export evidence preview complete
- Prior hardening audit score: 78/100

---

## Ranked Blocker List

## 1) No first-class disaster recovery path for workspace portability
- **Severity:** Critical
- **Category:** Recovery
- **Why it matters:** Real users need guaranteed ability to recover tax-year work if device/container/storage fails.
- **Real user impact scenario:** User loses Raspberry Pi disk or app volume and cannot reconstruct months of tax prep work.
- **Current system behavior:** Encrypted exports exist for accountant handoff, but no end-user workspace backup/restore contract for full app state continuity.
- **Recommended fix:** Introduce signed workspace backup/export + restore workflow with integrity verification and restore checkpoints.
- **Estimated implementation effort:** Large
- **Beta requirement:** Must Fix Before Beta

## 2) Session resilience gaps for long-running tax prep sessions
- **Severity:** High
- **Category:** Reliability
- **Why it matters:** Tax prep is long-lived; interruption tolerance must be reliable across refresh/network drops.
- **Real user impact scenario:** User spends 45 minutes in journey/review, refreshes on flaky Wi-Fi, and sees stale or confusing state.
- **Current system behavior:** Significant cache invalidation fixes shipped, but no explicit session-resume UX contract with offline/retry visibility.
- **Recommended fix:** Add explicit “session restored at …” + mutation retry state + interruption-safe draft indicators per critical form.
- **Estimated implementation effort:** Medium
- **Beta requirement:** Must Fix Before Beta

## 3) Evidence freshness trust signal is still weak for end users
- **Severity:** High
- **Category:** Data Integrity
- **Why it matters:** Users must trust whether checklist status is current before export.
- **Real user impact scenario:** User uploads document, sees checklist mismatch, assumes system is wrong and abandons.
- **Current system behavior:** Freshness fields and reconcile telemetry exist, but stale/fresh confidence is not strongly surfaced as decision-grade UX.
- **Recommended fix:** Prominent freshness badge with “last reconciled”, stale warning, and one-click forced reconcile status feedback.
- **Estimated implementation effort:** Small
- **Beta requirement:** Must Fix Before Beta

## 4) Manual-entry structured coverage is incomplete for common domains
- **Severity:** High
- **Category:** Tax Workflow
- **Why it matters:** Generic manual entries reduce tax-fact quality and evidence linkage confidence.
- **Real user impact scenario:** User enters allowance/travel/uniform using generic fields; downstream review/evidence quality degrades.
- **Current system behavior:** Key categories hardened, but multiple categories remain generic fallback.
- **Recommended fix:** Complete top-frequency remaining templates with schema validation + explanation templates.
- **Estimated implementation effort:** Medium
- **Beta requirement:** Must Fix Before Beta

## 5) Export handoff narrative remains fragmented across files
- **Severity:** High
- **Category:** Export
- **Why it matters:** Accountants need quick comprehension; fragmented artifacts increase review friction/errors.
- **Real user impact scenario:** Accountant misses unresolved evidence risk because context is split across several JSON/PDF files.
- **Current system behavior:** 04A and 05A improved clarity, but no consolidated reviewer index/checklist map.
- **Recommended fix:** Add a compact “Accountant Handoff Index” artifact linking tax items, evidence status, and blockers.
- **Estimated implementation effort:** Medium
- **Beta requirement:** Recommended Before Beta

## 6) Recovery-key and destructive-action safeguards need stronger UX hardening
- **Severity:** High
- **Category:** Security
- **Why it matters:** User-side key handling errors or accidental deletion can cause unrecoverable loss.
- **Real user impact scenario:** User archives/deletes workspace or loses recovery key without realizing irreversible consequences.
- **Current system behavior:** Security flows exist, but guardrails and practical recovery rehearsal patterns are limited.
- **Recommended fix:** Add explicit irreversible-action confirmation UX, recovery-key verification drill, and pre-delete backup prompt.
- **Estimated implementation effort:** Medium
- **Beta requirement:** Must Fix Before Beta

## 7) Mobile/tablet review and checklist ergonomics are not production-strong
- **Severity:** Medium
- **Category:** UX
- **Why it matters:** Many users will operate from iPad/mobile; dense lists can become error-prone.
- **Real user impact scenario:** User cannot efficiently navigate long evidence/review lists on tablet, causing missed confirmations.
- **Current system behavior:** Responsive layout exists, but long-list workflow ergonomics and touch efficiency are limited.
- **Recommended fix:** Add sticky summary controls, filter shortcuts, and mobile-first list compaction patterns.
- **Estimated implementation effort:** Medium
- **Beta requirement:** Recommended Before Beta

## 8) Reliability path for partial extraction failures needs stronger user guidance
- **Severity:** Medium
- **Category:** Reliability
- **Why it matters:** OCR/classification failures are normal; users need clear recovery paths.
- **Real user impact scenario:** Document extraction partially fails and user is unsure whether to re-upload or continue manually.
- **Current system behavior:** Error states exist, but guided remediation and retry strategy is limited.
- **Recommended fix:** Add structured failure reasons + guided next step (retry/manual entry/attach receipt path).
- **Estimated implementation effort:** Small
- **Beta requirement:** Recommended Before Beta

## 9) Audit timeline is not unified across journey→evidence→review→export
- **Severity:** Medium
- **Category:** Compliance
- **Why it matters:** Beta operations and user support need traceability for disputed outcomes.
- **Real user impact scenario:** User disputes why evidence was marked partial; support cannot quickly produce a coherent event chain.
- **Current system behavior:** Logs/provenance exist in parts, but no unified end-to-end timeline view.
- **Recommended fix:** Build an internal audit timeline view keyed by workspace/FY with major state transitions.
- **Estimated implementation effort:** Medium
- **Beta requirement:** Recommended Before Beta

## 10) Policy semantics still split between readiness and export layers
- **Severity:** Medium
- **Category:** Compliance
- **Why it matters:** Different pages can imply different readiness/export meanings.
- **Real user impact scenario:** User sees blocked readiness but still allowed export, interprets this as system inconsistency.
- **Current system behavior:** Intended soft-block behavior exists but requires nuanced interpretation.
- **Recommended fix:** Centralized policy dictionary + shared copy contract across readiness/export surfaces.
- **Estimated implementation effort:** Small
- **Beta requirement:** Must Fix Before Beta

## 11) Performance risk under bursty reconcile triggers for heavy users
- **Severity:** Medium
- **Category:** Performance
- **Why it matters:** Larger document/event volumes may stress request-path reconciliation.
- **Real user impact scenario:** Active user experiences lag during rapid edits/uploads.
- **Current system behavior:** Debounce/coalescing exists; no separate worker queue yet.
- **Recommended fix:** Instrument per-workspace reconcile cost thresholds and add optional background queue fallback.
- **Estimated implementation effort:** Medium
- **Beta requirement:** Post-Beta

## 12) Unsupported complex domains can cause false confidence
- **Severity:** Medium
- **Category:** Tax Workflow
- **Why it matters:** Users outside supported scope may assume completeness incorrectly.
- **Real user impact scenario:** Property investor expects full coverage but domain handling is partial.
- **Current system behavior:** Strong PAYG+basic investment path; complex domains not fully modeled.
- **Recommended fix:** Explicit scope gating and in-product “unsupported domain” warnings before data entry/export.
- **Estimated implementation effort:** Small
- **Beta requirement:** Must Fix Before Beta

---

## Required Review Areas Assessment

## A. Session Recovery
- Risk level: **High**
- Gaps: explicit resume guarantees, unsaved in-form drafts, interruption clarity.
- Beta stance: Must harden before open Beta.

## B. Workspace Recovery
- Risk level: **Critical**
- Gaps: full workspace backup/restore lifecycle and restore failure recovery.
- Beta stance: Must fix before Beta.

## C. Evidence Intelligence
- Risk level: **High**
- Gaps: user-facing stale-state trust signaling; reconcile timing transparency.
- Beta stance: Must fix before Beta.

## D. Review Workflow
- Risk level: **Medium**
- Gaps: accidental confirmation reversibility UX, unified auditability visibility.
- Beta stance: Recommended before Beta.

## E. Export Package
- Risk level: **High**
- Gaps: accountant handoff synthesis still fragmented.
- Beta stance: Recommended before Beta (or beta with narrow user profile + explicit caveat).

## F. Security
- Risk level: **High**
- Gaps: destructive-action safeguards and recovery-key operational UX.
- Beta stance: Must fix before Beta.

## G. Mobile / Tablet UX
- Risk level: **Medium**
- Gaps: long checklist/review ergonomics and touch-centric flows.
- Beta stance: Recommended before Beta.

## H. Reliability
- Risk level: **Medium**
- Gaps: extraction failure remediation clarity, partial processing recovery.
- Beta stance: Recommended before Beta.

## I. Tax Workflow Coverage
- Risk level: **High**
- Gaps: unsupported domains and generic manual entry pockets.
- Beta stance: Must scope-gate before Beta.

---

## Top 10 Beta Blockers

1. No full workspace backup/restore disaster recovery path  
2. Session resilience gaps for long-running sessions  
3. Evidence freshness trust signal not explicit enough  
4. Incomplete structured manual-entry coverage for common categories  
5. Recovery-key/destructive-action UX hardening gaps  
6. Readiness vs export policy semantics split in user-facing messaging  
7. Unsupported complex domain scope not strongly gated  
8. Export handoff narrative fragmentation for accountants  
9. Mobile/tablet long-list workflow friction  
10. Lack of unified audit timeline for support/compliance workflows

---

## Beta Readiness Score Recalculation After Fixes

Current assessed readiness: **78/100**.

If all **Must Fix Before Beta** items are completed:
- projected readiness: **88/100**

If both Must Fix + Recommended Before Beta are completed:
- projected readiness: **92/100**

Rationale:
- Largest risk reduction comes from recovery guarantees, policy consistency, and scope gating.
- Remaining delta to 100 is expected due to intentionally deferred advanced tax-domain breadth.

---

## Recommended Beta Scope

## Suggested scope
- **Invite-only Beta**
- **Single financial year per workspace**
- **Primary persona focus:** PAYG employees with common deductions + basic investments
- **Explicit exclusions:** complex property/sole-trader-heavy/advanced corporate action scenarios

## Operational controls for Beta
1. Forced scope disclaimer at onboarding.
2. Prominent unsupported-domain warnings.
3. Mandatory periodic backup/export prompt until full workspace backup ships.
4. Support playbook for extraction/reconcile/export failures.

---

## Recommended Beta User Profile

## Best-fit Beta cohorts
1. **Simple PAYG user (primary)**
2. **PAYG + light investor (bank interest, basic shares/crypto buy/sell)**
3. **PAYG + common deductions (donation/work expense/WFH)**

## Defer or tightly gate in early Beta
1. Contractor/sole trader with complex records
2. Property investor
3. High-complexity multi-asset investors requiring advanced CGT treatment

---

## Final Recommendation

**Recommendation: Beta after fixes**

## Rationale
The platform is close to Beta-usable for targeted personas, but current blockers around workspace recovery, session resilience, policy clarity, and scope gating are material risks for real users.  
Once Must Fix items are complete, a controlled invite-only Beta is appropriate.

