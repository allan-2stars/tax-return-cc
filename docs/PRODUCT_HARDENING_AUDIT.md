# PRODUCT_HARDENING_AUDIT

Scope audited: post-11B/12A/12B/12C/12D/12E platform state.  
This is an audit-only report; no runtime changes are included.

---

## 1) Architecture Review

## Current subsystem map
1. **Journey/Interview Engine**
   - State machine with branching, skip/edit semantics, incomplete tracking.
2. **Evidence Intelligence**
   - `EvidenceObligation` + `EvidenceMatch`, deterministic reconciliation, trigger-based freshness.
3. **Review Engine**
   - `TaxEvent` -> `ReviewItem` queue with user/agent review statuses.
4. **Readiness**
   - Legacy readiness score + additive `readiness_2_0` multidimensional payload.
5. **Export**
   - Eligibility checks + encrypted package generation, evidence preview soft-block messaging.
6. **Explanation Layer**
   - Deterministic template service with sidecar explanations in review/evidence/export artifacts.

## Current data flow map
1. Journey answers and manual events create/update `TaxProfile`, `InterviewSession`, `TaxEvent`.
2. Review queue derived from `TaxEvent` state and metadata.
3. Evidence reconcile builds obligations and candidate matches from journey/profile/events/documents.
4. Readiness consumes legacy score inputs + evidence obligation summaries + journey incomplete signals.
5. Export eligibility consumes interview/review/document checks + evidence preview (soft-block only).
6. Export package serializes tax/review/evidence snapshots (now including explanation sidecars).

## Coupling risks
1. **Cross-module policy spread**: journey blocking logic appears in multiple layers (interview, readiness_2_0, export).
2. **Schema drift risk**: manual-entry schema contracts live across docs/forms/backend validators and can diverge.
3. **Dual-run readiness complexity**: legacy + 2.0 model coexistence can confuse both code and UX semantics.
4. **Reconcile trigger fan-out**: many mutation surfaces trigger reconcile, increasing contention risk under burst load.

## Technical debt
1. Some manual-entry categories still generic (`description/amount/date`) fallback.
2. Explanation coverage is partial by category; generic fallback still common.
3. Policy constants are not fully centralized as a single “platform policy contract”.
4. No background queue/worker partition for reconcile; currently request-path + safe wrapper model.

---

## 2) UX Review

## Onboarding
- Strengths: clear workspace model, explicit auth/setup boundaries.
- Gaps: readiness intent and “what blocks final output” messaging still requires user interpretation across pages.

## Journey flow
- Strengths: skip/edit semantics significantly improved; incomplete questions modeled explicitly.
- Gaps: branch-heavy flows still cognitively dense; resumability messaging can be clearer earlier.

## Review flow
- Strengths: queue segmentation and explanation sidecars improve explainability.
- Gaps: dense cards for heavy users; limited bulk contextual explanation triage.

## Evidence checklist
- Strengths: obligation/match lifecycle is explicit; candidate vs accepted/rejected semantics are clear.
- Gaps: no manual remapping flow yet (accept/reject only), which can stall edge-case reconciliation.

## Readiness page
- Strengths: readiness_2_0 three-axis model is directionally correct; blockers/warnings separation is useful.
- Gaps: coexistence with legacy score still produces conceptual duplication despite recent UI dedup.

## Export page
- Strengths: evidence soft-block preview is informative without hard behavior breakage.
- Gaps: users may still confuse “allowed now” with “fully complete evidence posture”.

---

## 3) Security Review

## Session handling
- Positive: explicit authenticated workspace binding and setup-confirmation flow.
- Risk: long-lived client state + multi-page cache coherence can still create stale UX perceptions (mostly resolved, but monitor).

## Workspace isolation
- Positive: routes and tests consistently enforce workspace/FY scoping in evidence/review/export.
- Risk: additive new endpoints must keep this pattern strict; contract tests should remain mandatory.

## Export package
- Positive: encrypted ZIP generation and deterministic artifact structure.
- Risk: additive artifacts increase data exposure surface; ensure no sensitive raw extracted text leaks in new files.

## Encryption boundaries
- Positive: documented encrypted exports and auth key management boundaries exist.
- Risk: operational controls (key rotation cadence, incident runbooks) are not represented in milestone docs.

## Auditability
- Positive: rule_version provenance and audit logs are present.
- Gap: no single audit timeline combining journey answer changes + reconcile decisions + export snapshot metadata.

---

## 4) Tax Workflow Review

## Missing tax domains (high level)
1. Broader investment complexity (lot-level CGT tracking depth, advanced corporate actions).
2. Business/sole trader detail depth (outside current primary PAYG focus).
3. Some deduction/income categories still rely on generic fallback templates.

## Weak manual-entry categories
- Remaining generic/fallback categories should be promoted to structured templates in planned batches.

## Evidence coverage gaps
1. Rule coverage is still intentionally narrow; several categories lack specific obligations.
2. Deterministic matching is conservative; unmatched-but-valid evidence still needs manual resolution patterns.

## Review coverage gaps
1. Category-specific review guidance remains uneven.
2. Agent-review escalation policy could be more explicit and uniform across categories.

---

## 5) Export Review

## Package completeness
- Strong: canonical evidence status file (`05A-EVIDENCE-STATUS.json`) plus additive review artifact (`04A-REVIEW-ITEMS.json`) improve interpretability.
- Gap: no dedicated consolidated “review narrative index” for accountants across artifacts.

## Accountant usability
- Improved by explanation sidecars and evidence summaries.
- Still requires opening multiple files for full context stitching.

## Explanation usefulness
- Good for baseline clarity.
- Limited by deterministic template breadth and generic fallback for uncatalogued categories.

---

## 6) Performance Review

## Reconcile triggers
- Current approach is practical and safe; debounce/coalescing mitigates burst pressure.
- Risk: high-churn workflows can still generate repeated read/write load across obligation/match tables.

## Readiness calculation
- Legacy score + readiness_2_0 composition increases computation and response payload complexity.
- Risk is manageable now but should be profiled under production-like dataset sizes.

## Export generation
- Deterministic and stable; asynchronous job architecture improved resilience.
- Risk: heavy work remains within app process model rather than dedicated worker tier.

---

## 7) Production Readiness Score

**Score: 78 / 100**

## Rationale
1. Core domain flows (journey/review/evidence/readiness/export) are now coherent and test-backed.
2. Security and scoping controls are generally strong and validated by tests.
3. Explainability and evidence provenance significantly improved.
4. Remaining risk is mostly in policy consolidation, category coverage depth, and operational hardening at scale.

---

## 8) Recommended Roadmap

## Must Fix Before Beta
1. **Policy consolidation pass**
   - Single source for blocking/warning rules across readiness/export/journey.
2. **Structured template completion for top generic manual categories**
   - Reduce fallback usage in high-frequency categories.
3. **Evidence rule coverage expansion for top missing tax domains**
   - Add deterministic obligations where confidence is high.
4. **Cross-surface consistency tests**
   - Ensure readiness/export/evidence/journey stay in sync on incomplete and blocker semantics.
5. **Operational runbook hardening**
   - Reconcile failure handling, export failure recovery, telemetry dashboards.

## Nice To Have Before Beta
1. Manual evidence remap flow (beyond accept/reject candidate).
2. Compact “accountant handoff index” file inside export package.
3. Explanation fallback metadata (`is_generic_fallback`) for reviewer confidence signaling.
4. UX micro-polish for dense review/evidence lists and progressive disclosure.

## Post-Beta
1. Deeper tax domain expansion (advanced investment/CGT scenarios).
2. Worker-queue offload for heavy reconcile/export workloads.
3. Optional curated reference/citation layer for explanations.
4. Potential hard evidence gate alignment once product policy finalizes.

---

## Final assessment

The platform is in a strong late-pre-beta state with robust additive architecture.  
The next critical step is not major feature breadth; it is **policy and coverage hardening** to prevent drift between journey, evidence, readiness, and export semantics as the system scales.

