# Recovery MVP Acceptance Audit

Milestone: 13B-1E  
Purpose: determine whether the Recovery MVP is complete enough to satisfy the Critical Beta blocker identified in `docs/BETA_BLOCKERS.md`.

Inputs reviewed:

- `docs/RECOVERY_MVP.md`
- `docs/RECOVERY_IMPLEMENTATION_PLAN.md`
- `docs/RECOVERY_USER_GUIDE.md`
- `backend/app/services/recovery.py`
- `backend/app/services/recovery_compatibility.py`
- `backend/app/services/recovery_policy.py`
- `backend/app/api/routes/recovery.py`
- `backend/app/api/routes/workspaces.py`
- `backend/tests/test_recovery.py`
- `backend/tests/http/test_http_recovery.py`
- `backend/tests/test_settings.py`
- `frontend/components/settings/WorkspaceSafetyTab.tsx`
- `frontend/lib/api/recovery.ts`
- `frontend/__tests__/WorkspaceSafetyTab.test.tsx`
- `frontend/__tests__/settings-page.test.tsx`

## Executive Decision

**Recovery MVP status: Complete enough for invite-only Beta, with documented residual risk.**

Recovery now provides a first-class disaster-recovery path:

- encrypted `.trb` workspace backups
- manifest and checksum verification
- recovery-key-derived backup mode
- restore preview
- compatibility blocking
- restore apply with checkpoint and rollback
- minimum document-binary portability
- backup freshness guard for workspace archive/delete
- recovery audit events
- post-restore reconcile
- Workspace Safety UI

This resolves **Beta Blocker #1: No first-class disaster recovery path for workspace portability** at MVP level.

It does **not** fully close broader recovery/key-handling UX hardening. That risk remains tracked separately as high-priority Beta polish, especially around artifact download/selection, full frontend restore apply, scheduled backup, and recovery rehearsal workflows.

## Requirement Checklist

| Requirement | Implemented? | Evidence in Code/Docs/Tests | Remaining Gap | Beta Risk |
| --- | --- | --- | --- | --- |
| Manual Backup | Yes | `RecoveryService.create_backup(...)`; `POST /api/v1/recovery/backups`; `test_create_backup_and_verify_success`; Workspace Safety `Backup Workspace` action; `RECOVERY_USER_GUIDE.md` | UI is minimal and reports backup ID/path rather than a richer artifact management table. | Low |
| Encrypted Backup | Yes | `pyzipper.AESZipFile` with WZ_AES in `_write_encrypted_bundle`; `.trb` filename; staged temp then `os.replace`; `test_manifest_generation_contains_required_metadata`; `test_recovery_key_derived_backup_manifest_mode`; `test_failed_backup_leaves_no_finalized_artifact` | Default mode remains `server_derived`; portable mode requires explicit `recovery_key_derived` payload and is not exposed as a first-class UI toggle yet. | Medium |
| Recovery Key Verification | Yes | `POST /api/v1/recovery/key/verify`; `RecoveryService.verify_recovery_key`; 5-minute failure throttle in route; audit via `log_recovery_key_verification`; frontend Verify Recovery Key action; tests for success/failure/audit/safe error | UI verifies key but does not yet guide users into creating a recovery-key-derived backup after verification. | Medium |
| Restore Preview | Yes | `RecoveryService.preview_backup(...)`; `POST /api/v1/recovery/restore/preview`; checksum/key/version/workspace conflict checks; frontend Restore Preview action; tests for valid server-derived, valid recovery-key-derived, wrong key, corrupt backup, and non-mutation | UI is ID-based and does not support uploading/selecting an arbitrary `.trb` artifact yet. | Medium |
| Compatibility Matrix | Yes | `backend/app/services/recovery_compatibility.py`; `CURRENT_BACKUP_FORMAT_VERSION`; major-version blocker; unknown app/db version warnings; tests for incompatible format and missing metadata | Matrix is MVP-level only; app/db version policy is warning-oriented unless major format is incompatible. | Medium |
| Rollback Checkpoint | Yes | `restore_backup(...)` creates checkpoint through `create_backup(...)` before apply; rollback path reloads checkpoint and reapplies on failure; restore result includes `checkpoint_id` and `rollback_performed`; tests for successful restore and simulated failure rollback | Checkpoint metadata is artifact/path-based, not a persistent restore job record. Rollback failure is explicit and audited but still a severe operational state. | Low/Medium |
| Workspace Portability Minimum Path | Partial | Backup includes document binaries where available; `_restore_document_blobs(...)` writes to current storage backend path; `test_restore_apply_restores_document_binary_to_current_storage`; recovery-key-derived encryption support | Restore apply is scoped to current authenticated workspace ID and backup storage lookup. There is no complete “import backup from another deployment” UI/API upload path yet. Minimum storage-path remap works, but full new-device restore workflow is not polished. | Medium |
| Dangerous Operation Backup Guard | Yes | `RecoveryPolicyService.get_backup_safety_status`; `require_recent_backup_or_raise`; 24-hour policy; integrated into `workspace_archive` and `workspace_delete`; `GET /api/v1/recovery/safety-status`; tests for missing/healthy/stale status, archive block/pass, delete success after backup, guard audit events | Guard covers implemented destructive workspace operations. Future destructive operations must explicitly call the policy service. | Low/Medium |
| Recovery Audit Log | Partial | `AuditLog` entries for recovery key verify success/failure, restore apply start/success/failure, rollback start/success/failure, post-restore reconcile start/success/failure, guard checked/blocked/passed; tests assert key/restore/guard audit events | Backup create/verify actions are not clearly audited as first-class events. No unified recovery timeline UI exists. | Medium |
| Post-Restore Reconcile | Yes | `_run_post_restore_reconcile(...)` triggers `EvidenceReconcileService` with `trigger_source="restore_apply"` and `force=True`, runs `ReadinessEngine().calculate(...)`, returns `post_restore_reconcile`; tests assert obligations, readiness, export eligibility preview, and explanation sidecars after restore; failure reports warning without rollback | Reconcile failure after successful restore is non-blocking by design. UI does not yet show post-restore reconcile warnings because restore apply UI is not exposed. | Low/Medium |
| Workspace Safety UI | Yes | Settings tab `Workspace Safety`; `WorkspaceSafetyTab.tsx`; `frontend/lib/api/recovery.ts`; tests for status, backup success/failure, backup verify, recovery key verify, restore preview, and non-mutating copy; `RECOVERY_USER_GUIDE.md` | No full frontend restore apply flow. Backup/restore actions are still ID-based and operator-oriented. | Medium |

## Requirement Notes

### Manual And Encrypted Backup

The backup artifact is a versioned `.trb` package containing:

- workspace metadata
- tax profile state
- interview sessions
- tax events
- review items
- evidence obligations
- evidence matches
- document metadata
- document binary entries where storage access succeeds
- manifest checksums
- evidence rule version distribution
- app/db compatibility metadata

The implementation stages a temporary artifact, writes an encrypted archive, atomically finalizes it, then verifies it. Tests cover successful backup, tamper/corrupt failure, workspace scoping, and failed-backup cleanup.

### Recovery Key And Portability

Recovery-key-derived encryption exists and is tested. This is the critical foundation for portability if server secrets are lost. However, the default backup action in the current Workspace Safety UI uses the backend default mode. For Beta, the operational guide should instruct testers to verify recovery key and ensure at least one recovery-key-derived backup exists through supported API/operator workflow until the UI exposes that choice directly.

### Restore Safety

Restore apply repeats validation before mutation, requires `conflict_policy=replace_current_workspace`, creates a checkpoint first, applies DB/file state, verifies the restored workspace, and rolls back on failure. Tests cover:

- successful restore
- recovery-key-derived restore
- wrong key fails before mutation
- corrupt payload fails before mutation
- simulated failure rolls back
- document binary restored to current storage path
- audit events

This satisfies the no partial-success restore invariant at MVP level.

### Recovery Guards

Dangerous operation backup guard policy is implemented with a 24-hour freshness window. Archive and delete workspace routes are guarded. Safety status is exposed to the frontend.

Guard semantics:

- `missing`, `stale`, or `failed` backup status blocks dangerous action.
- `healthy` allows dangerous action.
- guard check/block/pass events are audited.

This is sufficient for current destructive operations. Any future destructive operation must call `RecoveryPolicyService.require_recent_backup_or_raise(...)`.

## Test Coverage Summary

Backend coverage includes:

- manifest generation and required metadata
- `.trb` encrypted package creation
- recovery-key-derived encryption metadata
- backup verification success
- tampered/corrupt verification failure
- failed backup leaves no finalized artifact
- workspace-scoped backup verification
- recovery key verification success/failure/audit
- restore preview with server-derived backup
- restore preview with recovery-key-derived backup
- wrong recovery key safe failure
- corrupt backup safe failure
- preview does not mutate DB state
- incompatible backup format blocked
- missing required metadata blocked
- safety status missing/healthy/stale
- archive/delete blocked or allowed according to safety status
- guard audit events
- restore apply success
- restore apply with recovery-key-derived backup
- wrong key/corrupt payload fail before mutation
- simulated apply failure rollback
- document binary storage-path remap
- restore audit events
- post-restore reconcile success
- post-restore reconcile failure reports warning without rollback

Frontend coverage includes:

- Workspace Safety tab appears under Settings
- safety status renders
- backup action success/failure
- backup verification success
- recovery key verification success/failure
- restore preview result rendering
- copy states that restore preview does not change data

Most recent relevant test results recorded during implementation:

- Backend: `make test` passed with 356 tests.
- Frontend: `make test-fe` passed with 386 tests.

This audit is documentation-only; no tests were rerun for this file.

## Known Limitations

1. **No scheduled backups.** Manual backup is available, but stale backup risk remains if users do not act.
2. **No rich backup artifact manager.** Users/operators currently work with backup IDs and paths.
3. **No full restore apply UI.** Backend restore apply exists; frontend exposes restore preview only.
4. **Minimum portability is partial.** Document storage-path remapping is tested, and recovery-key-derived encryption exists, but there is no polished import/upload flow for a backup from a different deployment.
5. **Audit coverage is not fully unified.** Restore, key verification, and guard events are audited. Backup create/verify first-class audit events and a recovery timeline UI are still missing.
6. **Compatibility matrix is MVP-level.** Major backup format mismatches block restore. Unknown app/db versions warn, but do not implement a richer compatibility grid.
7. **No retention lock.** A user or operator can still lose backup artifacts outside app control.
8. **No recovery rehearsal workflow.** Users can verify key and preview restore, but there is no guided “practice recovery” checklist.

## Does This Resolve Beta Blocker #1?

**Yes, at Recovery MVP level.**

`docs/BETA_BLOCKERS.md` identified the #1 Critical blocker as the lack of a first-class disaster recovery path for workspace portability. The implemented Recovery MVP now provides:

- a full-workspace encrypted backup artifact
- integrity verification
- recovery-key-derived encryption support
- restore preview and compatibility blocking
- restore apply with checkpoint/rollback
- document binary path remapping
- backup freshness guard for destructive workspace actions
- post-restore reconciliation
- minimal Workspace Safety UI and user guide

This is enough to move from “no first-class disaster recovery path” to “MVP disaster recovery path exists and is test-covered.”

The blocker should be downgraded from **Critical / Must Fix Before Beta** to **Medium residual risk / Beta polish**, mainly because portability and restore UX are not yet fully self-service.

## Updated Production Readiness Estimate

Previous baseline from `docs/PRODUCT_HARDENING_AUDIT.md`: **78/100**.

`docs/RECOVERY_MVP.md` estimated Recovery MVP completion would raise readiness to **87-89/100**.

Acceptance audit estimate:

- **Current after Recovery MVP: 88/100**

Rationale:

- Critical catastrophic-loss risk is materially addressed.
- Restore safety has backend checkpoint/rollback tests.
- Recovery key verification and recovery-key-derived encryption support true portability foundations.
- Backup guards reduce accidental destructive-loss risk.
- Post-restore reconcile reduces stale derived-state risk.
- Remaining risk is mostly UX polish, scheduled automation, import ergonomics, and broader audit timeline visibility.

## Beta Recommendation

**Recommendation: Beta after remaining non-recovery Must Fix items are triaged.**

Recovery no longer blocks invite-only Beta on its own. For Recovery specifically:

- acceptable for a controlled Beta with operator support
- acceptable for simple workspace backup/restore incidents
- not yet strong enough for unsupported self-service recovery at broader production scale

Before expanding beyond invite-only Beta, prioritize:

1. frontend recovery-key-derived backup option
2. artifact download/import workflow
3. full restore apply UI with explicit confirmation
4. first-class backup create/verify audit events
5. recovery timeline/support view
6. scheduled backup or prominent stale-backup reminders
