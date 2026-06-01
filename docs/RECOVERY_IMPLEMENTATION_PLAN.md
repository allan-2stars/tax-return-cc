# RECOVERY_IMPLEMENTATION_PLAN

Goal: convert Recovery MVP definition into a concrete execution roadmap for invite-only Beta readiness.

Inputs considered:
- `docs/PRODUCT_HARDENING_AUDIT.md`
- `docs/BETA_BLOCKERS.md`
- `docs/WORKSPACE_RECOVERY_DESIGN.md`
- `docs/WORKSPACE_RECOVERY_GAPS.md`
- `docs/RECOVERY_MVP.md`

Assumption: **Post-Restore Reconcile is part of Recovery MVP**.

---

## Milestone 13B-1C-1: Backup Foundation

## Objective
Establish a deterministic encrypted backup artifact that is integrity-verifiable and compatibility-aware.

## Scope
- Backup manifest schema
- Encrypted backup packaging
- Integrity verification primitives
- Compatibility metadata (`backup_format_version`, `db_schema_version`, `app_version`, rule metadata)

## Files likely affected
- `backend/app/services/` (new recovery service modules)
- `backend/app/api/routes/` (backup endpoints)
- `backend/app/db/models.py` (if backup job metadata model extension needed)
- `backend/alembic/versions/*` (only if persistent backup metadata table needed)
- `frontend/lib/api/*` (backup API client)
- `frontend/app/(dashboard)/settings/*` (Backup UI entry)
- `frontend/lib/api/types.ts`

## Backend changes
- Create `RecoveryService.backup_workspace(...)`
- Build artifact writer with staged temp + atomic finalize
- Build manifest and checksum generation
- Add integrity verification API (artifact-level)

## Frontend changes
- “Backup Workspace” action in Settings
- Backup status feedback (success/failure, timestamp)

## Migrations required
- **Prefer no migration** in MVP by storing operational status in existing logs/jobs.
- Optional migration if dedicated backup job table is required.

## Tests required
- Unit: manifest generation correctness
- Unit: encrypted package creation
- Unit: checksum verification pass/fail
- HTTP: backup create endpoint
- HTTP: verify endpoint
- Failure: interrupted backup leaves no valid artifact

## Acceptance criteria
- User can create encrypted backup artifact
- Artifact contains required metadata + checksum set
- Verification endpoint returns deterministic pass/fail
- Interrupted backup never appears as valid

## Estimated effort
- **Medium**

## Readiness impact after completion
- ~78 -> **81**

---

## Milestone 13B-1C-2: Recovery Key Verification

## Objective
Guarantee decryption path usability before recovery incidents and add auditability.

## Scope
- Recovery key verification flow
- Security requirements (attempt throttling, safe error responses)
- Verification audit events

## Files likely affected
- `backend/app/api/routes/auth.py` or recovery route group
- `backend/app/services/recovery_*`
- `backend/app/repositories/audit.py`
- `frontend/app/(dashboard)/settings/*`
- `frontend/components/*` (verification UX)

## Backend changes
- Add key verification endpoint (preflight only, no mutation)
- Add invalid-attempt rate limiting/throttle hooks
- Emit audit events for verify success/failure (non-sensitive)

## Frontend changes
- “Verify Recovery Key” flow in settings safety section
- Clear success/failure UX and guidance

## Migrations required
- **No** (reuse existing audit logging infrastructure)

## Tests required
- HTTP: valid key verify success
- HTTP: invalid key verify fail
- Security: repeated invalid attempts throttled
- Audit: verification events written correctly

## Acceptance criteria
- User can verify key without restoring
- Invalid keys do not reveal sensitive details
- Verification attempts are auditable

## Estimated effort
- **Small/Medium**

## Readiness impact after completion
- 81 -> **82**

---

## Milestone 13B-1C-3: Restore Preview

## Objective
Prevent blind restores by providing pre-apply validation and compatibility status.

## Scope
- Restore preview API
- Compatibility checks/matrix enforcement
- Validation checks (manifest/integrity/key/version/conflicts)

## Files likely affected
- `backend/app/services/recovery_*`
- `backend/app/api/routes/*` (restore preview endpoints)
- `docs/*` (compatibility matrix documentation)
- `frontend/app/(dashboard)/settings/*` or dedicated recovery page
- `frontend/lib/api/*`, `types.ts`

## Backend changes
- Parse/decrypt backup header payload
- Compute restore preview payload:
  - counts, versions, conflicts, blockers/warnings
- Enforce compatibility matrix policy

## Frontend changes
- Restore preview screen:
  - workspace identity
  - compatibility status
  - blockers/warnings
  - restore eligibility

## Migrations required
- **No**

## Tests required
- HTTP: preview with valid artifact
- HTTP: preview blocked by incompatible version
- HTTP: preview blocked by invalid checksum/key
- Contract: response includes blockers/warnings

## Acceptance criteria
- No restore apply allowed without preview pass
- Incompatible artifacts blocked with actionable message
- Preview includes deterministic risk signals (at least blockers/warnings)

## Estimated effort
- **Medium**

## Readiness impact after completion
- 82 -> **84**

---

## Milestone 13B-1C-4: Restore Engine

## Objective
Implement safe restore execution with rollback guarantees and minimum portability support.

## Scope
- Checkpoint creation before apply
- Restore transaction flow
- Rollback on failure/interruption
- New-device/new-deployment portability support

## Files likely affected
- `backend/app/services/recovery_restore.py` (new)
- `backend/app/storage/*` (path remap helpers)
- `backend/app/api/routes/*` (restore apply endpoints)
- `backend/tests/*` recovery integration tests
- `frontend` restore execution UX

## Backend changes
- Stage restore apply phases:
  1. checkpoint create
  2. apply db/files
  3. verify
  4. commit finalize
- Automatic rollback if phase fails
- Portability mapping for storage roots/keys

## Frontend changes
- Restore execution state UI (running/success/failure/rollback)
- Completion report

## Migrations required
- **Prefer no**  
- Optional if checkpoint metadata persistence requires schema.

## Tests required
- Integration: successful restore end-to-end
- Integration: restore interrupted -> rollback works
- Integration: corrupted payload -> fail without mutation
- Portability: restore to different storage path host

## Acceptance criteria
- Restore is atomic from user perspective
- Failed/interrupted restore auto-rolls back
- Restored workspace opens correctly on target environment

## Estimated effort
- **Medium/Large**

## Readiness impact after completion
- 84 -> **86**

---

## Milestone 13B-1C-5: Recovery Guards

## Objective
Prevent high-risk destructive operations when no recent valid backup exists.

## Scope
- Dangerous-operation backup guard
- Recent-backup policy enforcement
- Audit logging for guard checks/bypasses

## Files likely affected
- `backend/app/api/routes/settings.py` (archive/delete paths)
- `backend/app/services/recovery_policy.py`
- `frontend` destructive action modals/flows
- audit logging paths

## Backend changes
- Implement backup freshness policy gate (e.g., last successful verified backup window)
- Block or require inline backup before destructive actions
- Log bypass/override events if policy allows

## Frontend changes
- Pre-delete/irreversible action modal with backup status
- “Backup now” action inline before proceeding

## Migrations required
- **No**

## Tests required
- HTTP: dangerous action blocked without recent backup
- HTTP: action allowed after fresh backup
- Audit: guard events recorded
- UX tests: modal shows backup requirement

## Acceptance criteria
- Destructive actions are guarded by backup policy
- User has clear remediation path (“Backup now”)
- Guard outcomes are auditable

## Estimated effort
- **Small/Medium**

## Readiness impact after completion
- 86 -> **87**

---

## Milestone 13B-1C-6: Post-Restore Reconcile

## Objective
Re-establish domain consistency after restore across evidence/readiness/export-preview/explanations.

## Scope
- Trigger evidence reconciliation post-restore
- Refresh readiness 2.0 derived state
- Refresh export evidence preview-derived fields
- Ensure explanation sidecars align with reconciled state

## Files likely affected
- `backend/app/services/evidence_reconcile.py`
- `backend/app/services/recovery_restore.py`
- `backend/app/api/routes/readiness.py`
- `backend/app/api/routes/export.py`
- `backend/tests/*` integration tests

## Backend changes
- Add post-restore pipeline hook:
  1. reconcile obligations/matches
  2. invalidate/recompute readiness surfaces
  3. ensure export preview reflects fresh evidence
- Return post-restore reconcile status in restore completion report

## Frontend changes
- Restore completion UI shows “reconcile in progress/complete”
- Guidance to refresh checklist/readiness/export pages (or auto-refetch)

## Migrations required
- **No**

## Tests required
- Integration: restore then obligations consistent
- Integration: readiness reflects restored + reconciled state
- Integration: export preview reflects reconciled evidence counts
- Regression: explanation sidecars still present and coherent

## Acceptance criteria
- Restored workspace does not remain in stale evidence/readiness/export state
- Reconcile pipeline runs deterministically after restore
- User-visible completion includes reconcile outcome

## Estimated effort
- **Small**

## Readiness impact after completion
- 87 -> **88–89**

---

## Dependency Graph

## Strict prerequisites
1. **13B-1C-1 Backup Foundation** before all other milestones
2. **13B-1C-3 Restore Preview** before 13B-1C-4 Restore Engine apply path
3. **13B-1C-4 Restore Engine** before 13B-1C-6 Post-Restore Reconcile

## Recommended order (critical path)
1. 13B-1C-1 Backup Foundation
2. 13B-1C-2 Recovery Key Verification
3. 13B-1C-3 Restore Preview
4. 13B-1C-4 Restore Engine
5. 13B-1C-5 Recovery Guards
6. 13B-1C-6 Post-Restore Reconcile

## Parallelizable work
- 13B-1C-2 can partially run in parallel with late 13B-1C-1 test hardening.
- 13B-1C-5 UI work can start during 13B-1C-4 backend implementation.
- Documentation and compatibility matrix formalization can run parallel to 13B-1C-3.

---

## Beta Impact Progression (Estimated)

1. After 13B-1C-1: **81**
2. After 13B-1C-2: **82**
3. After 13B-1C-3: **84**
4. After 13B-1C-4: **86**
5. After 13B-1C-5: **87**
6. After 13B-1C-6: **88–89**

Baseline assumed: **78/100**

---

## Final Recommendation

Implement **13B-1C-1 Backup Foundation first**.

### Why first
1. Every other recovery feature depends on having a deterministic encrypted artifact with manifest/integrity metadata.
2. It immediately reduces catastrophic-loss risk.
3. It provides the technical contract needed by preview, restore, guards, and reconcile completion.

Without 13B-1C-1, downstream recovery milestones cannot be safely validated end-to-end.

