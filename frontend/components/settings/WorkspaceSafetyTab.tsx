'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, CheckCircle, KeyRound, Search } from 'lucide-react'
import {
  createBackup,
  getRecoverySafetyStatus,
  previewRestore,
  verifyBackup,
  verifyRecoveryKey,
} from '@/lib/api/recovery'
import type { RecoveryRestorePreviewData, RecoverySafetyStatusValue } from '@/lib/api/types'

type Feedback = { tone: 'success' | 'error'; message: string }

function formatDate(value: string | null): string {
  if (!value) return 'Not recorded'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function statusLabel(status: RecoverySafetyStatusValue): string {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function statusClass(status: RecoverySafetyStatusValue): string {
  if (status === 'healthy') return 'bg-ready-bg text-ready border-ready'
  if (status === 'failed') return 'bg-risk-bg text-risk-high border-risk-high'
  if (status === 'stale') return 'bg-review-bg text-review border-review'
  return 'bg-surface-raised text-text-muted border-border'
}

function errorMessage(err: unknown, fallback: string): string {
  const detail = (
    err as { response?: { data?: { detail?: { message?: string } } } }
  )?.response?.data?.detail
  return detail?.message || fallback
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between text-sm font-ui">
      <span className="text-text-muted">{label}</span>
      <span className="text-text-primary font-medium">{value}</span>
    </div>
  )
}

function FeedbackText({ feedback }: { feedback: Feedback | null }) {
  if (!feedback) return null
  return (
    <p className={`text-sm font-ui ${feedback.tone === 'success' ? 'text-ready' : 'text-risk-high'}`}>
      {feedback.message}
    </p>
  )
}

function PreviewResult({ preview }: { preview: RecoveryRestorePreviewData | null }) {
  if (!preview) return null

  return (
    <div className="rounded-md border border-border bg-surface-raised p-4 space-y-3">
      <div>
        <p className="text-sm font-ui font-semibold text-text-primary">
          {preview.can_restore ? 'Can restore' : 'Restore is blocked'}
        </p>
        <p className="text-sm font-ui text-text-muted">
          Preview only; no data is changed.
        </p>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <SummaryRow label="Workspace" value={preview.workspace_id || 'Unknown'} />
        <SummaryRow label="Financial year" value={preview.financial_year || 'Unknown'} />
        <SummaryRow label="Encryption" value={preview.encryption_mode || 'Unknown'} />
        <SummaryRow label="Sections" value={String(preview.included_sections.length)} />
      </div>
      {preview.blockers.length > 0 && (
        <div>
          <p className="text-sm font-ui font-semibold text-risk-high">Blockers</p>
          <ul className="mt-1 space-y-1">
            {preview.blockers.map((item) => (
              <li key={item} className="text-sm font-ui text-risk-high">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
      {preview.warnings.length > 0 && (
        <div>
          <p className="text-sm font-ui font-semibold text-review">Warnings</p>
          <ul className="mt-1 space-y-1">
            {preview.warnings.map((item) => (
              <li key={item} className="text-sm font-ui text-text-body">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function WorkspaceSafetyTab() {
  const queryClient = useQueryClient()
  const [backupFeedback, setBackupFeedback] = useState<Feedback | null>(null)
  const [backupIdToVerify, setBackupIdToVerify] = useState('')
  const [verifyBackupFeedback, setVerifyBackupFeedback] = useState<Feedback | null>(null)
  const [recoveryKey, setRecoveryKey] = useState('')
  const [keyFeedback, setKeyFeedback] = useState<Feedback | null>(null)
  const [previewBackupId, setPreviewBackupId] = useState('')
  const [previewRecoveryKey, setPreviewRecoveryKey] = useState('')
  const [previewFeedback, setPreviewFeedback] = useState<Feedback | null>(null)
  const [preview, setPreview] = useState<RecoveryRestorePreviewData | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['recovery', 'safety-status'],
    queryFn: () => getRecoverySafetyStatus().then((r) => r.data.data),
  })

  const backupMutation = useMutation({
    mutationFn: () => createBackup().then((r) => r.data.data),
    onSuccess: (result) => {
      setBackupFeedback({ tone: 'success', message: `Backup created: ${result.backup_id}` })
      void queryClient.invalidateQueries({ queryKey: ['recovery', 'safety-status'] })
    },
    onError: (err) => {
      setBackupFeedback({ tone: 'error', message: errorMessage(err, 'Backup failed.') })
    },
  })

  const verifyBackupMutation = useMutation({
    mutationFn: () => verifyBackup(backupIdToVerify.trim()).then((r) => r.data.data),
    onSuccess: (result) => {
      setVerifyBackupFeedback({ tone: 'success', message: `Backup verified: ${result.backup_id}` })
      void queryClient.invalidateQueries({ queryKey: ['recovery', 'safety-status'] })
    },
    onError: (err) => {
      setVerifyBackupFeedback({ tone: 'error', message: errorMessage(err, 'Backup verification failed.') })
    },
  })

  const keyMutation = useMutation({
    mutationFn: () => verifyRecoveryKey(recoveryKey).then((r) => r.data.data),
    onSuccess: () => {
      setKeyFeedback({ tone: 'success', message: 'Recovery key verified.' })
      setRecoveryKey('')
    },
    onError: (err) => {
      setKeyFeedback({ tone: 'error', message: errorMessage(err, 'Recovery key verification failed.') })
    },
  })

  const previewMutation = useMutation({
    mutationFn: () =>
      previewRestore({
        backup_id: previewBackupId.trim(),
        recovery_key: previewRecoveryKey.trim() || null,
      }).then((r) => r.data.data),
    onSuccess: (result) => {
      setPreview(result)
      setPreviewFeedback(null)
    },
    onError: (err) => {
      setPreview(null)
      setPreviewFeedback({ tone: 'error', message: errorMessage(err, 'Restore preview failed.') })
    },
  })

  const safetyStatus = data?.status

  return (
    <div className="space-y-8">
      <section className="space-y-4">
        <div>
          <h2 className="font-display text-base font-semibold text-text-primary">
            Workspace Safety
          </h2>
          <p className="mt-1 text-sm font-ui text-text-muted max-w-2xl">
            Backups are encrypted. A recovery key is required for portable restore.
            Destructive workspace actions require a recent verified backup. Restore preview checks a backup and does not change data.
          </p>
        </div>

        {isLoading && <p className="text-sm font-ui text-text-muted">Loading safety status…</p>}
        {isError && <p className="text-sm font-ui text-risk-high">Unable to load backup safety status.</p>}
        {data && (
          <div className="rounded-md border border-border bg-surface p-4 space-y-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-ui font-semibold text-text-primary">Backup safety status</p>
              <span className={`rounded-full border px-3 py-1 text-xs font-ui font-semibold ${statusClass(data.status)}`}>
                {statusLabel(data.status)}
              </span>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <SummaryRow label="Last backup" value={formatDate(data.last_backup_at)} />
              <SummaryRow label="Last verified" value={formatDate(data.last_verified_at)} />
              <SummaryRow label="Policy window" value={`${data.policy_window_hours} hours`} />
              <SummaryRow
                label="Guard enabled"
                value={data.requires_backup_before_dangerous_action ? 'Yes' : 'No'}
              />
            </div>
          </div>
        )}
        {!data && !isLoading && !isError && (
          <p className="text-sm font-ui text-text-muted">Backup safety status is not available.</p>
        )}
        {safetyStatus === 'missing' && (
          <p className="text-sm font-ui text-review">
            Create and verify a backup before deleting or overwriting workspace data.
          </p>
        )}
      </section>

      <section className="space-y-3">
        <h3 className="font-display text-base font-semibold text-text-primary">Backup Workspace</h3>
        <p className="text-sm font-ui text-text-muted">
          Creates an encrypted .trb backup artifact for this workspace.
        </p>
        <button
          type="button"
          onClick={() => backupMutation.mutate()}
          disabled={backupMutation.isPending}
          className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50 inline-flex items-center gap-2"
        >
          <Archive className="h-4 w-4" aria-hidden="true" />
          {backupMutation.isPending ? 'Creating backup…' : 'Backup Workspace'}
        </button>
        <FeedbackText feedback={backupFeedback} />
      </section>

      <section className="space-y-3 max-w-xl">
        <h3 className="font-display text-base font-semibold text-text-primary">Verify Backup</h3>
        <p className="text-sm font-ui text-text-muted">
          Verifies encryption and checksums for an existing backup artifact.
        </p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="flex-1">
            <label htmlFor="backup-id-verify" className="text-sm font-ui text-text-body block mb-1">
              Backup ID to verify
            </label>
            <input
              id="backup-id-verify"
              type="text"
              value={backupIdToVerify}
              onChange={(event) => setBackupIdToVerify(event.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
            />
          </div>
          <button
            type="button"
            onClick={() => verifyBackupMutation.mutate()}
            disabled={verifyBackupMutation.isPending || !backupIdToVerify.trim()}
            className="min-h-11 px-5 rounded-md border border-border text-text-primary text-sm font-ui font-semibold disabled:opacity-50 inline-flex items-center justify-center gap-2 sm:self-end"
          >
            <CheckCircle className="h-4 w-4" aria-hidden="true" />
            {verifyBackupMutation.isPending ? 'Verifying…' : 'Verify Backup'}
          </button>
        </div>
        <FeedbackText feedback={verifyBackupFeedback} />
      </section>

      <section className="space-y-3 max-w-xl">
        <h3 className="font-display text-base font-semibold text-text-primary">Verify Recovery Key</h3>
        <p className="text-sm font-ui text-text-muted">
          Checks the key without changing workspace data. The key is not logged.
        </p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="flex-1">
            <label htmlFor="recovery-key" className="text-sm font-ui text-text-body block mb-1">
              Recovery key
            </label>
            <input
              id="recovery-key"
              type="password"
              value={recoveryKey}
              onChange={(event) => setRecoveryKey(event.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
            />
          </div>
          <button
            type="button"
            onClick={() => keyMutation.mutate()}
            disabled={keyMutation.isPending || !recoveryKey}
            className="min-h-11 px-5 rounded-md border border-border text-text-primary text-sm font-ui font-semibold disabled:opacity-50 inline-flex items-center justify-center gap-2 sm:self-end"
          >
            <KeyRound className="h-4 w-4" aria-hidden="true" />
            {keyMutation.isPending ? 'Verifying…' : 'Verify Recovery Key'}
          </button>
        </div>
        <FeedbackText feedback={keyFeedback} />
      </section>

      <section className="space-y-3 max-w-2xl">
        <h3 className="font-display text-base font-semibold text-text-primary">Restore Preview</h3>
        <p className="text-sm font-ui text-text-muted">
          Preview only; no data is changed.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="restore-preview-backup-id" className="text-sm font-ui text-text-body block mb-1">
              Backup ID for restore preview
            </label>
            <input
              id="restore-preview-backup-id"
              type="text"
              value={previewBackupId}
              onChange={(event) => setPreviewBackupId(event.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
            />
          </div>
          <div>
            <label htmlFor="restore-preview-key" className="text-sm font-ui text-text-body block mb-1">
              Recovery key if required
            </label>
            <input
              id="restore-preview-key"
              type="password"
              value={previewRecoveryKey}
              onChange={(event) => setPreviewRecoveryKey(event.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
            />
          </div>
        </div>
        <button
          type="button"
          onClick={() => previewMutation.mutate()}
          disabled={previewMutation.isPending || !previewBackupId.trim()}
          className="min-h-11 px-5 rounded-md border border-border text-text-primary text-sm font-ui font-semibold disabled:opacity-50 inline-flex items-center gap-2"
        >
          <Search className="h-4 w-4" aria-hidden="true" />
          {previewMutation.isPending ? 'Previewing…' : 'Preview Restore'}
        </button>
        <FeedbackText feedback={previewFeedback} />
        <PreviewResult preview={preview} />
      </section>
    </div>
  )
}
