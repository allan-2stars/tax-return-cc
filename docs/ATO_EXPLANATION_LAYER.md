# ATO Explanation Layer (Design Only)

## 1) Purpose

Add an **explanation layer** that helps users understand why items appear in Journey/Review/Evidence/Readiness/Export flows.  
This layer is additive, review-oriented, deterministic, and versioned. It is not legal or tax advice.

---

## 2) Explanation Targets

Explanation records can attach to:

1. `TaxEvent` / `ReviewItem`
2. `EvidenceObligation`
3. `EvidenceMatch`
4. `Readiness` blockers/warnings
5. `Export` evidence preview warnings

`target_type` should be an enum-like string:
- `tax_event`
- `review_item`
- `evidence_obligation`
- `evidence_match`
- `readiness_signal`
- `export_warning`

---

## 3) Canonical Explanation Fields

```json
{
  "explanation_id": "exp_xxx",
  "target_type": "evidence_obligation",
  "target_id": "obl_xxx",
  "category": "evidence_requirement",
  "plain_english_summary": "This item expects a supporting statement.",
  "why_it_matters": "This helps confirm the tax item is accurate for review.",
  "what_user_should_check": "Check dates, payer/payee, and amount alignment.",
  "evidence_expected": ["annual statement", "receipt", "invoice"],
  "confidence_level": "high",
  "rule_version": "2026.1",
  "source": "rule"
}
```

### Field semantics
- `confidence_level`: `low | medium | high`
- `source`: `rule | extraction | user_entry | review | evidence_match`
- `category`: stable classifier, e.g. `income`, `deduction`, `investment`, `evidence_requirement`, `readiness_blocker`

---

## 4) Example Explanations (Template Set)

## bank_interest
- Summary: Bank interest was identified as taxable income for review.
- Why it matters: Interest may affect total assessable income.
- User should check: institution/account type, interest amount, period.
- Evidence expected: annual interest statement.

## donation
- Summary: A donation entry was added and should be checked for eligibility details.
- Why it matters: Donation claims usually depend on recipient status and receipt support.
- User should check: charity name, date, amount, receipt availability.
- Evidence expected: donation receipt.

## work_expense
- Summary: A work-related expense entry was recorded for review.
- Why it matters: Work-related claims should align to work use and records.
- User should check: expense type, work-related %, amount/date.
- Evidence expected: receipt or invoice.

## wfh_deduction
- Summary: Work-from-home deduction details were provided and need method-consistent evidence.
- Why it matters: WFH claims typically rely on records aligned to method used.
- User should check: method, hours/amount, financial year.
- Evidence expected: diary/timesheet/log and method support records.

## foreign_income
- Summary: Foreign income details were provided for conversion and review.
- Why it matters: FX conversion and tax paid fields affect review outcomes.
- User should check: currency, exchange rate, AUD amount, foreign tax paid.
- Evidence expected: foreign income statement and FX basis record.

## managed_fund_distribution
- Summary: Managed fund distribution components were captured for review.
- Why it matters: Component splits can affect downstream tax treatment.
- User should check: fund name, distribution amount, component fields, date.
- Evidence expected: annual tax statement/distribution statement.

## shares_acquisition
- Summary: Share acquisition was recorded as a non-disposal event.
- Why it matters: Acquisitions establish cost-base context for future disposals.
- User should check: stock code, units, purchase details, brokerage.
- Evidence expected: contract note/broker transaction record.

## crypto_acquisition
- Summary: Crypto acquisition was recorded as a non-disposal event.
- Why it matters: Acquisition records support future disposal and cost tracking.
- User should check: token code, quantity, AUD value, transaction date.
- Evidence expected: exchange statement/transaction export.

## capital_gain / capital_loss
- Summary: A disposal event indicates a potential capital gain/loss outcome for review.
- Why it matters: Disposal outcomes may affect taxable position.
- User should check: disposal proceeds, date, linked acquisition assumptions.
- Evidence expected: sell transaction record and related acquisition evidence.

---

## 5) Integration Plan

## Backend schema/service (additive)
- Add `ExplanationRecord` model (or materialized payload service) with the canonical fields.
- Generate explanations through deterministic templates keyed by:
  - event type/category
  - obligation key/status
  - readiness blocker/warning type
  - export evidence warning type
- Include `rule_version` from evidence/rule context (`CURRENT_EVIDENCE_RULE_VERSION`) where applicable.

## API shape (additive)
- Option A: embed `explanation` object directly in existing payload entities.
- Option B: sidecar collection:
  - `explanations: [{...}]`
  - with `target_type + target_id` references.
- Prefer sidecar first to avoid broad response rewrites.

## Frontend display locations
- Review item details drawer/card: show explanation summary + “what to check”.
- Evidence checklist rows: show obligation/match explanation and confidence.
- Readiness page blockers/warnings: expandable explanation text.
- Export page evidence preview: explanation snippets for blockers/warnings.

## Export package inclusion
- Add `06-EXPLANATIONS.json` (or adjacent canonical filename via release decision).
- Include explanation payloads referenced by exported tax/evidence/readiness artifacts.

## Rule-version provenance
- Every rule-derived explanation carries:
  - `rule_version`
  - `source = rule`
- Non-rule explanations may set `rule_version = null`.

---

## 6) Constraints and Guardrails

1. No legal/tax advice language.
2. Educational + review-oriented wording only.
3. No auto-crawled ATO citations.
4. If references are used later, they must come from curated, explicit URL maps.
5. No LLM-generated freeform explanations in MVP; template/rule-based only.

---

## 7) Test Matrix

## Backend
1. Explanation generation for each supported target type.
2. Correct `source`, `confidence_level`, `rule_version` propagation.
3. Stable IDs/references (`target_type`, `target_id`) and workspace/FY scoping.
4. No sensitive document contents leaked in explanation payload.

## API
1. Payload includes explanation objects or sidecar as designed.
2. Existing contracts remain backward compatible.
3. Export preview/readiness/evidence endpoints include correct explanation links.

## Frontend
1. Explanation text renders in Review/Evidence/Readiness/Export surfaces.
2. Confidence badges map correctly.
3. Empty/missing explanation fallback is safe and non-breaking.

## Export package
1. Explanation file exists when enabled.
2. Rule-version fields present where expected.
3. Referential integrity to tax/evidence/readiness entities.

---

## 8) Recommended Implementation Order

1. Define backend explanation templates + service API (no persistence first).
2. Add additive explanation sidecar to Evidence Checklist and Export Eligibility endpoints.
3. Add frontend rendering in Evidence Checklist (lowest ambiguity surface).
4. Extend to Readiness blockers/warnings.
5. Extend to Review item details.
6. Add export package explanation artifact.
7. Optional later: persist explanation snapshots for audit/history.

---

## 9) Backward Compatibility

- Fully additive; no existing field removals.
- Existing readiness/export behavior unchanged.
- Explanation consumers must tolerate missing explanation payloads during rollout.

