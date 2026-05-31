# RELEASE_NOTES_12A.md

## Milestone 12A Audit (12A-1 to 12A-4)

This is an audit-only release note. No runtime behavior was changed in 12A-4.

## 12A Summary

1. **12A-1 (Manual Entry Domain Audit):** identified overuse of generic `description/amount/date` payloads and inconsistent tax semantics.
2. **12A-2 (Schema Design):** introduced [TAX_FACT_SCHEMAS.md](./TAX_FACT_SCHEMAS.md) with category-level contracts and acquisition/disposal correction.
3. **12A-3 implementation slices:**
   - **12A-3A:** deduction templates hardened (`donation`, `work_expense`, `wfh_deduction`) with schema metadata and backend validation.
   - **12A-3B:** investment acquisition semantics corrected (`shares_acquisition`, `crypto_acquisition` for buys).
   - **12A-3C:** bank interest + managed fund hardening.
   - **12A-3D:** foreign income hardening + audit fields.
4. **12A-4 (this doc):** post-implementation audit against design.

---

## Domain-by-Domain Audit

## 1) donation
- **Implemented fields (frontend):** `charity_name`, `abn`, `dgr_confirmed`, `donation_amount`, `donation_date`, `receipt_available`, `note`.
- **Backend validation:** gated on `metadata.schema_version` presence; validates required name/amount/date, boolean flags, ABN format.
- **Frontend validation:** required charity name, amount > 0, valid FY-aware date checks.
- **TaxEvent shape:** `event_type=deduction`, `category=donation`.
- **schema_version behavior:** set to `"2026.1"` by template; legacy generic payload still accepted without schema validation.
- **EvidenceObligation impact:** donation events generate donation receipt obligation (`donation_receipt`).
- **ReviewItem behavior:** created normally, usually `needs_user_review`.
- **Gaps / risks:** schema field naming differs from docs (`recipient_name/is_dgr` in docs vs `charity_name/dgr_confirmed` in code).

## 2) work_expense
- **Implemented fields:** `expense_type`, `vendor`, `amount`, `purchase_date`, `work_related_percentage`, `receipt_available`, `note`.
- **Backend validation:** schema-gated; positive amount, date valid/not-future, percentage 1..100, required booleans.
- **Frontend validation:** required expense_type, amount > 0, valid purchase date, percentage bounds.
- **TaxEvent shape:** `event_type=deduction`, `category=work_expense`.
- **schema_version behavior:** `"2026.1"` emitted; legacy payload accepted.
- **EvidenceObligation impact:** work expense events generate `work_expense_receipt`.
- **ReviewItem behavior:** standard creation, generally `needs_user_review`.
- **Gaps / risks:** docs mention reimbursement fields; not yet modeled in template.

## 3) wfh_deduction
- **Implemented fields:** `method`, `financial_year`, `hours` (fixed rate optional), `amount` (actual cost optional), `evidence_available`, `note`.
- **Backend validation:** schema-gated; method enum, FY required, evidence flag required, positive/non-negative numeric checks.
- **Frontend validation:** method/fy checks; method-specific amount/hours checks.
- **TaxEvent shape:** `event_type=deduction`, `category=wfh_deduction`.
- **schema_version behavior:** `"2026.1"` emitted; legacy payload accepted.
- **EvidenceObligation impact:** WFH obligation currently profile-or-event driven (`wfh_evidence_log`), category recognized.
- **ReviewItem behavior:** standard creation.
- **Gaps / risks:** template still sets event `date` to `today` (synthetic) rather than explicit period/date contract.

## 4) shares_acquisition
- **Implemented fields:** via `SharesForm` buy path metadata (`stock_code`, units, price, brokerage, purchase date, platform/exchange, etc.).
- **Backend validation:** shares metadata validator enforces stock code regex, positive units/prices, non-negative brokerage, date integrity.
- **Frontend validation:** buy/sell/dividend forms validate required numeric/date inputs.
- **TaxEvent shape:** buy now `category=shares_acquisition`, `event_type=investment`; sell remains disposal via capital gain/loss categories.
- **schema_version behavior:** no explicit schema_version emitted for shares forms yet.
- **EvidenceObligation impact:** no dedicated acquisition obligation yet (expected at this stage).
- **ReviewItem behavior:** standard creation.
- **Gaps / risks:** schema-versioning for shares metadata not yet normalized to 2026.1.

## 5) crypto_acquisition
- **Implemented fields:** via `CryptoForm` buy path metadata (`coin`, units, purchase price, fee, purchase date, exchange/wallet, etc.).
- **Backend validation:** crypto validator enforces token regex, positive units/prices, non-negative fee, date integrity.
- **Frontend validation:** buy/sell/staking validation present.
- **TaxEvent shape:** buy now `category=crypto_acquisition`, `event_type=investment`; sell remains disposal (`capital_gain`/`capital_loss`).
- **schema_version behavior:** no explicit schema_version emitted for crypto forms yet.
- **EvidenceObligation impact:** no acquisition-specific rule yet.
- **ReviewItem behavior:** standard creation.
- **Gaps / risks:** schema-versioning missing for crypto metadata; still acceptable but weaker audit traceability.

## 6) bank_interest
- **Implemented fields:** `bank_name`, `account_type`, `interest_amount`, `statement_period_start`, `statement_period_end`, `financial_year`, `in_payg`, `note`.
- **Backend validation:** requires bank/account/amount; validates optional statement period dates and ordering; legacy payload without period still accepted.
- **Frontend validation:** required core fields + required statement period fields in specialized form.
- **TaxEvent shape:** `event_type=investment`, `category=bank_interest`, date uses statement period end.
- **schema_version behavior:** no explicit schema_version in bank-interest metadata.
- **EvidenceObligation impact:** recommended obligation `bank_interest_statement`.
- **ReviewItem behavior:** standard creation.
- **Gaps / risks:** docs specify income semantics (`event_type=income`) but implementation currently uses `investment`.

## 7) managed_fund_distribution
- **Implemented fields:** `fund_name`, `fund_manager`, `distribution_amount`, `capital_gains_component`, `foreign_income_component`, `tfn_withholding`, `distribution_date`, `note`.
- **Backend validation:** strict checks for required fields and non-negative components; date valid/not-future.
- **Frontend validation:** required fund/distribution/date; optional components; review escalation hint for capital gains component.
- **TaxEvent shape:** `event_type=investment`, `category=managed_fund_distribution`.
- **schema_version behavior:** no explicit schema_version emitted.
- **EvidenceObligation impact:** none specific yet.
- **ReviewItem behavior:** can set `needs_agent_review` when capital gains component > 0.
- **Gaps / risks:** lacks explicit schema_version; no dedicated obligation yet (acceptable at this stage).

## 8) foreign_income
- **Implemented fields:** `country`, `income_type`, `foreign_amount`, `currency`, `exchange_rate`, computed `aud_amount`, `income_date`, `foreign_tax_paid`, `fx_source`, `source_document_reference`, `note`.
- **Backend validation:** required country/income_type, positive foreign amount/rate, currency regex, aud consistency (if provided), non-negative foreign tax, optional audit fields length bound, date valid/not-future.
- **Frontend validation:** required core fields; shows computed AUD amount; supports new audit fields; submits schema_version.
- **TaxEvent shape:** `event_type=investment`, `category=foreign_income`.
- **schema_version behavior:** now emits `"2026.1"` from form.
- **EvidenceObligation impact:** none explicit yet.
- **ReviewItem behavior:** submitted with `needs_agent_review`.
- **Gaps / risks:** docs call for richer FX provenance in some cases; current implementation has minimal optional free-text fields only.

---

## Docs vs Code Mismatches

1. **bank_interest event_type mismatch**
   - Docs: `event_type=income`
   - Code: `event_type=investment`
2. **donation/work_expense field naming mismatch**
   - Docs use `recipient_name/is_dgr/work_related_portion_pct` style
   - Code uses `charity_name/dgr_confirmed/work_related_percentage`
3. **schema_version inconsistency**
   - Present for deduction templates + foreign_income
   - Missing for shares/crypto/bank_interest/managed_fund templates.
4. **WFH date semantics**
   - Docs favor explicit period semantics.
   - Code still uses synthetic `today` for event date.

---

## Categories Still Generic (Fallback)

Still largely generic in `ManualEntryForm`:
- Income: `payg_income`, `allowance`, `lump_sum`, `investment_income_basic`
- Deductions: `work_subscription`, `work_equipment`, `vehicle`, `travel`, `uniform`, `self_education`, `other_deduction`
- Investment fallback: `other`

Recommendation: keep as fallback for now, then convert incrementally to tax-specific templates with schema_version emission.

---

## Test Coverage Review

Strong coverage:
- Backend manual-event validation for all audited 12A domains.
- Frontend payload/assertion tests for shares, crypto, bank interest, managed fund, foreign income.

Weak areas:
1. No systematic schema-version assertion coverage for all specialized forms.
2. No explicit test enforcing WFH event-date semantics.
3. Limited end-to-end assertions that review labels for acquisitions avoid taxable-language confusion.
4. Existing warning debt in backend tests (`asyncio.sleep(0)` mocks not awaited) makes signal noisy.

---

## Recommended Next Milestone

**Recommendation: cleanup warning debt first**, then move to **12E Export Eligibility Evidence Preview**.

Rationale:
1. Warning cleanup improves test signal before gating changes.
2. 12A data quality is sufficient to safely surface evidence/export previews.
3. Readiness 2.0 scoring changes should come after export evidence messaging is stable.

---

## Changed files (12A-4)

- `docs/RELEASE_NOTES_12A.md` (new)

