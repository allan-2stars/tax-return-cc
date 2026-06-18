# Beta Dry-Run Results

Milestone: 13B-5D  
Purpose: record the aligned backend dry-run harness results and assess whether the harness is trustworthy as an invite-only Beta sign-off gate.

This document is report-only. No runtime behavior was changed.

## Execution

Documented harness command:

```bash
make test-file FILE=tests/integration/test_beta_dry_run.py
```

Summary-capture command used for this report:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend pytest tests/integration/test_beta_dry_run.py -s -v
```

Validation commands run:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend pytest tests/integration/test_beta_dry_run.py -s -v
make test
```

Result:

- Harness status: pass
- Harness tests passed: 9/9
- Scenario cases passed: 8/8
- Coverage guard passed: 1/1
- Full backend suite: 444 passed

## Captured Summaries

```text
BETA_DRY_RUN_SUMMARY {'scenario': 'BETA-001', 'obligations': ['bank_interest_statement'], 'review_items': ['bank_interest', 'payg_income'], 'readiness_state': 'ready', 'journey_state': 'ready', 'review_state': 'ready', 'evidence_state': 'ready', 'export_status': {'can_export': True, 'would_block_export': False}}
BETA_DRY_RUN_SUMMARY {'scenario': 'BETA-002', 'obligations': ['wfh_evidence_log'], 'review_items': ['payg_income', 'wfh_deduction'], 'readiness_state': 'blocked', 'journey_state': 'ready', 'review_state': 'ready', 'evidence_state': 'blocked', 'export_status': {'can_export': True, 'would_block_export': True}}
BETA_DRY_RUN_SUMMARY {'scenario': 'BETA-003', 'obligations': ['wfh_evidence_log'], 'review_items': ['payg_income', 'wfh_deduction'], 'readiness_state': 'blocked', 'journey_state': 'ready', 'review_state': 'ready', 'evidence_state': 'blocked', 'export_status': {'can_export': True, 'would_block_export': True}}
BETA_DRY_RUN_SUMMARY {'scenario': 'BETA-004', 'obligations': ['donation_receipt'], 'review_items': ['donation', 'payg_income'], 'readiness_state': 'blocked', 'journey_state': 'ready', 'review_state': 'ready', 'evidence_state': 'blocked', 'export_status': {'can_export': True, 'would_block_export': True}}
BETA_DRY_RUN_SUMMARY {'scenario': 'BETA-005', 'obligations': ['work_expense_receipt'], 'review_items': ['payg_income', 'work_expense', 'work_expense'], 'readiness_state': 'blocked', 'journey_state': 'ready', 'review_state': 'ready', 'evidence_state': 'blocked', 'export_status': {'can_export': True, 'would_block_export': True}}
BETA_DRY_RUN_SUMMARY {'scenario': 'BETA-006', 'obligations': ['managed_fund_annual_tax_statement', 'managed_fund_capital_gains_schedule', 'managed_fund_foreign_income_support'], 'review_items': ['managed_fund_distribution', 'payg_income'], 'readiness_state': 'blocked', 'journey_state': 'ready', 'review_state': 'ready', 'evidence_state': 'blocked', 'export_status': {'can_export': True, 'would_block_export': True}}
BETA_DRY_RUN_SUMMARY {'scenario': 'BETA-007', 'obligations': ['share_annual_broker_summary', 'share_buy_contract_note', 'share_sell_contract_note'], 'review_items': ['capital_gain', 'payg_income', 'shares_acquisition'], 'readiness_state': 'blocked', 'journey_state': 'ready', 'review_state': 'ready', 'evidence_state': 'blocked', 'export_status': {'can_export': True, 'would_block_export': True}}
BETA_DRY_RUN_SUMMARY {'scenario': 'BETA-008', 'obligations': ['crypto_disposal_supporting_records', 'crypto_exchange_transaction_export', 'crypto_staking_income_statement', 'crypto_wallet_activity_export'], 'review_items': ['capital_loss', 'crypto_acquisition', 'crypto_staking_income', 'payg_income'], 'readiness_state': 'blocked', 'journey_state': 'ready', 'review_state': 'ready', 'evidence_state': 'blocked', 'export_status': {'can_export': True, 'would_block_export': True}}
```

## Scenario Results

## BETA-001: PAYG only with bank interest

- Pass/fail: Pass
- Obligations generated: `bank_interest_statement`
- Review items generated: `bank_interest`, `payg_income`
- Readiness 2.0 state: overall `ready`; journey `ready`; review `ready`; evidence `ready`
- Export eligibility/preview: `can_export=true`; `would_block_export=false`
- Explanation sidecar coverage: deterministic explanation present for `bank_interest`; PAYG remains outside the asserted explanation set
- Mismatch from expected behavior: none that block sign-off; the scenario doc already allows `ready` or `warning` depending policy

## BETA-002: PAYG plus WFH with evidence supplied

- Pass/fail: Pass
- Obligations generated: `wfh_evidence_log`
- Review items generated: `payg_income`, `wfh_deduction`
- Readiness 2.0 state: overall `blocked`; journey `ready`; review `ready`; evidence `blocked`
- Export eligibility/preview: `can_export=true`; `would_block_export=true`
- Explanation sidecar coverage: deterministic explanation present for `wfh_deduction` and WFH obligation
- Mismatch from expected behavior: none; current backend policy keeps required evidence as a blocker until matched/accepted

## BETA-003: PAYG plus WFH with evidence missing

- Pass/fail: Pass
- Obligations generated: `wfh_evidence_log`
- Review items generated: `payg_income`, `wfh_deduction`
- Readiness 2.0 state: overall `blocked`; journey `ready`; review `ready`; evidence `blocked`
- Export eligibility/preview: `can_export=true`; `would_block_export=true`
- Explanation sidecar coverage: deterministic explanation present for `wfh_deduction` and WFH obligation
- Mismatch from expected behavior: none; this was the missing automation gap and is now covered

## BETA-004: PAYG plus donations

- Pass/fail: Pass
- Obligations generated: `donation_receipt`
- Review items generated: `donation`, `payg_income`
- Readiness 2.0 state: overall `blocked`; journey `ready`; review `ready`; evidence `blocked`
- Export eligibility/preview: `can_export=true`; `would_block_export=true`
- Explanation sidecar coverage: deterministic explanation present for `donation` and donation obligation
- Mismatch from expected behavior: none

## BETA-005: PAYG plus work expenses

- Pass/fail: Pass
- Obligations generated: `work_expense_receipt`
- Review items generated: `payg_income`, `work_expense`, `work_expense`
- Readiness 2.0 state: overall `blocked`; journey `ready`; review `ready`; evidence `blocked`
- Export eligibility/preview: `can_export=true`; `would_block_export=true`
- Explanation sidecar coverage: deterministic explanation present for `work_expense` and work-expense obligation
- Mismatch from expected behavior: none

## BETA-006: PAYG plus managed fund

- Pass/fail: Pass
- Obligations generated: `managed_fund_annual_tax_statement`, `managed_fund_capital_gains_schedule`, `managed_fund_foreign_income_support`
- Review items generated: `managed_fund_distribution`, `payg_income`
- Readiness 2.0 state: overall `blocked`; journey `ready`; review `ready`; evidence `blocked`
- Export eligibility/preview: `can_export=true`; `would_block_export=true`
- Explanation sidecar coverage: deterministic explanation present for `managed_fund_distribution` and investment-specific evidence obligation guidance
- Candidate matching coverage: uploaded `managed_fund_annual_tax_statement` creates a candidate match for the annual statement obligation; related capital-gains/foreign-income obligations remain missing until supported evidence is accepted
- Mismatch from expected behavior: none; this now validates the evidence-pipeline path rather than a known rule gap

## BETA-007: PAYG plus shares

- Pass/fail: Pass
- Obligations generated: `share_annual_broker_summary`, `share_buy_contract_note`, `share_sell_contract_note`
- Review items generated: `capital_gain`, `payg_income`, `shares_acquisition`
- Readiness 2.0 state: overall `blocked`; journey `ready`; review `ready`; evidence `blocked`
- Export eligibility/preview: `can_export=true`; `would_block_export=true`
- Explanation sidecar coverage: deterministic explanations present for `shares_acquisition` and `capital_gain`, plus investment-specific evidence guidance
- Candidate matching coverage: uploaded `share_buy_contract_note` and `share_sell_contract_note` create candidate matches for the corresponding obligations; annual broker summary remains a recommended missing obligation in this scenario
- Mismatch from expected behavior: none; evidence is now modeled as a required/recommended obligation set instead of a gap

## BETA-008: PAYG plus crypto

- Pass/fail: Pass
- Obligations generated: `crypto_disposal_supporting_records`, `crypto_exchange_transaction_export`, `crypto_staking_income_statement`, `crypto_wallet_activity_export`
- Review items generated: `capital_loss`, `crypto_acquisition`, `crypto_staking_income`, `payg_income`
- Readiness 2.0 state: overall `blocked`; journey `ready`; review `ready`; evidence `blocked`
- Export eligibility/preview: `can_export=true`; `would_block_export=true`
- Explanation sidecar coverage: deterministic explanation present for `crypto_acquisition` and `capital_loss`; `crypto_staking_income` remains covered by current explanation/fallback behavior alongside investment-specific evidence guidance
- Candidate matching coverage: uploaded `crypto_exchange_transaction_export` creates candidate matches for exchange-export, disposal-support, and staking obligations; wallet export remains a recommended missing obligation in this scenario
- Mismatch from expected behavior: none; this now validates the investment evidence path without requiring parser/extraction support

## Overall Assessment

- Harness execution: Pass
- Scenario-pack conformance: Pass
- Overall automation result: usable as a backend Beta sign-off gate for the currently implemented scenario set

What is now validated well:

- Scenario IDs and names match between the scenario document and the harness
- Both WFH paths are covered:
  - supplied evidence
  - missing evidence
- Required-evidence blocker semantics stay consistent across Readiness 2.0 and export preview
- Explanation sidecars remain present across supported categories
- Export remains soft-blocked by evidence rather than hard-blocked

## Defects Found

## High severity

- None in the aligned harness execution

## Medium severity

- Variant undercoverage remains:
  - shares are still covered as one combined scenario rather than separate buy-only and buy-and-sell variants
  - crypto is still covered as one combined scenario rather than separate buy, sell, and staking variants
- Investment parser/extraction gaps remain even though the obligation/classification/matching pipeline is now present

## Low severity

- `BETA-001` readiness wording is still somewhat loose in the scenario document because implemented policy currently lands on `ready`

## Must Fix Before Invite-Only Beta

- None from this alignment milestone

## Recommended Fixes

- Split shares into explicit buy-only and buy-and-sell automated scenarios if the Beta gate will depend on finer investment-path coverage
- Split crypto into acquisition, disposal, and staking automated scenarios if the Beta gate will depend on per-path coverage instead of a combined investment smoke test
- Add export-artifact assertions in a future milestone if Beta sign-off needs package-content verification rather than only backend domain-state verification

## Remaining Scenario Coverage Gaps

- No dedicated export ZIP artifact validation in the dry-run harness
- No frontend/manual UX validation in the harness
- No separate shares buy-only vs buy-and-sell scenario
- No separate crypto buy vs sell vs staking scenario
- No parser/extraction validation for investment uploads beyond classification and candidate matching

## Production Readiness Estimate

- Previous estimate: 90/100
- Updated estimate after investment evidence refresh: 91/100

Rationale:

- The earlier high-severity trust issue in the automation layer remains resolved.
- The harness now matches the documented scenario map and the shipped investment evidence pipeline.
- Remaining gaps are parser/extraction and scenario-expansion gaps, not sign-off-trust defects.
