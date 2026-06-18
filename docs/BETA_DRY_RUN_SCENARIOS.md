# Beta Dry-Run Scenario Pack

Milestone: 13B-5A  
Purpose: define end-to-end invite-only Beta validation scenarios for the Australian PAYG workflows currently supported by Tax Return AI.

This document is a test-design artifact only. It does not change runtime behavior.

## Scope And Assumptions

These scenarios validate the integrated product surface after:

- Recovery MVP
- Session Resilience MVP
- Evidence Intelligence
- Readiness 2.0
- Explanation Layer
- Evidence Freshness
- Review Auditability

Core assumptions:

- Each scenario runs in a fresh workspace for the same financial year.
- Testers use synthetic documents only. Do not use real TFNs, account numbers, addresses, recovery keys, or real taxpayer records.
- Evidence matching is deterministic and conservative. Candidate matches should be accepted by the tester when the document clearly satisfies the obligation.
- Evidence can block Readiness 2.0, but export evidence risk remains a soft warning. Export eligibility must not be disabled solely because required evidence is missing or partially matched.
- Existing export hard gates still apply, including incomplete Journey state and unresolved review/export preconditions.
- The product prepares a tax-ready evidence package for review. It does not lodge tax returns and does not provide final tax advice.

## Global Tester Instructions

For each scenario:

1. Create a fresh workspace for the target financial year.
2. Complete the Tax Journey with the listed answers.
3. Upload the listed synthetic documents.
4. Add manual tax items where the scenario requires them.
5. Open Evidence Checklist and run Reconcile/Refresh.
6. Accept candidate evidence matches only when the synthetic document clearly matches the obligation.
7. Open Review and confirm or amend items according to the scenario.
8. Open Readiness and record Journey, Review, and Evidence readiness states.
9. Open Export and record export eligibility plus evidence preview state.
10. Generate an export package only after review actions required by the scenario are complete.
11. Inspect export artifacts listed in this document.

Record actual results, screenshots for UI mismatches, and artifact excerpts for JSON mismatches.

## Global Pass Criteria

The scenario pack passes when every scenario satisfies these global checks:

- No blank page, crash, or unrecoverable loading state appears.
- Session restore, mutation error, draft, and upload interruption UX remain usable during the run.
- Evidence freshness is visible on Evidence Checklist, Readiness, and Export surfaces.
- Review decisions are auditable through item history.
- Bulk review confirmation requires explicit confirmation when used.
- Readiness 2.0 separates Journey, Review, and Evidence states.
- Evidence obligations show required/recommended level, status, reason, rule version, and explanation where supported.
- Export eligibility preserves current hard-gate behavior and shows evidence as a preview/soft warning.
- Export package includes the expected ordered artifacts and does not omit canonical evidence status.

## Global Fail Criteria

Any of these is a scenario failure:

- Journey answer, skip, or edit leaves stale summary data after refresh/reconcile.
- A skipped required Journey question is hidden from incomplete questions.
- Evidence status is stale or failed with no visible explanation.
- A required evidence obligation is missing from the checklist for a supported rule.
- Candidate evidence is shown as verified before user acceptance.
- A review item can be bulk-confirmed without the confirmation dialog.
- A confirmed/amended review item has no visible decision history.
- Export hard-blocks solely because evidence is missing or partially matched.
- Export package omits `05A-EVIDENCE-STATUS.json`.
- Export package omits `04A-REVIEW-ITEMS.json`.

## Expected Export Artifacts

Every generated export package should include at least:

- `00-COVER.pdf`
- `01-TAX-EVENTS.json`
- `02-REVIEW-SUMMARY.pdf`
- `03-MISSING-ITEMS.pdf`
- `04-AI-REASONING.json`
- `04A-REVIEW-ITEMS.json`
- `05-AUDIT-LOG.json`
- `05A-EVIDENCE-STATUS.json`
- `06-SCHEMA-VERSION.txt`
- `07-DISCLAIMER.txt`
- `evidence/manifest.json`
- referenced files under `evidence/` when source documents are included

Artifact checks:

- `04A-REVIEW-ITEMS.json` includes review item explanations where available.
- `05A-EVIDENCE-STATUS.json` is the canonical evidence status artifact.
- `05A-EVIDENCE-STATUS.json` includes evidence summaries, incomplete required/recommended obligations, rule version metadata where available, and obligation explanations.
- Additional compatible artifacts are allowed and should not fail the scenario.

## Scenario Matrix

## BETA-001: PAYG Only With Bank Interest

Purpose: validate the simplest Beta user profile: PAYG income, bank interest, and no deductions.

Uploaded documents:

| Document | Expected classification/use |
| --- | --- |
| Synthetic income statement or PAYG summary | Source for `payg_income` review item |
| Synthetic bank interest statement | Source for `bank_interest` review item and recommended evidence obligation |

Journey answers:

| Question area | Answer |
| --- | --- |
| Employment income | Yes, PAYG employee |
| Bank interest | Yes |
| Work from home | No |
| Donations | No |
| Work expenses | No |
| Investments beyond bank interest | No |
| Private health insurance | No, unless separately tested |

Generated tax events:

| Category | Event type | Expected source |
| --- | --- | --- |
| `payg_income` | `income` | extracted or manually added if extraction is unavailable |
| `bank_interest` | `income` | extracted or manually added |

Expected review items:

- PAYG income item with gross income and tax withheld fields where available.
- Bank interest item with bank name, account type, interest amount, and period fields where available.
- Both items start in a review-required state and can be confirmed.

Expected evidence obligations:

| Obligation | Level | Expected state |
| --- | --- | --- |
| Bank interest statement | recommended | partially matched before acceptance, matched after tester accepts the candidate |

Current known limitation:

- PAYG income evidence is documented as a future explicit rule. Do not fail this scenario solely because no first-class PAYG evidence obligation exists.

Expected readiness state:

- Journey: ready after all required Journey questions are answered.
- Review: warning until review items are confirmed, ready after confirmation.
- Evidence: warning if recommended bank interest evidence is missing or only candidate; ready or warning after accepted match depending current policy.
- Overall Readiness 2.0: not blocked once Journey is complete and only recommended evidence remains.

Expected export eligibility:

- Export may be blocked by unresolved review items before confirmation.
- After review confirmation, export is allowed.
- Evidence preview should show no required evidence blocker.

Expected explanation coverage:

- `bank_interest` explanation renders in Review.
- Bank interest evidence obligation explanation renders in Evidence Checklist.
- Generic safe explanation is acceptable for `payg_income` if no category-specific template exists.

Pass criteria:

- Bank interest appears under Income/All in Review, not Investments-only.
- Bank interest evidence is recommended, not a hard readiness blocker.
- Export package includes both PAYG and bank interest tax events after review confirmation.

Fail criteria:

- Bank interest is hidden from Income review filters.
- Recommended bank interest evidence hard-blocks export.
- Evidence checklist labels candidate bank statement as verified before acceptance.

## BETA-002: PAYG Plus Work From Home - Evidence Supplied

Purpose: validate fixed-rate WFH flow when supporting hours/diary evidence is present.

Uploaded documents:

| Document | Expected classification/use |
| --- | --- |
| Synthetic income statement | PAYG income source |
| WFH diary, timesheet, roster, or hours log | WFH evidence obligation match |

Journey answers:

| Question area | Answer |
| --- | --- |
| Employment income | Yes, PAYG employee |
| Work from home | Yes, regularly |
| WFH days per week | Integer 1..7 |
| WFH method | Fixed rate |
| WFH evidence availability | Evidence supplied |
| Donations/work expenses/investments | No, except PAYG income |

Generated tax events:

| Category | Event type | Expected source |
| --- | --- | --- |
| `payg_income` | `income` | extracted/manual |
| `wfh_deduction` | `deduction` | manual WFH entry or extracted if supported |

Expected review items:

- PAYG income review item.
- WFH candidate deduction review item with method `fixed_rate`, financial year, hours or days basis, and evidence flag metadata.

Expected evidence obligations:

| Obligation | Level | Expected state |
| --- | --- | --- |
| WFH diary/timesheet/hours evidence | required | partially matched before acceptance, matched after tester accepts candidate |

Expected readiness state:

- Journey: ready after WFH follow-up questions are complete.
- Review: warning until PAYG and WFH review items are confirmed.
- Evidence: blocked while WFH evidence is candidate-only if policy treats required candidate as partial; ready after accepted match.
- Overall Readiness 2.0: blocked until required WFH evidence is matched and review work is resolved according to current policy.

Expected export eligibility:

- Evidence export status may show soft-block warning while WFH evidence is partial.
- Export must not be disabled solely by WFH evidence partial/missing state.

Expected explanation coverage:

- `wfh_deduction` explanation renders in Review.
- WFH evidence obligation explanation renders in Evidence Checklist with rule version.

Pass criteria:

- WFH fixed-rate Journey branch does not show irrelevant downstream branch questions.
- WFH obligation is created and matched to the uploaded WFH log.
- Evidence freshness updates after upload/reconcile.

Fail criteria:

- WFH skip/edit state leaves stale WFH answers in summary.
- WFH evidence is absent from Evidence Checklist.
- Readiness shows evidence ready while required WFH evidence is still missing or only rejected.

## BETA-003: PAYG Plus Work From Home - Evidence Missing

Purpose: validate WFH readiness blocker and export soft-warning behavior when evidence is missing.

Uploaded documents:

| Document | Expected classification/use |
| --- | --- |
| Synthetic income statement | PAYG income source |

Journey answers:

- Same as BETA-002, except no WFH evidence is uploaded.

Generated tax events:

- `payg_income`
- `wfh_deduction`

Expected review items:

- PAYG income item.
- WFH candidate deduction item with evidence metadata showing evidence unavailable or not yet supplied.

Expected evidence obligations:

| Obligation | Level | Expected state |
| --- | --- | --- |
| WFH diary/timesheet/hours evidence | required | missing |

Expected readiness state:

- Journey: ready.
- Review: warning until review items confirmed.
- Evidence: blocked with required missing count >= 1.
- Overall Readiness 2.0: blocked because required evidence is missing.

Expected export eligibility:

- Export evidence status `would_block_export` should be true in soft-block mode.
- Export remains allowed if all existing non-evidence hard gates are satisfied.
- Export page warning should direct tester to Evidence Checklist.

Expected explanation coverage:

- WFH review item and WFH obligation both have explanations or safe fallback.

Pass criteria:

- Readiness clearly says evidence is incomplete.
- Export clearly says export is allowed for now but evidence may be incomplete.
- `05A-EVIDENCE-STATUS.json` lists the missing WFH obligation.

Fail criteria:

- Missing WFH evidence is not visible in Readiness or Export preview.
- Missing WFH evidence disables export as a new hard gate.
- Export evidence status omits the missing required obligation.

## BETA-004: PAYG Plus Donations

Purpose: validate donation manual-entry/extraction, receipt obligations, and missing receipt behavior.

Variants:

- BETA-004A: valid receipts supplied.
- BETA-004B: receipts missing.

Uploaded documents:

| Variant | Documents |
| --- | --- |
| 004A | Income statement plus one or more donation receipts |
| 004B | Income statement only |

Journey answers:

| Question area | Answer |
| --- | --- |
| Employment income | Yes |
| Donations | Yes |
| WFH/work expenses/investments | No unless separately tested |

Generated tax events:

| Category | Event type | Expected metadata |
| --- | --- | --- |
| `payg_income` | `income` | payer/gross/tax withheld when available |
| `donation` | `deduction` | charity name, optional ABN, DGR confirmation flag, amount, date, receipt availability, `schema_version` |

Expected review items:

- Donation candidate deduction item for each receipt/manual entry.
- Review item should show explanation and field values.
- If receipt availability is false, item remains review-visible and should not be silently confirmed.

Expected evidence obligations:

| Variant | Obligation | Level | Expected state |
| --- | --- | --- | --- |
| 004A | Donation receipt | required | partially matched before acceptance, matched after acceptance |
| 004B | Donation receipt | required | missing |

Expected readiness state:

- 004A: evidence blocked until candidate receipt is accepted; ready or warning after accepted match and review confirmation.
- 004B: evidence blocked because required donation receipt is missing.

Expected export eligibility:

- 004A: no evidence soft-block after receipt match accepted.
- 004B: evidence soft-block warning, but no evidence hard gate.

Expected explanation coverage:

- `donation` review explanation.
- Donation receipt obligation explanation with rule version.

Pass criteria:

- Donation receipt obligation is created from the donation tax event.
- Missing receipt is shown in Readiness and `05A-EVIDENCE-STATUS.json`.
- Confirm/amend decision history is written for donation review item.

Fail criteria:

- Donation amount <= 0 can be accepted by backend.
- Missing donation receipt is hidden.
- Candidate receipt is displayed as verified before acceptance.

## BETA-005: PAYG Plus Work Expenses

Purpose: validate multiple work expense items, mixed work-related percentages, and receipt matching.

Uploaded documents:

| Document | Expected classification/use |
| --- | --- |
| Synthetic income statement | PAYG income source |
| Laptop receipt | Work expense receipt candidate |
| Professional subscription invoice | Work expense receipt candidate |
| Mobile/internet bill | Work expense receipt candidate |

Journey answers:

| Question area | Answer |
| --- | --- |
| Employment income | Yes |
| Work expenses | Yes |
| WFH | No unless testing combined WFH separately |
| Donations/investments | No |

Generated tax events:

| Category | Event type | Example metadata |
| --- | --- | --- |
| `payg_income` | `income` | payer/gross/tax withheld |
| `work_expense` | `deduction` | expense type `equipment`, vendor, amount, purchase date, work-related percentage 100, receipt available |
| `work_expense` | `deduction` | expense type `subscription`, vendor, amount, purchase date, work-related percentage 100, receipt available |
| `work_expense` | `deduction` | expense type `phone_internet`, vendor, amount, purchase date, work-related percentage 40 or 60, receipt available |

Expected review items:

- One review item per work expense.
- Each review item shows amount and work-related percentage metadata.
- Mixed percentages remain visible for reviewer attention.

Expected evidence obligations:

| Obligation | Level | Expected state |
| --- | --- | --- |
| Receipt/invoice for each work expense | required | matched after candidate acceptance when receipt is supplied |

Expected readiness state:

- Evidence blocked while any required work expense receipt is missing or partial.
- Review warning until all work expense items are confirmed/amended.
- Overall ready only after Journey complete, review resolved, and required receipts accepted.

Expected export eligibility:

- Evidence missing/partial appears in soft-block preview.
- Export button remains governed by existing hard gates.

Expected explanation coverage:

- `work_expense` explanation renders for each review item.
- Work expense receipt obligation explanation renders in checklist.

Pass criteria:

- Work-related percentage validation prevents invalid percentages.
- Required receipt obligations are created for all work expense events.
- Review history captures any amendment to amount/category/note.

Fail criteria:

- Multiple expenses collapse into one ambiguous review item.
- Receipt obligation is not created for work expense.
- A rejected evidence match still satisfies an obligation.

## BETA-006: PAYG Plus Managed Fund

Purpose: validate managed fund distribution metadata, generated evidence obligations, candidate matching, and current parser/extraction limitations.

Uploaded documents:

| Document | Expected classification/use |
| --- | --- |
| Synthetic income statement | PAYG income source |
| Managed fund annual tax statement | Managed fund source document and candidate evidence match for annual statement obligation |

Journey answers:

| Question area | Answer |
| --- | --- |
| Employment income | Yes |
| Investments | Yes |
| Managed fund distributions | Yes |
| Shares/crypto/donations/WFH | No unless separately tested |

Generated tax events:

| Category | Event type | Expected metadata |
| --- | --- | --- |
| `payg_income` | `income` | payer/gross/tax withheld |
| `managed_fund_distribution` | `investment_income` | fund name, optional fund manager, distribution amount, distribution date, capital gains component, foreign income component, TFN withholding |

Expected review items:

- Managed fund distribution review item.
- If capital gains or foreign components are present, item should remain review-visible and may require agent attention depending current policy.

Expected evidence obligations:

| Obligation | Level | Expected state |
| --- | --- | --- |
| Managed fund annual tax statement | required | candidate or partially matched until accepted |
| Managed fund capital gains schedule | required | missing unless the uploaded document supports it and the tester accepts a candidate |
| Managed fund foreign income support | required | missing unless the uploaded document supports it and the tester accepts a candidate |

Expected evidence matching behavior:

- Uploading a document classified as `managed_fund_annual_tax_statement` should create a candidate match for the annual statement obligation.
- Candidate matches remain candidate until the tester accepts them.
- No document parser/extraction exists yet, so the upload does not create or amend TaxEvents automatically.

Expected readiness state:

- Journey ready after investment answers complete.
- Review warning until item confirmed.
- Evidence blocked while required managed fund obligations remain missing or candidate-only.

Expected export eligibility:

- Export allowed after legacy hard gates are satisfied.
- Evidence preview includes managed fund missing/candidate obligations as soft warnings.

Expected explanation coverage:

- `managed_fund_distribution` explanation renders in Review.
- Evidence explanation renders for managed fund obligations and should show investment-specific `What to check` guidance where supported.

Pass criteria:

- Managed fund metadata validates and persists.
- Capital gains and foreign income components remain visible in review/export JSON.
- Export package includes managed fund event, review explanation, and evidence status showing the missing/candidate obligations.

Fail criteria:

- Managed fund event is stored as generic low-confidence without structured metadata.
- Negative distribution components are accepted.
- A managed fund upload is treated as fully matched without user acceptance.
- Export omits the managed fund review item after confirmation.

## BETA-007: PAYG Plus Shares

Purpose: validate share acquisition/disposal semantics, generated evidence obligations, and conservative share evidence candidate matching.

Variants:

- BETA-007A: buy only.
- BETA-007B: buy and sell.

Uploaded documents:

| Variant | Documents |
| --- | --- |
| 007A | Income statement plus share buy contract note |
| 007B | Income statement plus buy and sell contract notes |

Journey answers:

| Question area | Answer |
| --- | --- |
| Employment income | Yes |
| Investments | Yes |
| Shares/ETF | Yes |
| Crypto/managed fund/donations/WFH | No unless separately tested |

Generated tax events:

| Variant | Category | Event type | Expected semantics |
| --- | --- | --- | --- |
| 007A | `shares_acquisition` | `investment_position` | acquisition/non-disposal fact |
| 007B | `shares_acquisition` | `investment_position` | buy-side position fact |
| 007B | `shares_disposal`, `capital_gain`, or `capital_loss` according to current mapping | `investment_position` or `capital` | sell/disposal fact with proceeds/cost basis metadata |

Expected review items:

- Buy-only item label/copy must not imply taxable capital gain.
- Buy-and-sell flow should show disposal outcome for the sell transaction only.
- Review history should record confirm/amend/undo decisions.

Expected evidence obligations:

| Obligation | Level | Expected state |
| --- | --- | --- |
| Share buy contract note | required | candidate or partially matched until accepted |
| Share sell contract note | required | candidate or partially matched until accepted when disposal exists |
| Share annual broker summary | recommended | missing unless a broker summary is uploaded |

Expected evidence matching behavior:

- Uploading a document classified as `share_buy_contract_note` should create a candidate match for the buy obligation.
- Uploading a document classified as `share_sell_contract_note` should create a candidate match for the sell obligation.
- Uploading `share_annual_broker_summary` may create broad candidate matches for buy, sell, dividend, and broker summary obligations when those obligations exist.
- Candidate matches remain candidate until the tester accepts them.
- No parcel-matching, cost-base engine, or parser/extraction logic exists yet.

Expected readiness state:

- Journey ready after investment branch complete.
- Review warning until investment review items are confirmed.
- Evidence blocked while required share obligations remain missing or candidate-only.

Expected export eligibility:

- Export allowed after existing hard gates are satisfied.
- Evidence warning should remain soft at export even when readiness evidence is blocked.

Expected explanation coverage:

- `shares_acquisition` explanation for buy-only item.
- `capital_gain` or `capital_loss` explanation for sell/disposal item where current mapping creates those categories.

Pass criteria:

- Share buy submits/stores acquisition semantics, not capital gain/loss.
- Share sell creates a disposal/capital review item with calculation inputs visible.
- Uploaded buy/sell documents create candidate evidence matches, not auto-accepted matches.
- Export package contains separate acquisition and disposal facts where applicable.

Fail criteria:

- Share buy appears as a capital gain or capital loss.
- Buy-only scenario creates a misleading taxable disposal review item.
- Purchase date after sale date is accepted.
- A share evidence document is treated as matched without explicit acceptance.

## BETA-008: PAYG Plus Crypto

Purpose: validate crypto acquisition/disposal/staking semantics, generated evidence obligations, conservative crypto candidate matching, and current parser/reconciliation limitations.

Variants:

- BETA-008A: crypto buy.
- BETA-008B: crypto sell.
- BETA-008C: crypto staking income.

Uploaded documents:

| Variant | Documents |
| --- | --- |
| 008A | Income statement plus exchange buy receipt or transaction CSV |
| 008B | Income statement plus exchange buy/sell report or transaction CSV |
| 008C | Income statement plus staking rewards statement or exchange CSV |

Journey answers:

| Question area | Answer |
| --- | --- |
| Employment income | Yes |
| Investments | Yes |
| Cryptocurrency | Yes |
| Shares/managed fund/donations/WFH | No unless separately tested |

Generated tax events:

| Variant | Category | Event type | Expected semantics |
| --- | --- | --- | --- |
| 008A | `crypto_acquisition` | `investment_position` | acquisition/non-disposal fact |
| 008B | `crypto_disposal`, `capital_gain`, or `capital_loss` according to current mapping | `investment_position` or `capital` | sell/disposal fact |
| 008C | `crypto_staking_income` | `investment_income` | income fact requiring review |

Expected review items:

- Crypto buy item must not imply taxable capital gain.
- Crypto sell item should show disposal inputs and gain/loss outcome where available.
- Crypto staking item should remain review-visible and may need agent attention under current policy.

Expected evidence obligations:

| Obligation | Level | Expected state |
| --- | --- | --- |
| Crypto exchange transaction export | required | candidate or partially matched until accepted |
| Crypto disposal supporting records | required | candidate or partially matched until accepted when disposal exists |
| Crypto staking income statement | required | candidate or partially matched until accepted when staking exists |
| Crypto wallet activity export | recommended | missing unless a wallet export is uploaded |

Expected evidence matching behavior:

- Uploading a document classified as `crypto_exchange_transaction_export` should create candidate matches for the exchange-export, disposal-support, and staking obligations when those obligations exist.
- Uploading `crypto_wallet_activity_export` may create candidate matches for wallet/disposal obligations.
- Uploading `crypto_staking_income_statement` should create a candidate match for the staking obligation.
- Candidate matches remain candidate until the tester accepts them.
- No crypto parser, wallet reconciliation, DeFi/NFT support, or tax-lot engine exists yet.
- Crypto staking event shape remains known technical debt; coverage depends on the current accepted event shapes.

Expected readiness state:

- Journey ready after crypto branch complete.
- Review warning until crypto review items are confirmed.
- Evidence blocked while required crypto obligations remain missing or candidate-only.

Expected export eligibility:

- Export allowed after existing hard gates are satisfied.
- Evidence warnings remain soft at export even when readiness evidence is blocked.

Expected explanation coverage:

- `crypto_acquisition` explanation for buy-only item.
- `capital_gain` or `capital_loss` explanation for sell/disposal item where current mapping creates those categories.
- `crypto_staking_income` explanation or current generic fallback is acceptable, depending template coverage.
- Evidence explanations should show investment-specific `What to check` guidance where supported.

Pass criteria:

- Crypto buy stores acquisition semantics, not capital gain/loss.
- Crypto sell stores disposal/capital semantics only for the sell event.
- Exchange export upload creates candidate evidence matches but does not auto-create new TaxEvents.
- Coin/token validation prevents invalid symbols.
- Export package includes crypto review items and explanations/fallbacks.

Fail criteria:

- Crypto buy appears as capital gain/loss.
- Staking income is hidden from Review.
- Invalid negative quantities or amounts are accepted.
- A crypto evidence upload is treated as fully matched without explicit acceptance.

## Cross-Scenario Recovery And Session Checks

Run these once during at least two scenarios, preferably BETA-003 and BETA-007B:

| Check | Expected result |
| --- | --- |
| Refresh browser during manual entry before submit | Draft can be restored or discarded |
| Submit manual entry after simulated network/API failure | Error is visible and entered fields remain |
| Upload document and interrupt SSE/polling | Upload UI shows interruption/status-check guidance and continues fallback checking |
| Generate backup before export | Workspace Safety shows recent verified backup status when available |
| Restore preview of a valid backup | Preview reports compatibility without mutating workspace |
| Review confirm then undo | Review item returns to prior status and history records undo |
| Bulk confirm multiple items | Confirmation dialog lists item count/details before action |

## Scenario Result Template

Use this template for each dry run:

```text
Scenario ID:
Workspace/FY:
Tester:
Run date:

Uploaded documents:
Journey answers completed:
Manual items added:

Observed tax events:
Observed review items:
Observed evidence obligations:
Observed readiness_2_0 state:
Observed export eligibility:
Observed export artifacts:

Pass/fail:
Failures:
Screenshots/artifact references:
Notes:
```

## Recommended Execution Order

1. BETA-001 PAYG only with bank interest.
2. BETA-002 WFH with evidence supplied.
3. BETA-003 WFH evidence missing.
4. BETA-004 Donations.
5. BETA-005 Work expenses.
6. BETA-006 Managed fund.
7. BETA-007 Shares.
8. BETA-008 Crypto.

Rationale:

- Start with the simplest PAYG path to validate baseline Journey, Review, Readiness, Export, and artifact generation.
- Validate required evidence blocker behavior before investment complexity.
- Run investment scenarios after core income/deduction paths because their evidence pipeline is now present, but parser/extraction and advanced tax logic are still intentionally limited.

## Beta Exit Criteria For This Pack

The platform is acceptable for invite-only Beta dry-run completion when:

- BETA-001 through BETA-005 pass without critical failures.
- BETA-006 through BETA-008 pass with generated obligations, candidate matching, and clear parser/extraction limitations only.
- No scenario reveals a data-loss, workspace recovery, stale readiness, invisible blocker, or misleading export eligibility defect.
- Export packages are understandable to a reviewer using `04A-REVIEW-ITEMS.json` and `05A-EVIDENCE-STATUS.json`.
- All failures are triaged as either Must Fix Before Beta, Recommended Before Beta, or Post-Beta.

Recommended Beta user profile after this pack:

- Primary: simple PAYG user with bank interest, WFH, donations, and modest work expenses.
- Secondary controlled cohort: PAYG user with managed fund or simple shares/crypto transactions, only if testers understand these scenarios validate the evidence pipeline and review flow, not full investment parser/tax automation.
