# RELEASE_NOTES_12C

## Milestone 12C Summary

Milestone 12C introduced an additive **Explanation Layer** across backend APIs, frontend review/evidence UX, and export artifacts.  
The objective is transparency: users and reviewers can see why items and obligations exist and what to check.

No readiness score policy, export gating policy, or interview/review decision logic was changed in this milestone.

---

## 12C-1: Explanation Layer Design

Design document created:
- `docs/ATO_EXPLANATION_LAYER.md`

Design established:
- explanation targets (`TaxEvent`/`ReviewItem`, `EvidenceObligation`, `EvidenceMatch`, readiness/export signals)
- canonical explanation payload fields
- deterministic template approach
- rule-version provenance expectations
- additive rollout and test matrix

---

## 12C-2: Backend Explanation Templates

Implemented deterministic template service:
- `backend/app/services/explanations.py`

Initial supported categories:
- `bank_interest`
- `donation`
- `work_expense`
- `wfh_deduction`
- `foreign_income`
- `managed_fund_distribution`
- `shares_acquisition`
- `crypto_acquisition`
- `capital_gain`
- `capital_loss`

Additive API sidecar exposure:
- Review queue items include `explanation`
- Evidence obligations include `explanation`

No fields removed from existing response contracts.

---

## 12C-3: Frontend Explanation UI

Frontend rendering added for explanation sidecars:
- Review cards: compact summary + expandable details
- Evidence checklist rows: summary + expandable details (+ rule version when available)

Key detail blocks:
- Why this matters
- What to check
- Expected evidence

UX behavior:
- kept compact by default
- details collapse/expand per item
- existing candidate/accepted/rejected match actions unchanged

---

## 12C-4: Export Package Inclusion

Export artifacts now include explanations for reviewer context.

## Added artifact
- `04A-REVIEW-ITEMS.json`
  - review item snapshot
  - includes explanation sidecar per review item

## Extended canonical evidence artifact
- `05A-EVIDENCE-STATUS.json`
  - remains canonical evidence status file
  - now includes explanation sidecar on listed incomplete obligations

These changes are additive. Existing artifact names and prior files remain present.

---

## Explanation Payload Coverage

Explanation sidecars include:
- `plain_english_summary`
- `why_it_matters`
- `what_user_should_check`
- `evidence_expected`
- `confidence_level`
- `rule_version`
- `source`

---

## Current Limitations

1. Deterministic templates only.
2. No LLM freeform explanation generation.
3. No legal/tax advice wording.
4. Uncatalogued categories use safe generic fallback text.
5. No curated citation/ATO reference automation yet.

---

## Compatibility Notes

- Additive-only rollout; no removals of existing API fields.
- No changes to readiness scoring behavior.
- No changes to export hard-gating behavior.
- No changes to review action semantics.

---

## Recommended Next Milestone

Recommended next step: **12C-6 Explanation Coverage Hardening + API Consistency**

Suggested scope:
1. Expand deterministic templates for remaining high-frequency uncatalogued categories.
2. Normalize explanation payload shape across all surfaces (review, evidence, readiness, export preview).
3. Add explicit fallback metadata marker (e.g. `is_generic_fallback`) for auditability.
4. Add frontend affordances for dense queues (truncate + “show more” for long explanation text).
5. Add contract tests to guarantee explanation field presence/shape where expected.

