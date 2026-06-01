# RECOVERY_MVP

Goal: define the minimum Recovery capability required to move Tax Return AI from current readiness to an invite-only Beta candidate, assuming only **2 weeks** of implementation time.

Inputs reviewed:
- `docs/PRODUCT_HARDENING_AUDIT.md`
- `docs/BETA_BLOCKERS.md`
- `docs/WORKSPACE_RECOVERY_DESIGN.md`
- `docs/WORKSPACE_RECOVERY_GAPS.md`

---

## Decision Framing (2-week constraint)

With 2 weeks, the objective is not full enterprise DR.  
The objective is: **prevent catastrophic user data loss and unsafe restore actions** for invite-only Beta.

Core principle:
1. Users must be able to create a recoverable encrypted backup.
2. Users must be blocked from high-risk destructive actions without recent backup.
3. Restore must be verifiable and safely gated before mutation.

---

## Capability Classification

## 1) Manual Backup
- **Why required:** baseline recoverability for every user.
- **User risk if missing:** irrecoverable workspace loss.
- **Dependencies:** encrypted backup format, manifest/checksum.
- **Implementation effort:** Medium
- **Beta requirement:** **Must Have**

## 2) Scheduled Backup
- **Why required:** reduces human error from missed manual backups.
- **User risk if missing:** backup may become stale.
- **Dependencies:** manual backup pipeline + scheduler state.
- **Implementation effort:** Medium
- **Beta requirement:** Should Have

## 3) Encrypted Backup
- **Why required:** sensitive tax data protection.
- **User risk if missing:** severe data exposure risk.
- **Dependencies:** key derivation/recovery-key path.
- **Implementation effort:** Medium
- **Beta requirement:** **Must Have**

## 4) Backup Health Dashboard
- **Why required:** users need confidence backup is fresh/restorable.
- **User risk if missing:** false sense of safety.
- **Dependencies:** backup metadata + verification events.
- **Implementation effort:** Small
- **Beta requirement:** Should Have

## 5) Recovery Key Verification
- **Why required:** ensures restore path actually works before incident.
- **User risk if missing:** backup unusable at recovery time.
- **Dependencies:** encrypted backup + key validation API.
- **Implementation effort:** Small/Medium
- **Beta requirement:** **Must Have**

## 6) Restore Preview
- **Why required:** prevents blind destructive restore.
- **User risk if missing:** wrong workspace overwrite.
- **Dependencies:** backup parsing + metadata manifest.
- **Implementation effort:** Medium
- **Beta requirement:** **Must Have**

## 7) Restore Risk Score
- **Why required:** standardizes restore risk communication.
- **User risk if missing:** ambiguous restore warnings.
- **Dependencies:** preview + compatibility checks.
- **Implementation effort:** Medium
- **Beta requirement:** Nice To Have

## 8) Compatibility Matrix
- **Why required:** prevents incompatible restores.
- **User risk if missing:** silent corruption or failed restore.
- **Dependencies:** version metadata in backup.
- **Implementation effort:** Small
- **Beta requirement:** **Must Have**

## 9) Rollback Checkpoint
- **Why required:** safe recovery from interrupted/failed restore.
- **User risk if missing:** partial corruption after failed restore.
- **Dependencies:** snapshot mechanism + restore transaction phases.
- **Implementation effort:** Medium/Large
- **Beta requirement:** **Must Have**

## 10) Post-Restore Reconcile
- **Why required:** refreshes evidence/readiness integrity after restore.
- **User risk if missing:** stale or contradictory state after restore.
- **Dependencies:** reconcile trigger service.
- **Implementation effort:** Small
- **Beta requirement:** **Must Have**

## 11) Workspace Portability
- **Why required:** move workspace to new machine/deployment.
- **User risk if missing:** recovery limited to same environment.
- **Dependencies:** portable artifact paths + compatibility matrix.
- **Implementation effort:** Medium
- **Beta requirement:** **Must Have** (minimum “new device restore”)

## 12) Backup Retention Lock
- **Why required:** protects key recovery snapshots from auto-prune.
- **User risk if missing:** accidental loss of last known-good backup.
- **Dependencies:** retention subsystem.
- **Implementation effort:** Medium
- **Beta requirement:** Nice To Have

## 13) Dangerous Operation Backup Guard
- **Why required:** blocks destructive actions without recent backup.
- **User risk if missing:** preventable data loss.
- **Dependencies:** backup metadata freshness policy.
- **Implementation effort:** Small/Medium
- **Beta requirement:** **Must Have**

## 14) Recovery Audit Log
- **Why required:** incident traceability and supportability.
- **User risk if missing:** weak accountability/debugging.
- **Dependencies:** audit event schema and writes.
- **Implementation effort:** Small
- **Beta requirement:** **Must Have**

## 15) Restore Dry Run
- **Why required:** preflight validation before mutation.
- **User risk if missing:** avoidable restore failures during apply.
- **Dependencies:** preview parser + compatibility checks.
- **Implementation effort:** Medium
- **Beta requirement:** Should Have

---

## A) Recovery MVP Scope (Must Have for Beta)

1. Manual Backup  
2. Encrypted Backup  
3. Recovery Key Verification  
4. Restore Preview  
5. Compatibility Matrix (enforced)  
6. Rollback Checkpoint  
7. Workspace Portability (minimum new-device restore path)  
8. Dangerous Operation Backup Guard  
9. Recovery Audit Log  
10. Post-Restore Reconcile

### Why this is minimum
- Covers catastrophic-loss risk.
- Prevents unsafe restore writes.
- Ensures recoverability is not theoretical.
- Adds operational traceability for Beta support.

---

## B) Recovery Phase 2 (Recommended after Beta start)

1. Scheduled Backup  
2. Backup Health Dashboard  
3. Restore Dry Run  
4. Restore Risk Score (simple version)

---

## C) Recovery Phase 3 (Enterprise-grade Enhancements)

1. Backup Retention Lock / legal-hold style preservation
2. Advanced restore risk model with policy tiers
3. Multi-target backup destinations and integrity attestation
4. Restore simulation reports and automated compatibility certification

---

## D) Final Architecture Recommendation

Implement Recovery as a dedicated service boundary:
- `RecoveryService` (backup/restore orchestrator)
- `BackupManifest` contract (versioned)
- `CompatibilityPolicy` module (explicit matrix)
- `RecoveryAudit` event stream

Execution model:
1. Backup/restore operations run as resumable staged jobs.
2. Restore apply is guarded by preview + compatibility + key validation.
3. Rollback checkpoint is mandatory before apply in MVP.

Avoid in MVP:
- broad background infrastructure redesign
- cross-region storage
- enterprise retention complexity

---

## E) Readiness Impact Estimate

Baseline from prior audit: **78/100**

If Recovery MVP (Must Have set) is complete:
- Estimated readiness: **87–89/100**

If Recovery Phase 2 is complete:
- Estimated readiness: **90–92/100**

If Recovery Phase 3 is complete:
- Estimated readiness: **92–94/100**

Rationale:
- MVP directly addresses the top Critical blocker (workspace recoverability).
- Phase 2 improves reliability confidence and user trust loops.
- Phase 3 mostly improves scale/compliance posture.

---

## Prioritized Implementation Order (2-week realistic sequence)

1. Encrypted manual backup artifact + manifest + integrity checks
2. Recovery key verification preflight
3. Compatibility matrix enforcement (block incompatible restore)
4. Restore preview
5. Rollback checkpoint + restore apply transaction flow
6. Dangerous-operation backup guard
7. Recovery audit logging
8. Minimum portability validation path (new device restore runbook)
9. Post-restore reconcile + readiness refresh + export-evidence preview refresh

---

## Final Recommendation

**Recommendation: Beta after Recovery MVP**

### Rationale
- Current state without recovery MVP leaves unacceptable catastrophic-loss risk.
- Recovery MVP is the minimum safety threshold for invite-only real-user Beta.
- Recovery is not optional for this product class; “Recovery not required” is not defensible.

---

## Post-Restore Reconcile Re-evaluation

**Explicit recommendation: Promote to Recovery MVP**

### Rationale
Given current platform coupling, restore is not complete unless state is re-reconciled:
1. **EvidenceObligation consistency:** restored profile/events can invalidate prior obligation status until reconcile runs.
2. **EvidenceMatch regeneration:** candidate links are deterministic and may need rebuild from restored docs/events.
3. **Readiness 2.0 freshness:** evidence + journey/review rollups can remain stale without a post-restore recompute path.
4. **Explanation-layer consistency:** explanation sidecars depend on current category/obligation state and should align after reconcile.
5. **Export evidence preview consistency:** export preview consumes evidence summaries; stale post-restore data can mislead users.

### Beta readiness impact
- Promoting post-restore reconcile to MVP increases reliability confidence for restore outcomes.
- Estimated uplift: approximately **+1 point** versus prior MVP estimate.
- Revised estimate reflected above: **Recovery MVP complete = 87–89/100**.
