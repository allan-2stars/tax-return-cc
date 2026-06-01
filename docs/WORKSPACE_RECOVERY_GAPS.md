# WORKSPACE_RECOVERY_GAPS

Review source: `docs/WORKSPACE_RECOVERY_DESIGN.md`  
Scope: gap analysis only (no implementation changes).

---

## 1) Missing Recovery Safeguards

## Gap 1.1: No explicit immutable backup retention lock
- **Severity:** High
- **Recommendation:** Add retention lock option (e.g., keep last N “protected” backups not auto-pruned).
- **Implementation effort:** Medium

## Gap 1.2: No explicit restore “two-person confirm” for destructive overwrite
- **Severity:** Medium
- **Recommendation:** Require second confirmation phrase and final summary hash before overwrite restore.
- **Implementation effort:** Small

## Gap 1.3: No documented maximum restore-time timeout and abort policy
- **Severity:** Medium
- **Recommendation:** Define timeout/abort behavior with safe rollback and resumable status markers.
- **Implementation effort:** Small

## Gap 1.4: No anti-replay/nonce model for backup artifact metadata
- **Severity:** Medium
- **Recommendation:** Add backup artifact UUID + nonce + creation signature to detect replay/confusion issues.
- **Implementation effort:** Medium

## Gap 1.5: No explicit post-restore reconciliation safety sequence
- **Severity:** High
- **Recommendation:** Define deterministic post-restore pipeline: integrity check -> optional reconcile -> readiness refresh.
- **Implementation effort:** Medium

---

## 2) Backup-Health UX Recommendations

## Gap 2.1: Backup health is timestamp-centric, not confidence-centric
- **Severity:** High
- **Recommendation:** Show health state: `Healthy / Aging / Stale / Failed`, based on age + last verification result.
- **Implementation effort:** Small

## Gap 2.2: No backup verification badge
- **Severity:** High
- **Recommendation:** Add “Verified restorable” badge from periodic checksum/decrypt smoke test.
- **Implementation effort:** Medium

## Gap 2.3: No proactive alert thresholds
- **Severity:** Medium
- **Recommendation:** Trigger warnings for “no successful backup in X days” and “backup storage nearly full”.
- **Implementation effort:** Small

## Gap 2.4: No user-visible backup delta summary
- **Severity:** Medium
- **Recommendation:** Show what changed since last backup (docs/events/review changes) to build user trust.
- **Implementation effort:** Medium

## Gap 2.5: No explicit failed-backup remediation flow
- **Severity:** Medium
- **Recommendation:** Provide guided recovery actions (retry, free space, verify key, view logs).
- **Implementation effort:** Small

---

## 3) Recovery-Key Verification Flow

## Gap 3.1: “Strongly encourage drill” is non-binding
- **Severity:** High
- **Recommendation:** Add mandatory key verification step at setup completion and periodic reminders.
- **Implementation effort:** Medium

## Gap 3.2: No explicit key-rotation + re-encryption flow
- **Severity:** Medium
- **Recommendation:** Define recovery-key rotation UX and cryptographic rewrap procedure with rollback.
- **Implementation effort:** Medium

## Gap 3.3: No lockout/rate-limit strategy for repeated invalid key attempts
- **Severity:** Medium
- **Recommendation:** Add attempt throttling + security event logging for repeated failures.
- **Implementation effort:** Small

## Gap 3.4: No “proof of recovery” artifact in audit logs
- **Severity:** Medium
- **Recommendation:** Log successful verification checkpoints with timestamp and workspace context.
- **Implementation effort:** Small

## Gap 3.5: No clear lost-key/no-key recovery boundary UX
- **Severity:** High
- **Recommendation:** Explicitly communicate irrecoverability conditions and require acknowledgement.
- **Implementation effort:** Small

---

## 4) Restore-Risk Scoring Model

## Gap 4.1: No formal restore risk score in preview
- **Severity:** High
- **Recommendation:** Add risk score (0–100) derived from:
  - version delta severity
  - artifact verification confidence
  - overwrite conflict level
  - partial data omissions
  - key-validation posture
- **Implementation effort:** Medium

## Gap 4.2: No graded restore modes by risk tier
- **Severity:** Medium
- **Recommendation:** Map risk tiers to policies:
  - Low: standard restore
  - Medium: mandatory dry-run
  - High: dry-run + explicit override confirmation
- **Implementation effort:** Medium

## Gap 4.3: No structured blocker/warning list in restore preview
- **Severity:** Medium
- **Recommendation:** Standardize preview output with `blockers`, `warnings`, `notes`.
- **Implementation effort:** Small

## Gap 4.4: No quantitative integrity confidence display
- **Severity:** Low
- **Recommendation:** Show confidence indicator from checksum/signature coverage completeness.
- **Implementation effort:** Small

---

## 5) Backup-Before-Dangerous-Operation Policy

## Gap 5.1: Policy not explicitly enforced for destructive operations
- **Severity:** Critical
- **Recommendation:** Require successful recent backup before:
  - workspace delete/archive
  - major restore overwrite
  - irreversible security resets
- **Implementation effort:** Medium

## Gap 5.2: No freshness threshold for “recent backup”
- **Severity:** High
- **Recommendation:** Define policy threshold (e.g., successful verified backup within last 24h) or explicit bypass justification.
- **Implementation effort:** Small

## Gap 5.3: No forced pre-operation backup fallback flow
- **Severity:** High
- **Recommendation:** Offer “Create backup now” inline path before allowing dangerous action.
- **Implementation effort:** Small

## Gap 5.4: No audit requirement for bypassing backup guard
- **Severity:** Medium
- **Recommendation:** Log reasoned bypass events with actor/time/action context.
- **Implementation effort:** Small

---

## 6) Restore Compatibility Matrix

## Gap 6.1: Version policy is conceptual, not tabulated
- **Severity:** High
- **Recommendation:** Publish explicit matrix:
  - backup_format_version vs app_version
  - db_schema_version compatibility
  - rule_version behavior
- **Implementation effort:** Small

## Gap 6.2: No downgrade/forward incompatibility handling strategy details
- **Severity:** High
- **Recommendation:** Define:
  - allowed upgrades
  - blocked downgrades
  - conditional migrations with dry-run required
- **Implementation effort:** Medium

## Gap 6.3: No compatibility behavior for optional payload sections
- **Severity:** Medium
- **Recommendation:** Define required vs optional sections and fail/open behavior per section.
- **Implementation effort:** Small

## Gap 6.4: No test contract requirement for matrix guarantees
- **Severity:** Medium
- **Recommendation:** Require compatibility matrix-backed test suite:
  - same-version restore
  - +1 minor upgrade restore
  - unsupported major mismatch blocked
  - missing optional section tolerated
- **Implementation effort:** Medium

---

## Summary Priority

## Must address first
1. Backup-before-dangerous-operation enforcement (5.1, 5.2, 5.3)
2. Explicit compatibility matrix (6.1, 6.2)
3. Mandatory recovery-key verification lifecycle (3.1)
4. Backup health confidence UX (2.1, 2.2)
5. Restore risk scoring baseline (4.1)

These close the largest practical safety gaps between current design and Beta-ready recovery guarantees.

