# Phase 14A Investment Extraction Coverage Audit

Audit date: 2026-06-18

Scope:

- Share investment document flows
- Managed fund document flows
- Crypto investment document flows
- End-to-end verification across classification, candidate matching, extraction, review, evidence, readiness, and export

This is an audit only. No runtime architecture, schema, API shape, or frontend behavior was changed as part of this document.

## Executive Summary

The current investment pipeline is now structurally sound but uneven in extraction depth.

- **Fully wired through extraction and review**:
  - `share_buy_contract_note`
  - `share_sell_contract_note`
  - `share_dividend_statement`
  - `managed_fund_annual_tax_statement`
- **Partially supported through classification and candidate matching only**:
  - `share_annual_broker_summary`
  - `managed_fund_distribution_statement`
  - `crypto_exchange_transaction_export`
  - `crypto_wallet_activity_export`
  - `crypto_staking_income_statement`
- **Readiness and export evidence impact already work for all investment obligation keys generated in 14A-2A**, because those systems consume `EvidenceObligation` generically.
- **The largest remaining investment gap before Beta RC2 is not evidence generation or matching. It is extraction coverage for the still-partial document types, especially broker summaries and all crypto documents.**

## Coverage Matrix

| Document Type | Classification | Matching | Extraction | Review | Status |
| ------------- | -------------- | -------- | ---------- | ------ | ------ |
| `share_buy_contract_note` | Yes | Yes | Yes | Yes | Fully supported |
| `share_sell_contract_note` | Yes | Yes | Yes | Yes | Fully supported |
| `share_dividend_statement` | Yes | Yes | Yes | Yes | Fully supported |
| `share_annual_broker_summary` | Yes | Yes | No | No | Partially supported |
| `managed_fund_annual_tax_statement` | Yes | Yes | Yes | Yes | Fully supported |
| `managed_fund_distribution_statement` | Yes | Yes | No | No | Partially supported |
| `crypto_exchange_transaction_export` | Yes | Yes | No | No | Partially supported |
| `crypto_wallet_activity_export` | Yes | Yes | No | No | Partially supported |
| `crypto_staking_income_statement` | Yes | Yes | No | No | Partially supported |

## Shares

### `share_buy_contract_note`

Verified:

- Classification vocabulary exists in `backend/app/ai/base.py` and `backend/app/ai/prompts.py`
- Deterministic candidate matching exists in `backend/app/engines/evidence_obligations.py`
- Extraction exists in `backend/app/skills/investment_skill/__init__.py`
- Extraction creates:
  - `event_type = "investment"`
  - `category = "shares_acquisition"`
- Extracted metadata includes:
  - `platform`
  - `stock_code`
  - `exchange`
  - `trade_date`
  - `settlement_date`
  - `units`
  - `price_per_unit`
  - `gross_amount`
  - `brokerage_fee`
  - `transaction_type = "buy"`
- Review integration exists through the standard document extraction pipeline
- Idempotency is covered: reprocessing the same document does not create duplicate events
- Obligation can be satisfied through the existing evidence match accept workflow
- Missing required evidence affects readiness/export through the generic obligation stack

Coverage assessment:

- This is **fully supported for Beta RC2** as an extraction-to-review workflow.

Remaining limitations:

- No parcel model
- No cost-base engine
- No downstream CGT linkage beyond storing acquisition facts

### `share_sell_contract_note`

Verified:

- Classification vocabulary exists
- Deterministic candidate matching exists
- Extraction exists
- Extraction creates:
  - `event_type = "investment"`
  - `category = "capital_gain_candidate"`
- Review item creation is covered by upload pipeline tests
- User can confirm the resulting review item through the normal review flow
- Obligation can be satisfied through the evidence match workflow
- Missing required evidence affects readiness/export

Coverage assessment:

- This is **functionally supported for Beta RC2**, but only as a disposal-fact extraction flow.

Important limitation:

- There is still **no CGT engine**
- No parcel matching
- No cost-base logic
- No final `capital_gain` / `capital_loss` computation from extracted sell notes alone

This is acceptable for RC2 if the product position remains: extraction creates a reviewable disposal candidate, not a finished capital-gains result.

### `share_dividend_statement`

Verified:

- Classification vocabulary exists
- Deterministic candidate matching exists
- Extraction exists
- Extraction creates:
  - `event_type = "investment"`
  - `category = "dividend"`
- Metadata extraction includes:
  - `company_name`
  - `stock_code`
  - `dividend_amount`
  - `franking_credits`
  - `payment_date`
  - `record_date`
  - `shares_held`
  - `currency`
- Review item creation is covered
- Partial extraction still produces a reviewable event when enough facts are present
- Idempotency is covered
- Missing dividend evidence affects readiness/export via obligations

Coverage assessment:

- This is **fully supported for Beta RC2** as a document-to-review workflow.

Remaining limitations:

- No dividend tax engine
- No franking-credit validation
- No registry-level reconciliation across multiple statements

### `share_annual_broker_summary`

Verified:

- Classification vocabulary exists
- Deterministic candidate matching exists
- One uploaded broker summary can create candidate matches for:
  - `share_buy_contract_note`
  - `share_sell_contract_note`
  - `share_dividend_statement`
  - `share_annual_broker_summary`
- Recommended obligation semantics are correct:
  - `share_annual_broker_summary` is recommended, not required
  - It does not create an unexpected hard export block by itself

Confirmed gap:

- No extraction is implemented
- No `TaxEvent` creation
- No `ReviewItem` creation

Coverage assessment:

- **Partially supported**

RC2 blocker assessment:

- **Not a hard RC2 blocker** if RC2 only promises support for contract notes and dividend statements
- **A meaningful usability gap** because broker summaries are common and can carry enough data to reduce manual entry

## Managed Funds

### `managed_fund_annual_tax_statement`

Verified:

- Classification vocabulary exists
- Deterministic candidate matching exists
- Extraction exists
- Extraction creates:
  - `event_type = "investment"`
  - `category = "managed_fund_distribution"`
- Metadata extraction includes:
  - `fund_name`
  - `fund_manager`
  - `distribution_amount`
  - `capital_gains_component`
  - `foreign_income_component`
  - `tfn_withholding`
  - `statement_date`
  - `financial_year`
- Review item creation is covered
- Partial extraction still creates a reviewable event
- Idempotency is covered
- Missing annual statement and component schedules affect readiness/export through required obligations

Coverage assessment:

- This is **fully supported for Beta RC2** as a document-to-review workflow.

Remaining limitations:

- No AMIT engine
- No tax-deferred adjustment logic
- No foreign tax offset calculation
- No managed-fund CGT engine
- Component values remain review metadata, not final tax outcomes

### `managed_fund_distribution_statement`

Verified:

- Classification vocabulary exists
- Deterministic candidate matching exists
- A distribution statement can candidate-match:
  - `managed_fund_annual_tax_statement`
  - `managed_fund_capital_gains_schedule`
  - `managed_fund_foreign_income_support`

Confirmed gap:

- No extraction is implemented
- No `TaxEvent` creation
- No `ReviewItem` creation

Coverage assessment:

- **Partially supported**

RC2 blocker assessment:

- **Not a hard RC2 blocker** if annual tax statements are the supported managed-fund extraction path for RC2
- **Worth scheduling soon**, because users may upload distribution statements instead of annual tax statements

## Crypto

### `crypto_exchange_transaction_export`

Verified:

- Classification vocabulary exists
- Deterministic candidate matching exists
- One exchange export can candidate-match:
  - `crypto_exchange_transaction_export`
  - `crypto_disposal_supporting_records`
  - `crypto_staking_income_statement`
- Missing required evidence affects readiness/export through the obligation engine

Confirmed gap:

- No extraction is implemented
- No `TaxEvent` creation
- No `ReviewItem` creation

Coverage assessment:

- **Partially supported**

### `crypto_wallet_activity_export`

Verified:

- Classification vocabulary exists
- Deterministic candidate matching exists
- Wallet export can candidate-match:
  - `crypto_wallet_activity_export`
  - `crypto_disposal_supporting_records`
- Recommended obligation semantics are already respected through the evidence stack

Confirmed gap:

- No extraction is implemented
- No `TaxEvent` creation
- No `ReviewItem` creation

Coverage assessment:

- **Partially supported**

### `crypto_staking_income_statement`

Verified:

- Classification vocabulary exists
- Deterministic candidate matching exists
- Direct staking statement candidate matching exists
- Missing required evidence affects readiness/export

Confirmed gap:

- No extraction is implemented
- No `TaxEvent` creation
- No `ReviewItem` creation

Coverage assessment:

- **Partially supported**

### Crypto RC2 assessment

Crypto currently has:

- obligation generation
- evidence diagnostics
- candidate matching
- readiness/export evidence impact

Crypto does **not** yet have:

- extraction
- reviewable document-derived events
- wallet reconciliation
- tax-lot engine
- DeFi/NFT handling

RC2 blocker assessment:

- **Not a blocker only if Beta RC2 explicitly positions crypto as evidence-tracked but not extraction-enabled**
- **A blocker if RC2 claims uploaded crypto records will produce review-ready transactions**

## End-to-End Pipeline Assessment

### What is fully covered now

The following document flows are complete enough to support the intended Beta RC2 document pipeline:

- `share_buy_contract_note`
- `share_sell_contract_note`
- `share_dividend_statement`
- `managed_fund_annual_tax_statement`

For these flows, the pipeline is:

`Document -> Classification -> Candidate Match -> Extraction -> TaxEvent -> ReviewItem -> Readiness/Export evidence impact`

### What is only partially covered now

These document types currently stop at:

`Document -> Classification -> Candidate Match`

but do **not** continue into extracted events/review:

- `share_annual_broker_summary`
- `managed_fund_distribution_statement`
- `crypto_exchange_transaction_export`
- `crypto_wallet_activity_export`
- `crypto_staking_income_statement`

## RC2 Blockers

Hard blockers depend on the Beta RC2 promise surface.

### Hard blockers if RC2 claims broad investment document extraction

- Crypto documents do not extract into review items
- Broker summaries do not extract into review items
- Managed fund distribution statements do not extract into review items

### Hard blockers under a narrower RC2 scope

If RC2 scope is explicitly:

- share contract notes
- dividend statements
- managed fund annual tax statements
- evidence generation/matching for other investment documents only

then **no additional hard blocker was identified in the current implementation**.

## RC2 Non-Blockers

The following are important but non-blocking if product positioning remains explicit:

- No CGT engine
- No parcel matching
- No cost-base calculations
- No AMIT engine
- No foreign tax offset calculation for managed funds
- No tax-deferred adjustments
- No broker summary extraction
- No managed fund distribution statement extraction
- No crypto extraction
- No wallet reconciliation
- No DeFi/NFT handling

## Recommended Next Milestone

Recommended next milestone:

`14A-6F Broker Annual Summary Extraction`

Reasoning:

- It extends the already-strong shares path, which is the most mature investment area in the product
- Classification and candidate matching are already in place, so extraction is the next logical step
- Broker summaries can reduce manual share entry substantially without requiring a CGT engine
- It is materially lower risk than starting crypto extraction next

Crypto extraction should remain deferred until:

- share and managed-fund extraction paths are stable in Beta
- the product has a clearer posture for exchange-export parsing and transaction-shape normalization

## Recommendation for Beta RC2 Positioning

The product should describe investment support conservatively:

- **Supported extraction**:
  - share buy contract notes
  - share sell contract notes
  - share dividend statements
  - managed fund annual tax statements
- **Supported evidence tracking and candidate matching only**:
  - share annual broker summaries
  - managed fund distribution statements
  - crypto exports / staking statements

That positioning matches current implementation and avoids over-claiming document automation depth.
