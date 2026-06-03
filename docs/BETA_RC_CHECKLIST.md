# Invite-only Beta RC Checklist

Milestone: 13B-6A  
Purpose: provide the final release-candidate checklist for deciding whether Tax Return AI is ready for invite-only Beta.

This document is decision support only. No runtime behavior changes are included.

## 1. Beta Blocker Status

| Area | Status | Evidence | Residual Risk | RC Decision |
| --- | --- | --- | --- | --- |
| Recovery | Resolved at MVP level | `RECOVERY_MVP_ACCEPTANCE.md` | Medium | Pass with operator guidance |
| Session resilience | Resolved at MVP level | `SESSION_RESILIENCE_ACCEPTANCE.md` | Medium | Pass |
| Evidence freshness | Resolved at MVP level | `EVIDENCE_FRESHNESS_ACCEPTANCE.md` | Medium | Pass |
| Review auditability | Resolved at MVP level | `REVIEW_AUDITABILITY_ACCEPTANCE.md` | Low/Medium | Pass |
| Dry-run harness trust | Resolved for current backend sign-off scope | `BETA_DRY_RUN_RESULTS.md` | Medium | Pass |

Summary:

- The original top Beta blockers for recovery, session resilience, evidence freshness, review auditability, and dry-run harness trust are now addressed well enough for invite-only Beta.
- Residual risk remains in scope-gating, policy clarity, and domain coverage breadth rather than core platform stability for the supported cohort.

## 2. Current Test Baseline

## Backend

- Latest full backend baseline: `make test`
- Result: 378 passed
- Includes:
  - recovery tests
  - evidence freshness tests
  - review auditability tests
  - migration regression tests
  - dry-run harness tests

## Frontend

- Latest recorded frontend baseline: `make test-fe`
- Result: 61 suites passed, 436 tests passed
- Source: `REVIEW_AUDITABILITY_ACCEPTANCE.md`

## Dry-run Harness

- Latest harness baseline:
  - `make test-file FILE=tests/integration/test_beta_dry_run.py`
  - `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend pytest tests/integration/test_beta_dry_run.py -s -v`
- Result: 9 passed
- Scenario cases: 8/8 passed
- Coverage guard: 1/1 passed

## 3. Remaining Must Fix Before Invite-only Beta

These are the remaining items that should be treated as Beta conditions rather than optional polish:

1. Scope gating for unsupported tax domains
   - Property-heavy, sole-trader-heavy, and advanced CGT edge cases must be explicitly excluded or warned before users rely on the platform.

2. Readiness vs export policy copy consistency
   - Users can still see blocked readiness alongside export soft-block messaging.
   - This is an intentional policy split, but the language must stay explicit and consistent across Journey, Readiness, and Export.

3. Beta operations discipline for recovery
   - Every Beta workspace should have a recent verified backup path and operators should know how to preview and restore before onboarding real user data.

If those conditions are not enforced operationally and in-product, the Beta recommendation should be downgraded.

## 4. Remaining Recommended Before Invite-only Beta

1. Split shares into buy-only and buy-plus-sell dry-run scenarios.
2. Split crypto into buy, sell, and staking dry-run scenarios.
3. Improve explicit support messaging for managed fund, shares, and crypto evidence-rule gaps.
4. Add a consolidated accountant handoff index artifact in export.
5. Tighten mobile/tablet ergonomics for long review and evidence lists.
6. Expand structured manual-entry templates for remaining common fallback domains.

## 5. Post-Beta Backlog

1. Scheduled backups and richer backup artifact management.
2. Full restore apply UI and artifact import workflow.
3. Unified end-to-end audit timeline across Journey, Evidence, Review, and Export.
4. Export ZIP artifact assertions in the dry-run harness.
5. Frontend/manual UX automation beyond backend state validation.
6. Additional evidence rules for managed funds, shares, crypto, and future domains.
7. Offline/resumable upload or richer interruption tolerance beyond current MVP.

## 6. Beta Scope

## Supported users

- PAYG employees
- PAYG users with bank interest
- PAYG users with common deductions:
  - WFH
  - donations
  - work expenses
- PAYG users with light investment complexity:
  - simple managed fund distributions
  - basic shares buy/sell
  - basic crypto buy/sell/staking

## Unsupported users

- Property investors
- Complex sole traders or contractors
- Users with advanced CGT/corporate action needs
- Users expecting full unsupported-domain tax coverage
- Users who need offline-first or resumable-upload behavior

## Supported tax domains

- PAYG income
- bank interest
- WFH deduction
- donations
- work expenses
- managed fund distribution
- simple shares acquisition/disposal review facts
- simple crypto acquisition/disposal/staking review facts

## Unsupported or only partially supported domains

- property schedules
- complex business income workflows
- advanced portfolio cost-base tracing
- complex corporate actions
- broad generic manual-entry categories not yet schema-hardened

## 7. Operational Runbook

## Create backup before Beta

Preferred path:

1. Open Settings -> Workspace Safety.
2. Check backup safety status.
3. Run `Backup Workspace`.
4. If recovery-key verification is part of the session, verify recovery key before relying on portable restore.
5. Confirm a successful backup/verification result before inviting a user to continue substantial work.

## Run dry-run harness

Documented command:

```bash
make test-file FILE=tests/integration/test_beta_dry_run.py
```

If scenario summaries are needed:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend pytest tests/integration/test_beta_dry_run.py -s -v
```

## Verify frontend/backend health

Backend:

```bash
curl -sS http://127.0.0.1:8060/api/v1/health
```

Frontend:

```bash
curl -I http://127.0.0.1:3060
```

Containers:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

## Logs to inspect

Backend logs:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs --tail=200 backend
```

Frontend logs:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs --tail=200 frontend
```

Focus areas:

- Alembic migration failures
- evidence reconcile failures
- export generation failures
- restore/apply failures
- repeated document processing failures

## Recover workspace

Minimum recovery path:

1. Open Workspace Safety.
2. Verify recovery key if needed.
3. Run restore preview on the target backup.
4. Confirm compatibility and review blockers/warnings.
5. Apply restore through the supported recovery backend/operator workflow.
6. Confirm post-restore reconcile completes and evidence/readiness refreshes.

## 8. Final Recommendation

**Recommendation: Ready with conditions**

Conditions:

1. Invite-only cohort must stay inside the supported PAYG-focused scope.
2. Unsupported-domain warnings and operator guidance must be explicit.
3. Recovery/backup discipline must be followed for all Beta workspaces.
4. Readiness/export copy must remain explicit about soft-block evidence semantics.

Rationale:

- The highest-risk platform blockers called out for Beta have been reduced to MVP-acceptable levels.
- Backend stability, recovery path, session resilience, evidence freshness visibility, review auditability, and dry-run harness trust are all at pass level for the supported cohort.
- The remaining risks are real, but they are mostly scope and policy-management risks, not core invite-only Beta stability defects.
