# Phase 14A Investment Coverage Audit

Audit date: 2026-06-11

Scope:

- Managed Funds
- Shares
- Crypto

This is an audit only. No runtime behavior, schema, API, or frontend behavior was changed as part of this document.

## Executive Summary

The current investment foundation is uneven:

- **Managed Funds** and **Shares** have meaningful **manual-entry and review-validation coverage**, but almost no investment-specific **evidence obligation** or **readiness** coverage.
- **Crypto** has manual-entry support plus a registered backend skill, but the skill is currently a **stub** and does not add questions, evidence rules, extraction, or readiness coverage.
- The system is currently strongest at **capturing investment items as manual `TaxEvent`s** and routing them into **Review**.
- The system is weakest at **evidence expectations**, **readiness blocking**, and **document/extraction support** for investment workflows.

In practice, Beta RC1 can record investment events, but it does not yet provide investment-grade evidence/readiness safeguards.

---

## Managed Funds

### Current state

#### Interview questions

- No dedicated managed-fund interview questions were found in [`backend/app/engines/interview.py`](../backend/app/engines/interview.py).
- No managed-fund questions are provided by a skill.
- The Journey does not currently collect:
  - whether the user had managed fund distributions
  - whether an annual tax statement exists
  - whether the distribution included capital gains / foreign income / tax deferred components

#### Income/event model

- Manual managed-fund entry exists in [`frontend/components/review/investment/ManagedFundForm.tsx`](../frontend/components/review/investment/ManagedFundForm.tsx).
- It creates a manual event through [`backend/app/api/routes/events.py`](../backend/app/api/routes/events.py) with:
  - `event_type = "investment"`
  - `category = "managed_fund_distribution"`
- Backend validation exists in [`backend/app/engines/review.py`](../backend/app/engines/review.py):
  - `_validate_managed_fund_metadata()`
- Captured metadata today:
  - `fund_name`
  - `fund_manager`
  - `distribution_amount`
  - `capital_gains_component`
  - `foreign_income_component`
  - `tfn_withholding`
  - `distribution_date`

#### Evidence obligation generation

- No managed-fund obligation rule exists in [`backend/app/engines/evidence_obligations.py`](../backend/app/engines/evidence_obligations.py).
- Integration dry-run explicitly records this as a known gap:
  - `known_gap_obligation_keys={"managed_fund_statement"}` in [`backend/tests/integration/test_beta_dry_run.py`](../backend/tests/integration/test_beta_dry_run.py).

#### Evidence matching

- No managed-fund document matching rule exists in [`backend/app/engines/evidence_obligations.py`](../backend/app/engines/evidence_obligations.py).
- AI document classification is generic and currently only supports coarse document types like `payg_summary|bank_statement|receipt|invoice|csv|other|unknown` in [`backend/app/ai/prompts.py`](../backend/app/ai/prompts.py).
- There is no managed-fund-specific document type or parser path.

#### Readiness logic

- No managed-fund evidence requirement exists in:
  - [`backend/app/engines/evidence_obligations.py`](../backend/app/engines/evidence_obligations.py)
  - [`backend/app/engines/readiness.py`](../backend/app/engines/readiness.py)
- Result:
  - a managed-fund scenario can be `journey=ready`, `review=ready`, `evidence=ready` with no managed-fund statement obligation at all.
- This is confirmed in [`backend/tests/integration/test_beta_dry_run.py`](../backend/tests/integration/test_beta_dry_run.py) scenario `BETA-006`.

#### Export logic

- Managed-fund events are exported only as generic tax events/review items in [`backend/app/engines/export.py`](../backend/app/engines/export.py).
- No managed-fund-specific export section, breakdown, or evidence warning exists.
- Explanation coverage exists in [`backend/app/services/explanations.py`](../backend/app/services/explanations.py) for `managed_fund_distribution`.

### Missing capabilities

- No managed-fund interview capture
- No managed-fund skill ownership
- No managed-fund evidence obligation
- No managed-fund document matching
- No managed-fund extraction path from uploaded statements
- No managed-fund readiness blocker/warning
- No distinction between:
  - gross distribution
  - capital gains discount method
  - foreign tax offsets / foreign tax credits
  - tax deferred / tax free / AMIT cost-base adjustments
  - franking credits embedded in fund distributions

### Missing validation

Current validation is only structural. It does **not** validate:

- that component totals reconcile to the distribution
- that the annual tax statement financial year matches `Workspace.financial_year`
- that capital-gains component implies downstream capital-gains evidence requirements
- that foreign-income component implies foreign-tax evidence expectations

### Missing readiness checks

- No required statement check for annual managed fund tax statement
- No warning when capital gains component exists without supporting statement
- No warning when foreign-income component exists without source statement / tax offset evidence
- No warning when TFN withholding is present without statement support

### Recommended obligations

1. `managed_fund_annual_tax_statement`
   - required when `managed_fund_distribution` exists
2. `managed_fund_capital_gains_schedule`
   - required when `capital_gains_component > 0`
3. `managed_fund_foreign_income_support`
   - required when `foreign_income_component > 0`
4. `managed_fund_tfn_withholding_support`
   - recommended or required when `tfn_withholding > 0`

### Recommended evidence types

- managed fund annual tax statement
- fund distribution tax breakdown
- annual investor statement
- platform-generated tax pack / annual tax report

### Recommended readiness checks

- Block readiness if `managed_fund_distribution` exists and no annual tax statement obligation is matched
- Warn when distribution contains capital-gains component but no capital-gains schedule evidence
- Warn when foreign-income component exists but no foreign-income support is matched
- Carry these obligations into export warnings

---

## Shares

### Current state

#### Interview questions

- No dedicated shares interview questions were found in [`backend/app/engines/interview.py`](../backend/app/engines/interview.py).
- No shares skill is registered in [`backend/app/skills/registry.py`](../backend/app/skills/registry.py).
- The Journey does not currently ask:
  - whether the user bought or sold shares
  - whether they received dividends
  - whether they have contract notes, broker summaries, or registry statements

#### Acquisition handling

- Manual share buy flow exists in [`frontend/components/review/investment/SharesForm.tsx`](../frontend/components/review/investment/SharesForm.tsx).
- It creates:
  - `event_type = "investment"`
  - `category = "shares_acquisition"`
- Backend validation exists in [`backend/app/engines/review.py`](../backend/app/engines/review.py):
  - `_validate_shares_metadata()` for `transaction_type == "buy"`
- Captured fields:
  - `platform`
  - `stock_code`
  - `exchange`
  - `units`
  - `price_per_unit`
  - `brokerage_fee`
  - `purchase_date`

#### Disposal handling

- Manual share sell flow exists in [`frontend/components/review/investment/SharesForm.tsx`](../frontend/components/review/investment/SharesForm.tsx).
- It creates:
  - `category = "capital_gain"` or `category = "capital_loss"` based on a simple frontend estimate
- Captured fields:
  - `platform`
  - `stock_code`
  - `exchange`
  - `units`
  - `sale_price_per_unit`
  - `purchase_price_per_unit`
  - `brokerage_fee`
  - `sale_date`
  - `purchase_date`
- Frontend helper [`frontend/lib/utils/investment.ts`](../frontend/lib/utils/investment.ts) only computes:
  - day count
  - simple `>= 365 days` CGT discount hint

#### Dividend handling

- Manual dividend flow exists in [`frontend/components/review/investment/SharesForm.tsx`](../frontend/components/review/investment/SharesForm.tsx).
- It creates:
  - `category = "dividend"`
- Captured fields:
  - `company_name`
  - `stock_code`
  - `dividend_amount`
  - `franking_credits`
  - `payment_date`
  - `in_payg`

#### Capital gains handling

- There is no dedicated backend capital-gains engine.
- Share sell events are represented as generic `capital_gain` / `capital_loss` `TaxEvent`s.
- Validation is input-level only in [`backend/app/engines/review.py`](../backend/app/engines/review.py); there is no tax-logic layer for:
  - parcel selection
  - partial disposal matching
  - cost-base adjustments
  - dividend reinvestment implications
  - scrip-for-scrip or corporate actions

#### Evidence matching

- No shares obligation rules exist in [`backend/app/engines/evidence_obligations.py`](../backend/app/engines/evidence_obligations.py).
- Integration dry-run explicitly records:
  - `known_gap_obligation_keys={"share_contract_note"}` in [`backend/tests/integration/test_beta_dry_run.py`](../backend/tests/integration/test_beta_dry_run.py).
- No matching exists for:
  - contract notes
  - broker annual summaries
  - dividend statements
  - share registry reports

#### Readiness logic

- No shares-specific evidence rules feed readiness.
- A shares scenario can therefore reach evidence/readiness `ready` with no contract notes or dividend statements matched.
- This is confirmed in `BETA-007` in [`backend/tests/integration/test_beta_dry_run.py`](../backend/tests/integration/test_beta_dry_run.py).

#### Export logic

- Shares data exports only through generic event/review payloads in [`backend/app/engines/export.py`](../backend/app/engines/export.py).
- No share-specific evidence completeness or capital-gains support warnings are added.
- Explanation coverage exists for:
  - `shares_acquisition`
  - `capital_gain`
  - `capital_loss`
  in [`backend/app/services/explanations.py`](../backend/app/services/explanations.py).

### Missing capabilities

- No shares interview discovery
- No shares skill ownership
- No evidence obligations for:
  - buy contract note
  - sell contract note
  - dividend statement
  - annual broker / registry summary
- No statement extraction for broker or registry reports
- No backend capital-gains calculation/cost-base model
- No holding-parcel linkage between acquisitions and disposals

### Missing validation

Current validation does **not** cover:

- partial parcel disposals
- multiple acquisition lots
- DRP / bonus issues / splits / consolidations
- foreign share FX normalization
- dividend franking-credit reasonableness
- consistency between acquisition records and disposal units

### Missing readiness checks

- No required evidence for share acquisitions/disposals
- No required evidence for dividend statements
- No warning when `capital_gain` / `capital_loss` exists without acquisition support
- No warning when `dividend` exists without dividend statement / annual summary

### Recommended obligations

1. `share_buy_contract_note`
   - required when `shares_acquisition` exists
2. `share_sell_contract_note`
   - required when `capital_gain` or `capital_loss` from shares exists
3. `share_dividend_statement`
   - required when `dividend` exists
4. `share_annual_broker_summary`
   - recommended when any shares activity exists
5. `share_registry_tax_statement`
   - recommended for dividend-heavy / registry-driven holdings

### Recommended evidence types

- broker contract note
- sell contract note
- annual broker transaction summary
- dividend statement
- share registry annual tax statement

### Recommended readiness checks

- Block readiness on missing buy/sell contract notes for share CGT events
- Warn when dividend exists with no dividend statement evidence
- Warn when acquisition/disposal dates or units imply incomplete parcel support

---

## Crypto

### Current state

#### Interview questions

- No dedicated crypto interview questions are defined in [`backend/app/engines/interview.py`](../backend/app/engines/interview.py).
- `crypto_skill_au` is registered in [`backend/app/skills/registry.py`](../backend/app/skills/registry.py) and can activate from `TaxProfile.has_crypto`.
- But the skill currently returns **no questions** in [`backend/app/skills/crypto_skill_au/__init__.py`](../backend/app/skills/crypto_skill_au/__init__.py).
- The only Journey-adjacent crypto guidance is a next-step hint in [`frontend/components/interview/NextStepsList.tsx`](../frontend/components/interview/NextStepsList.tsx):
  - “Export your crypto transaction history”

#### Acquisition handling

- Manual crypto buy flow exists in [`frontend/components/review/investment/CryptoForm.tsx`](../frontend/components/review/investment/CryptoForm.tsx).
- It creates:
  - `event_type = "investment"`
  - `category = "crypto_acquisition"`
- Backend validation exists in [`backend/app/engines/review.py`](../backend/app/engines/review.py):
  - `_validate_crypto_metadata()` for `transaction_type == "buy"`
- Captured fields:
  - `exchange`
  - `coin`
  - `amount_units`
  - `purchase_price`
  - `transaction_fee`
  - `purchase_date`

#### Disposal handling

- Manual crypto sell flow exists in [`frontend/components/review/investment/CryptoForm.tsx`](../frontend/components/review/investment/CryptoForm.tsx).
- It creates:
  - `category = "capital_gain"` or `category = "capital_loss"` using simple frontend math
- Captured fields:
  - `exchange`
  - `coin`
  - `amount_units`
  - `sale_price`
  - `purchase_price`
  - `transaction_fee`
  - `sale_date`
  - `purchase_date`
  - `cost_basis_method`

#### Exchange statement support

- CSV ingestion exists generically in [`backend/app/engines/evidence.py`](../backend/app/engines/evidence.py), but the parser registry in [`backend/app/constants/csv_parsers.py`](../backend/app/constants/csv_parsers.py) only supports bank CSV layouts plus a stub `COINSPOT` hint.
- AI classification only recognizes coarse document types like `csv`, not `crypto_exchange_statement`, in [`backend/app/ai/prompts.py`](../backend/app/ai/prompts.py).
- `crypto_skill_au.extract_events()` currently returns an empty list in [`backend/app/skills/crypto_skill_au/__init__.py`](../backend/app/skills/crypto_skill_au/__init__.py).
- Result: uploaded crypto exchange exports do not currently produce crypto tax events through the document pipeline.

#### Wallet export support

- No wallet export parser was found.
- No wallet-specific obligation or matching rule was found.
- “wallet activity export” appears only as explanation text in [`backend/app/services/explanations.py`](../backend/app/services/explanations.py), not as implemented matching logic.

#### Readiness logic

- `crypto_skill_au.get_evidence_requirements()` returns an empty list in [`backend/app/skills/crypto_skill_au/__init__.py`](../backend/app/skills/crypto_skill_au/__init__.py).
- No crypto obligation rules exist in [`backend/app/engines/evidence_obligations.py`](../backend/app/engines/evidence_obligations.py).
- Integration dry-run explicitly records:
  - `known_gap_obligation_keys={"crypto_exchange_statement"}` in [`backend/tests/integration/test_beta_dry_run.py`](../backend/tests/integration/test_beta_dry_run.py).
- A crypto scenario can therefore reach readiness with no exchange export or wallet activity evidence at all.

#### Evidence matching

- No crypto evidence obligation or matching rules currently exist.
- No exchange CSV / wallet export document-type normalization currently exists.
- No reconcile path links crypto events to exchange exports or wallet exports.

#### Export logic

- Crypto events export only through generic event/review payloads in [`backend/app/engines/export.py`](../backend/app/engines/export.py).
- No export warning is added for missing transaction-history evidence.

### Missing capabilities

- Crypto skill is registered but functionally stubbed
- No crypto interview capture beyond generic `has_crypto` activation
- No extraction from exchange CSV/PDF uploads
- No wallet export ingestion
- No staking/reward document matching
- No evidence obligations for transaction-history completeness
- No readiness blocker for missing exchange export / wallet export

### Missing validation

Manual-entry validation does **not** cover:

- transfers between wallets/exchanges
- swaps / token-to-token disposals
- staking reward source evidence
- NFT / DeFi / liquidity pool / wrapped asset cases
- disposal/acquisition lot matching beyond a single purchase-price input
- consistency between `amount_units` and cost-basis selection across multiple lots

### Missing readiness checks

- No required exchange statement / transaction export check
- No required wallet export check where self-custody activity exists
- No warning when capital gain/loss exists without acquisition/disposal source records
- No warning when staking income exists without activity/export evidence

### Recommended obligations

1. `crypto_exchange_transaction_export`
   - required when exchange-based crypto activity exists
2. `crypto_wallet_activity_export`
   - required when wallet/self-custody activity exists
3. `crypto_disposal_supporting_records`
   - required when `capital_gain` / `capital_loss` from crypto exists
4. `crypto_staking_income_statement`
   - required when staking/reward income exists

### Recommended evidence types

- exchange CSV export
- exchange annual tax report
- wallet activity export
- transaction ledger export
- staking reward report

### Recommended readiness checks

- Block readiness when crypto disposal exists without exchange/wallet transaction history
- Warn when staking income exists without staking statement/export
- Warn when crypto acquisition/disposal mix implies incomplete source coverage

---

## Cross-cutting findings

### 1. Manual-entry coverage is ahead of evidence coverage

Evidence for investment categories is far behind manual event creation:

- review validation exists for managed funds, shares, crypto, bank interest, foreign income
- obligation generation currently covers only:
  - private health
  - WFH
  - donations
  - work expenses
  - bank interest

Key file:
- [`backend/app/engines/evidence_obligations.py`](../backend/app/engines/evidence_obligations.py)

### 2. There is no investment skill except crypto, and crypto is stubbed

- No `investment_skill` implementation exists.
- The AI prompt still mentions `investment_skill` as a possible classifier output in [`backend/app/ai/prompts.py`](../backend/app/ai/prompts.py), but the registry only loads:
  - `employee_tax_au`
  - `crypto_skill_au`
- This is a correctness gap between prompt vocabulary and real runtime behavior.

### 3. Readiness currently underestimates investment evidence risk

- Readiness 2.0 relies on evidence obligations plus incomplete Journey state in [`backend/app/api/routes/readiness.py`](../backend/app/api/routes/readiness.py).
- Because investment obligations mostly do not exist yet, investment-heavy workspaces can appear artificially ready.

### 4. Export currently relies on generic event presence, not investment evidence sufficiency

- Export eligibility only blocks on evidence obligations already generated in [`backend/app/services/export_eligibility.py`](../backend/app/services/export_eligibility.py).
- Missing investment obligations means export warning/blocking is currently incomplete for managed funds, shares, and crypto.

---

## Risk assessment

### Highest risk

1. **Crypto**
   - Highest correctness risk
   - Registered skill exists but does nothing
   - Upload pipeline does not turn crypto exchange exports into crypto events
   - No evidence or readiness protection for transaction-history completeness

2. **Shares**
   - High evidence risk
   - Manual event support exists, but there is no contract-note / dividend-statement obligation coverage
   - Capital gains are modeled as simple events without backend lot/cost-base support

3. **Managed Funds**
   - Medium-to-high evidence risk
   - Distribution capture exists, but annual tax statement support is not enforced
   - Component-specific readiness is absent

### Lower relative risk

- **Bank interest** and **foreign income** already have partial foundations:
  - bank interest has evidence obligations and matching
  - foreign income has manual-entry validation but still no obligation layer

---

## Recommended implementation order

1. **Crypto evidence foundations**
   - Add crypto evidence obligations and readiness checks first
   - Reason: highest mismatch between supported UI and actual evidence correctness

2. **Shares evidence foundations**
   - Add contract note / dividend statement obligations and readiness checks
   - Reason: share CGT/dividend flows are already user-visible and likely common

3. **Managed fund evidence foundations**
   - Add managed fund annual statement obligation and capital-gains/foreign-income warnings
   - Reason: moderate complexity, but still important for evidence correctness

4. **Document classification + parser uplift**
   - Add investment document types and exchange/broker parsing support
   - Reason: needed after obligation semantics are defined

5. **Deeper tax-logic enhancements**
   - parcel matching
   - multi-lot cost-base handling
   - wallet/exchange reconciliation
   - managed-fund component normalization

---

## Recommended next milestone: 14A-2

### 14A-2 — Investment Evidence Obligations Foundation

Recommended scope:

1. Add deterministic `EvidenceObligation` generation for:
   - managed fund annual tax statement
   - share buy contract note
   - share sell contract note
   - share dividend statement
   - crypto exchange transaction export
   - crypto wallet activity export
   - crypto staking income statement

2. Add deterministic candidate matching for obvious document types where already available.

3. Add readiness 2.0 and export-eligibility integration for these new obligations.

4. Keep this phase **evidence/readiness first**.
   - Do **not** yet redesign manual-entry forms
   - Do **not** yet build full parser/lot-accounting logic
   - Do **not** yet change workspace/Journey architecture

### Why 14A-2 should come next

This gives the product immediate correctness value:

- better readiness truthfulness
- better evidence guidance
- safer export warnings
- no redesign of stable beta systems

It also preserves the current architecture:

- Workspace owns FY
- Journey remains the context layer
- Evidence remains deterministic
- Review remains the manual correction surface

