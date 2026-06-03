# Beta Dry-Run Execution Guide

Milestone: 13B-5B  
Purpose: explain how to run and interpret the automated backend dry-run harness for the scenarios defined in `docs/BETA_DRY_RUN_SCENARIOS.md`.

This document is operational guidance only. It does not change runtime behavior.

## Harness Location

Automated backend harness:

- `backend/tests/integration/test_beta_dry_run.py`

The harness seeds synthetic workspaces and validates the domain outputs for:

- PAYG only with bank interest
- PAYG plus WFH
- PAYG plus donations
- PAYG plus work expenses
- PAYG plus managed fund
- PAYG plus shares
- PAYG plus crypto

## What The Harness Validates

For each scenario, the test creates:

- a fresh workspace
- a tax profile
- a completed interview session
- synthetic ready documents
- tax events
- review items
- evidence obligations and matches through reconciliation

Then it validates:

- Journey state through `readiness_2_0.journey`
- Evidence obligations through `EvidenceObligation`
- Review items through `ReviewItem`
- Readiness state through `readiness_2_0`
- Export hard eligibility through `ExportEngine.check_eligibility`
- Export evidence preview through `ExportEligibilityService`
- deterministic explanation sidecars through `app.services.explanations`

## What The Harness Does Not Do

The harness intentionally does not:

- run OCR or document extraction
- exercise frontend flows
- generate export ZIP files
- mutate production runtime behavior
- require real taxpayer data
- verify unsupported future evidence rules for managed funds, shares, or crypto

Those gaps are covered by manual dry-run execution or future automation milestones.

## Running The Harness

Run the specific dry-run harness:

```bash
make test-file FILE=tests/integration/test_beta_dry_run.py
```

Run the full backend suite:

```bash
make test
```

The harness prints one summary line per scenario:

```text
BETA_DRY_RUN_SUMMARY {
  'scenario': 'BETA-001',
  'obligations': [...],
  'review_items': [...],
  'readiness_state': 'ready',
  'export_status': {'can_export': True, 'would_block_export': False}
}
```

Use these summaries as a quick operator-facing validation report. Pytest captures output by default; run with the project-supported verbose/no-capture option if detailed summaries are needed during manual investigation.

## Expected Known Gaps

The following are intentional known gaps in the current evidence-rule set:

- Managed fund annual tax statement obligation
- Share/ETF trade contract note obligation
- Crypto exchange report obligation

The harness asserts these obligations are not accidentally treated as implemented. The scenarios still validate that the related tax events, review items, export eligibility, and explanation sidecars remain visible.

## Failure Triage

Classify failures as follows:

- Must Fix Before Beta: stale Journey/Readiness state, missing supported obligations, missing review items, broken export eligibility, missing explanations for supported categories.
- Recommended Before Beta: scenario summary output is unclear, unsupported investment evidence rules need stronger reporting.
- Post-Beta: broader extraction coverage, additional investment evidence rules, full export ZIP verification for every dry-run scenario.

## Relationship To Manual Dry Runs

The automated harness is a repeatable backend safety check. It does not replace the manual scenario pack.

Manual dry runs should still verify:

- upload UX
- evidence freshness badges
- Review history and undo UI
- Readiness page copy
- Export page copy
- generated export ZIP contents
- Workspace Safety recovery UX

Use `docs/BETA_DRY_RUN_SCENARIOS.md` as the source of truth for manual tester instructions.
