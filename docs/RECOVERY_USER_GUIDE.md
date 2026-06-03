# Recovery User Guide

This guide covers the current Recovery MVP workflow for protecting a Tax Return AI workspace before Beta use.

## What Recovery Does

Recovery protects a workspace by creating encrypted `.trb` backup artifacts, verifying backup integrity, checking recovery keys, previewing restore safety, and applying backend recovery guards before destructive workspace operations.

The current Workspace Safety UI exposes:

- Backup Workspace
- Verify Backup
- Verify Recovery Key
- Restore Preview
- Backup safety status

Restore preview is non-mutating. It validates a backup and reports whether restore would be allowed, but it does not change workspace data.

## Creating a Backup

Use **Settings -> Workspace Safety -> Backup Workspace**.

The backup process:

1. Builds a deterministic backup manifest.
2. Includes workspace, interview, tax event, review, evidence, document metadata, and document file data where available.
3. Encrypts the `.trb` artifact.
4. Verifies manifest and checksum integrity.
5. Finalises the artifact only after successful staging.

No plaintext backup artifact should remain after a successful or failed backup attempt.

## Verifying a Backup

Use **Verify Backup** with the backup ID shown after creation.

Verification checks:

- Backup can be decrypted.
- Manifest exists.
- Required sections are present.
- Checksums match.
- Compatibility metadata exists.

The Workspace Safety status uses recent verified backups to decide whether destructive operations should be allowed.

## Verifying a Recovery Key

Use **Verify Recovery Key** before relying on a backup for portability.

The verification endpoint checks the key without changing workspace data. Recovery key material must not be logged or shown in audit records.

A valid recovery key is required for portable restore when a backup uses recovery-key-derived encryption.

## Previewing Restore

Use **Restore Preview** with a backup ID and, when required, the recovery key.

Restore preview checks:

- Encryption mode and key validity.
- Backup format compatibility.
- Manifest and section integrity.
- Workspace ID and financial year.
- Existing workspace conflicts.
- Blockers, warnings, and notes.

Restore preview does not apply restore data, overwrite the current workspace, or mutate documents.

## Backup Safety Status

Workspace Safety shows:

- Status: healthy, stale, missing, or failed.
- Last backup time.
- Last verified time.
- Policy window in hours.
- Whether dangerous-operation guards are enabled.

MVP policy: destructive workspace actions require a successful verified backup inside the configured policy window, currently 24 hours.

## Before Deleting Or Archiving A Workspace

Before a destructive operation:

1. Create a backup.
2. Verify the backup.
3. Verify the recovery key if you need portability.
4. Confirm Workspace Safety status is healthy.

The backend recovery guard may block dangerous operations if no recent verified backup exists.

## Current Limitations

- Scheduled backups are not implemented.
- Full restore apply is backend-only; no complete frontend restore wizard is exposed yet.
- Restore preview accepts safe backup summaries only and does not show raw tax data.
- Backup retention locks are not implemented.
- Recovery key rotation for old artifacts is not implemented.
- Compatibility policy is MVP-level and should be expanded before broader production use.

## Operational Notes

- Keep `.trb` artifacts outside the application host when preparing for device failure.
- Store recovery keys separately from backup artifacts.
- Run restore preview before any restore apply operation.
- After restore apply, the backend runs post-restore reconciliation so Evidence Intelligence, Readiness 2.0, export evidence preview, and explanation sidecars reflect restored data.
