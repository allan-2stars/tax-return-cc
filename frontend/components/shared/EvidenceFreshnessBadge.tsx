import type { EvidenceFreshness } from '@/lib/api/types'

const LABELS = {
  fresh: 'Fresh',
  reconciling: 'Reconciling',
  stale: 'Stale',
  failed: 'Failed',
}

const CLASSES = {
  fresh: 'border-ready bg-ready-bg text-ready',
  reconciling: 'border-review bg-review-bg text-review',
  stale: 'border-review bg-review-bg text-review',
  failed: 'border-risk-high bg-risk-bg text-risk-high',
}

function formatDate(value?: string | null) {
  if (!value) return null
  return new Date(value).toLocaleString()
}

export default function EvidenceFreshnessBadge({
  freshness,
  compact = false,
}: {
  freshness?: EvidenceFreshness | null
  compact?: boolean
}) {
  if (!freshness) return null

  const state = freshness.freshness_state ?? 'stale'
  const label = LABELS[state] ?? state
  const lastReconciled = formatDate(freshness.last_reconciled_at ?? freshness.evidence_reconciled_at)
  const lastAttempted = formatDate(freshness.last_attempted_at)
  const lastFailure = formatDate(freshness.last_failure_at)

  return (
    <div className="space-y-1">
      <span className={`inline-flex rounded-full border px-2 py-1 text-xs font-ui font-medium ${CLASSES[state]}`}>
        {label}
      </span>
      {!compact && (
        <div className="space-y-0.5 text-xs font-ui text-text-muted">
          {lastReconciled && <p>Last reconciled: {lastReconciled}</p>}
          {lastAttempted && <p>Last attempted: {lastAttempted}</p>}
          {lastFailure && <p>Last failed: {lastFailure}</p>}
          {freshness.freshness_reason && <p>{freshness.freshness_reason}</p>}
        </div>
      )}
    </div>
  )
}
