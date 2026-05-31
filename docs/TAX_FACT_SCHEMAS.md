# TAX_FACT_SCHEMAS.md

## Purpose

This document defines tax-fact schemas for manual-entry TaxEvents before UI/form refactors.

Scope is schema design only:
- No runtime behavior changes in this document.
- No readiness/export gating changes.
- No LLM matching changes.

Key correction:
- **Shares buy** and **Crypto buy** are **acquisition/non-disposal** facts, not capital gain/loss facts.
- **Capital gain/loss** facts should come from disposal/sell facts only.

---

## 1) Cross-Cutting Schema Contract

### 1.1 Base TaxEvent envelope (existing)
- `event_type` (string)
- `category` (string)
- `description` (string)
- `amount` (number)
- `date` (YYYY-MM-DD)
- `source = manual_entry`
- `event_metadata` (JSON)
- `status` (`needs_user_review` or `needs_agent_review`)

### 1.2 Metadata versioning
- Use `event_metadata.schema_version` (string), starting with `"2026.1"`.
- Preserve existing rows without `schema_version`.
- New validations apply to new/edited rows for supported categories.

### 1.3 Confidence and fallback
- Generic fallback facts should include:
  - `event_metadata.confidence = "low"`
  - `status = needs_user_review` (or `needs_agent_review` when category is complex)

### 1.4 Shared validation defaults
- Numeric: finite.
- Positive fields: `> 0`.
- Optional fee/tax fields: `>= 0`.
- Max numeric cap: `999_999_999`.
- `description <= 500`, `note <= 5000`.
- Free-text metadata default max: `100` chars unless overridden.
- Date: valid ISO and not future.
- Pair dates: purchase/acquisition must be `<=` disposal date.

---

## 2) Category Schemas

## 2.1 Income

### payg_income
- `event_type`: `income`
- Required metadata:
  - `payer_name`
  - `gross_income`
- Optional metadata:
  - `tax_withheld`
  - `allowances_component`
  - `payment_summary_ref`
- `amount`:
  - gross PAYG amount
- Validation:
  - `gross_income > 0`, `tax_withheld >= 0` if present
- Evidence obligations:
  - recommend PAYG summary/payslip evidence (future explicit rule)
- Review behavior:
  - `needs_user_review` default
- UI fields:
  - payer name, gross income, tax withheld, period/date

### allowance
- `event_type`: `income`
- Required metadata:
  - `allowance_type`
  - `payer_name`
- Optional:
  - `taxed_at_source` (boolean)
- `amount`: allowance amount
- Evidence:
  - recommend payslip/payment summary evidence
- Review:
  - `needs_user_review`
- UI:
  - type, payer, amount, date

### lump_sum
- `event_type`: `income`
- Required metadata:
  - `lump_sum_type`
  - `payer_name`
- Optional:
  - `tax_withheld`
  - `termination_context`
- `amount`: lump sum gross
- Evidence:
  - payout statement required/recommended by subtype
- Review:
  - `needs_agent_review` preferred for complex types
- UI:
  - type, payer, amount, tax withheld, date

### bank_interest
- `event_type`: `income`
- Required metadata:
  - `bank_name`
  - `account_type`
  - `interest_amount`
  - `period_start`
  - `period_end`
- Optional:
  - `in_payg`
  - `account_nickname`
- `amount`: interest amount
- Validation:
  - period_start <= period_end
- Evidence:
  - recommended `bank_interest_statement` (existing rule)
- Review:
  - `needs_user_review`
- UI:
  - bank/account, interest amount, period start/end, duplicate flag

### investment_income_basic
- `event_type`: `income`
- Required metadata:
  - `income_source`
  - `income_subtype`
- Optional:
  - `payer_or_institution`
- `amount`: received amount
- Evidence:
  - recommended statement/notice
- Review:
  - `needs_user_review`
- UI:
  - source, subtype, amount, date

---

## 2.2 Deductions

### donation
- `event_type`: `deduction`
- Required metadata:
  - `recipient_name`
  - `is_dgr` (boolean)
  - `receipt_available` (boolean)
- Optional:
  - `donation_type` (cash/goods)
- `amount`: claim amount
- Evidence:
  - required `donation_receipt` (existing rule)
- Review:
  - `needs_user_review`; escalate if no receipt
- UI:
  - recipient, DGR checkbox, amount, receipt flag/date

### work_expense
- `event_type`: `deduction`
- Required metadata:
  - `expense_type`
  - `work_related_portion_pct` (1..100)
- Optional:
  - `employer_reimbursed` (boolean)
  - `receipt_available` (boolean)
- `amount`: work-related claim amount
- Evidence:
  - required `work_expense_receipt` (existing rule)
- Review:
  - `needs_user_review`, agent-review when ambiguous split
- UI:
  - expense type, total/claim amount, work-use %, reimbursement, receipt/date

### work_subscription
- `event_type`: `deduction`
- Required metadata:
  - `provider_name`
  - `work_related_portion_pct`
- Optional:
  - `billing_period`
- `amount`: deductible component
- Evidence:
  - required work expense receipt/invoice
- Review/UI:
  - same pattern as work_expense

### work_equipment
- `event_type`: `deduction`
- Required metadata:
  - `equipment_type`
  - `work_related_portion_pct`
- Optional:
  - `asset_cost`
  - `depreciation_method_hint`
- `amount`: claim amount for FY
- Evidence:
  - required receipt/invoice
- Review:
  - agent-review for borderline capital/depreciation cases
- UI:
  - equipment type, cost, business-use %, claim amount, purchase date

### vehicle
- `event_type`: `deduction`
- Required metadata:
  - `method` (`cents_per_km` | `logbook`)
  - `work_km` or `logbook_pct` (depending on method)
- Optional:
  - `total_km`
  - `engine_type`
- `amount`: claim amount
- Evidence:
  - required logbook/diary evidence (future rule)
- Review:
  - `needs_agent_review` if insufficient method support
- UI:
  - method selector and method-specific inputs

### travel
- `event_type`: `deduction`
- Required metadata:
  - `travel_type`
  - `work_purpose`
- Optional:
  - `nights`
  - `employer_reimbursed`
- `amount`: claim amount
- Evidence:
  - required receipt/invoice; itinerary optional
- Review/UI:
  - travel purpose, amount, date range

### uniform
- `event_type`: `deduction`
- Required metadata:
  - `uniform_type`
- Optional:
  - `laundry_component`
- `amount`: claim amount
- Evidence:
  - required receipt/laundry records when applicable
- Review/UI:
  - type, amount, date

### self_education
- `event_type`: `deduction`
- Required metadata:
  - `course_name`
  - `provider_name`
  - `work_relevance_reason`
- Optional:
  - `fee_component`
  - `materials_component`
- `amount`: claim amount
- Evidence:
  - required invoice/receipt
- Review:
  - often `needs_agent_review`
- UI:
  - course/provider/relevance/amount/date

### wfh_deduction
- `event_type`: `deduction`
- Required metadata:
  - `method` (`fixed_rate` | `actual_cost`)
  - `hours_or_days_basis`
- Optional:
  - `period_start`, `period_end`
- `amount`: claim amount
- Evidence:
  - required WFH diary/timesheet evidence (existing profile-driven rule; category rule can be added later)
- Review:
  - `needs_user_review`, agent-review for actual-cost complexity
- UI:
  - method, hours/days, amount, period

### other_deduction
- `event_type`: `deduction`
- Required metadata:
  - `deduction_reason`
  - `confidence = low`
- Optional:
  - `supporting_context`
- `amount`: claim amount
- Evidence:
  - recommended receipt/invoice
- Review:
  - `needs_user_review` minimum; `needs_agent_review` for unclear claims
- UI:
  - generic description/amount/date + reason

---

## 2.3 Investment / Capital

### dividend (tax fact)
- `event_type`: `investment_income`
- Required metadata:
  - `company_or_fund`
  - `payment_date`
  - `dividend_amount`
- Optional:
  - `stock_code`
  - `franking_credits`
  - `in_payg`
- `amount`: dividend amount
- Evidence:
  - dividend statement recommended
- Review:
  - `needs_user_review`

### capital_gain (tax fact)
- `event_type`: `capital`
- Required metadata:
  - `asset_class`
  - `disposal_date`
  - `cost_base`
  - `capital_proceeds`
- Optional:
  - `discount_eligible`
  - `calculation_method`
- `amount`: gain amount
- Evidence:
  - disposal + acquisition support evidence recommended/required
- Review:
  - `needs_agent_review` for complex calculations

### capital_loss (tax fact)
- `event_type`: `capital`
- Required metadata same as capital_gain
- `amount`: absolute loss amount (or signed by convention; choose one implementation-wide)
- Review/Evidence:
  - same as capital_gain

### shares_acquisition (new canonical fact; replaces buy-as-capital_gain)
- `event_type`: `investment_position`
- `category`: `shares_acquisition`
- Required metadata:
  - `stock_code`
  - `exchange`
  - `units`
  - `price_per_unit`
  - `brokerage_fee` (default 0)
  - `purchase_date`
- Optional:
  - `platform`
- `amount`: total cost base increment
- Validation:
  - stock code regex `^[A-Z0-9]{1,10}$`, units > 0, price > 0, brokerage >= 0
- Evidence:
  - trade contract note recommended
- Review:
  - `needs_user_review`
- UI:
  - current shares buy form fields retained

### shares_disposal (new canonical fact; sell input)
- `event_type`: `investment_position`
- `category`: `shares_disposal`
- Required metadata:
  - all sell details (stock_code, exchange, units, sale_price_per_unit, purchase_price_per_unit, brokerage_fee, purchase_date, sale_date)
- `amount`: net proceeds
- Validation:
  - purchase_date <= sale_date
- Evidence:
  - disposal contract required/recommended
- Review:
  - `needs_user_review` or `needs_agent_review` for non-ASX/complex

### shares_dividend (canonical, can continue mapping to `dividend`)
- `event_type`: `investment_income`
- `category`: `shares_dividend` (or keep `dividend` with subtype tag)
- Required metadata:
  - company, dividend_amount, payment_date
- Optional:
  - stock_code, franking_credits, in_payg

### crypto_acquisition (new canonical fact; replaces buy-as-capital_gain)
- `event_type`: `investment_position`
- `category`: `crypto_acquisition`
- Required metadata:
  - `coin`, `amount_units`, `purchase_price`, `transaction_fee`, `purchase_date`
- Optional:
  - `exchange`
- Validation:
  - coin regex `^[A-Z0-9]{1,10}$`
- `amount`: cost base increment
- Review:
  - `needs_user_review`

### crypto_disposal (new canonical fact; sell input)
- `event_type`: `investment_position`
- `category`: `crypto_disposal`
- Required metadata:
  - sell and purchase references (coin, units, sale/purchase price, fee, purchase_date, sale_date)
- `amount`: net proceeds
- Review:
  - `needs_user_review` (agent-review for complex basis methods)

### crypto_staking
- `event_type`: `investment_income`
- `category`: `crypto_staking_income`
- Required metadata:
  - `coin`, `income_amount`, `income_date`
- Optional:
  - `platform`
- `amount`: AUD income amount
- Review:
  - `needs_agent_review` default

### managed_fund_distribution
- `event_type`: `investment_income`
- Required metadata:
  - `fund_name`
  - `distribution_amount`
  - `distribution_date`
- Optional:
  - `fund_manager`
  - `capital_gains_component`
  - `foreign_income_component`
  - `tfn_withholding_tax`
- `amount`: distribution_amount
- Evidence:
  - annual tax statement required/recommended
- Review:
  - `needs_user_review`; `needs_agent_review` when capital gains or foreign components present

### foreign_income
- `event_type`: `investment_income`
- Required metadata:
  - `country`
  - `income_type`
  - `foreign_amount`
  - `currency` (3-letter)
  - `exchange_rate`
  - `income_date`
- Optional:
  - `foreign_tax_paid`
- `amount`: AUD converted amount
- Review:
  - `needs_agent_review` default
- Evidence:
  - foreign statement/tax proof recommended/required by subtype

---

## 3) Generic Fallback Schema

Category:
- `manual_generic_fallback` (or existing category with fallback marker)

Metadata:
- `confidence = "low"`
- `raw_user_category`
- `reason_unstructured`

Rules:
- keep allowed for flexibility
- always visible in review
- preferred `needs_agent_review` for high-risk domains

---

## 4) Evidence Obligation Mapping (explicit)

Current explicit mappings:
- `donation` -> required `donation_receipt`
- `work_expense` -> required `work_expense_receipt`
- `bank_interest` -> recommended `bank_interest_statement`
- profile `has_wfh` -> required `wfh_evidence_log`
- profile `has_private_health` -> required `private_health_annual_statement`

Proposed additions after schema rollout:
- shares/crypto disposals -> disposal contract/statement recommended
- managed fund distribution -> annual tax statement recommended/required
- foreign income -> source statement + FX reference recommended/required

---

## 5) Backward Compatibility and Migration Notes

1. Keep existing categories valid and readable.
2. For new canonical categories (`shares_acquisition`, `shares_disposal`, `crypto_acquisition`, `crypto_disposal`):
   - do not rewrite old rows in-place.
   - use `event_metadata.schema_version` and subtype markers for coexistence.
3. Read layer should accept both:
   - legacy (`capital_gain` with shares/crypto buy metadata)
   - canonical acquisition/disposal categories.
4. Review filters should include canonical categories in Investments.
5. Evidence rules should be additive; no deletion of current rules.

---

## 6) Recommended Implementation Order (12A-3+)

1. Backend schema/validator expansion (accept canonical categories + strict subtype validators).
2. Manual-entry form payload updates for shares/crypto buy/sell categories.
3. Review taxonomy updates to include canonical acquisition/disposal categories.
4. Evidence obligation rule additions for newly explicit investment facts.
5. Optional migration utilities/reporting for legacy fact visibility.

---

## 7) Changed-Files Risk Map

High risk:
- `backend/app/engines/review.py` (validation + create_manual_event mapping)
- `backend/app/api/routes/events.py` (request contract)
- `frontend/components/review/ManualEntryForm.tsx`
- `frontend/components/review/investment/SharesForm.tsx`
- `frontend/components/review/investment/CryptoForm.tsx`
- `frontend/lib/api/types.ts`

Medium risk:
- `frontend/app/(dashboard)/review/page.tsx` (category filtering)
- `backend/app/engines/evidence_obligations.py` (new rule triggers)

Low risk:
- `frontend/lib/api/events.ts` (thin transport wrapper)

---

## 8) Test Matrix (planned)

Backend tests:
1. Manual event validation by category:
   - required fields, numeric bounds, date constraints, regex constraints.
2. Canonical mapping:
   - shares/crypto buy create acquisition categories, not capital_gain.
   - shares/crypto sell map to disposal; gain/loss only for disposal-derived facts.
3. Backward compatibility:
   - legacy rows still load and remain reviewable.
4. Evidence mapping:
   - donation/work_expense/bank_interest unchanged.
   - new categories produce expected (additive) obligations when implemented.

Frontend tests:
1. Form field rendering by category/template.
2. Payload shape per template (including metadata + schema_version).
3. Shares/Crypto buy no longer submits `capital_gain` category.
4. Review tab includes new canonical investment categories.
5. Generic fallback emits low-confidence metadata.

