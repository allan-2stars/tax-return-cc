# WORKSPACE_RECOVERY_DESIGN

Goal: define a complete workspace disaster-recovery system for Tax Return AI.

This design addresses the Critical Beta blocker: missing full workspace backup/restore portability and recovery guarantees.

---

## 1) Backup Model

## 1.1 Backup types

1. **Manual backup**
   - User-triggered from Settings.
   - Immediate point-in-time workspace package.
2. **Pre-export backup**
   - Optional automatic backup before generating final export.
   - Reduces risk before high-value handoff events.
3. **Scheduled backup**
   - Configurable cadence (daily/weekly) with retention policy.
   - Local-only schedule in current deployment model.
4. **Encrypted backup**
   - Mandatory encryption at rest for backup artifacts.
   - Never store unencrypted workspace backup payloads.

## 1.2 Backup unit of data

Backup must include full workspace recovery scope:
- Workspace metadata
- Tax profile/session/interview state
- Tax events/review items
- Evidence obligations/matches
- Documents metadata + binary files
- Export history metadata (optional: export binaries configurable)
- Audit logs
- Version/provenance metadata:
  - app version
  - schema/migration version
  - evidence rule version distribution

## 1.3 Backup artifact shape (proposed)

Single encrypted archive:
- `workspace-backup-{workspace_id}-{timestamp}.trb` (Tax Return Backup)

Inside encrypted container (logical structure):
- `manifest.json` (metadata + checksums + version headers)
- `db/workspace_snapshot.jsonl` or table-wise JSON
- `documents/*`
- `exports/*` (optional by policy)
- `checksums.sha256`
- `signature.json` (optional HMAC/signature metadata)

## 1.4 Backup consistency strategy

Use one of:
1. **Transactional snapshot + file freeze window** (preferred)
2. **Copy-on-write staging directory**

Minimum requirement:
- DB snapshot and file manifest must be consistent to one checkpoint timestamp.

---

## 2) Restore Model

## 2.1 Restore flow

1. Upload/select backup artifact
2. Decrypt header and validate key material
3. Show **Restore Preview** (workspace name/FY/counts/version)
4. Run integrity verification
5. Optional dry-run validation
6. Create rollback checkpoint
7. Apply restore
8. Post-restore verification + completion report

## 2.2 Restore preview

Preview must include:
- workspace_id/name/fy
- created_at backup timestamp
- record counts (events/review/docs/obligations)
- backup app/schema/rule versions
- estimated restore size/time
- conflicts (existing workspace id/name/fy)

## 2.3 Integrity verification

Before apply:
- checksum validation for manifest and payload segments
- encryption/authentication tag verification
- required files presence checks
- schema compatibility validation

## 2.4 Recovery-key validation

User must provide recovery credential path:
- password-derived or recovery-key-derived decrypt route
- explicit “key valid / invalid” preflight result

## 2.5 Dry-run restore

Dry-run applies no persistent changes:
- parse + decrypt + validate schema mappings
- simulate id remapping/conflict policy
- report pass/fail and warnings

## 2.6 Rollback checkpoint

Before apply:
- create checkpoint snapshot of current workspace state
- if restore fails mid-flight, auto-rollback to checkpoint
- keep checkpoint restorable for short retention window

---

## 3) Failure Scenarios

## 3.1 Interrupted backup
- Behavior: incomplete backup marked invalid; never surfaced as restorable.
- Mitigation: staged temp artifact + atomic finalize rename.

## 3.2 Interrupted restore
- Behavior: automatic rollback to checkpoint.
- Mitigation: idempotent restore phases + resume-safe state marker.

## 3.3 Corrupted backup
- Behavior: fail at integrity precheck with explicit error.
- Mitigation: checksums + authenticated encryption + manifest validation.

## 3.4 Wrong recovery key
- Behavior: fail before restore preview apply; no data mutation.
- Mitigation: separate key-validation preflight step.

## 3.5 Version mismatch
- Behavior:
  - compatible minor mismatch: allowed with migration plan
  - incompatible major mismatch: blocked with upgrade path
- Mitigation: version policy matrix in restore engine.

---

## 4) Workspace Portability

## 4.1 New device restore

Supported path:
1. Install same/newer app version
2. Provide backup artifact + recovery secret
3. Run preview + restore
4. Verify restored workspace health

## 4.2 New deployment restore

Supports movement across:
- Docker host change
- path changes
- environment changes

Requirements:
- environment-agnostic artifact paths
- deterministic re-linking of document storage keys to local storage backend

---

## 5) Security Model

## 5.1 Encryption boundaries

- Backup payload always encrypted.
- Encryption key derived from user credential flow (aligned with existing workspace security model).
- No plaintext backup writes outside secure temp memory/disk windows.

## 5.2 Recovery-key usage

- Recovery key enables decryption/restoration when normal credential path unavailable.
- Recovery key is never stored in plaintext after setup.
- Restore flow should strongly encourage key verification drill.

## 5.3 Audit logging

Log all backup/restore actions:
- initiated_by
- workspace_id
- backup_id / restore_id
- start/end timestamps
- status (success/fail/rollback)
- failure code (non-sensitive)
- source/target environment markers

---

## 6) UX Design

## 6.1 Backup Workspace

Entry point: Settings -> Workspace Safety
- Primary actions:
  - Backup now
  - Enable scheduled backup
  - Pre-export backup toggle
- Show:
  - last backup timestamp/status
  - retention policy
  - storage usage estimate

## 6.2 Restore Workspace

Entry point: Settings -> Workspace Safety
- Upload/select backup file
- Enter credential/recovery key
- Run verify

## 6.3 Restore Preview

Preview panel:
- workspace identity + FY
- item counts summary
- app/schema/rule versions
- conflict warnings + resolution mode
- dry-run result

## 6.4 Restore Complete

Completion report:
- restored counts vs backup counts
- warnings/skips
- post-restore health check summary
- optional “open restored workspace” CTA

---

## 7) Recommended Implementation Order

1. **Phase 1: Backup foundation**
   - manifest schema
   - manual encrypted backup
   - integrity checks
2. **Phase 2: Restore safe path**
   - preview + key validation + dry-run
   - rollback checkpoint and atomic apply
3. **Phase 3: Portability hardening**
   - cross-environment path remapping
   - compatibility matrix enforcement
4. **Phase 4: Scheduled/pre-export backup**
   - scheduling
   - retention management
5. **Phase 5: UX polish + support tooling**
   - status dashboards
   - restore reports
   - admin diagnostics

---

## Migration and Compatibility Considerations

1. **No immediate schema migration required for MVP backup format**, but include:
   - `backup_format_version`
   - `db_schema_version`
   - `app_version`
2. Restore engine must support:
   - same-version restore
   - newer-app restore of older backup (forward compatibility path)
3. Explicit policy for incompatible versions:
   - block restore with actionable upgrade instructions
4. For evolving rule/versioned models (evidence/explanations):
   - restore raw historical data as-is
   - optionally trigger post-restore reconcile with clear user notice

---

## Readiness Impact After Implementation

Current readiness baseline (hardening audit): **78/100**.

Expected impact after full workspace backup/restore implementation:
- **+7 to +10 points** on operational/beta readiness.
- Likely updated readiness range: **85–88/100** (before other Beta blockers).

Reason:
- Eliminates highest-risk data-loss scenario.
- Enables safe real-user Beta with recoverability guarantees.
- Improves trust, supportability, and compliance posture.

---

## Final Design Position

Workspace backup/restore must be treated as a core safety subsystem, not a convenience feature.  
For Beta with real taxpayer data, disaster-recovery guarantees are required for responsible rollout.

