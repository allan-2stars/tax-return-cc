import { useState } from 'react'
import type { EvidenceMatchItem, EvidenceObligation, EvidenceObligationStatus } from '@/lib/api/types'

const STATUS_LABELS: Record<EvidenceObligationStatus, string> = {
  missing: 'Missing',
  partially_matched: 'Partially matched',
  matched: 'Matched',
  waived: 'Waived',
  not_applicable: 'Not applicable',
}

function statusClass(status: EvidenceObligationStatus): string {
  if (status === 'missing') return 'text-risk-high'
  if (status === 'partially_matched') return 'text-review'
  if (status === 'matched') return 'text-ready'
  return 'text-text-muted'
}

function matchLine(match: EvidenceMatchItem): string {
  if (match.document) {
    return `${match.document.original_filename} (${match.document.document_type ?? 'document'}, ${match.document.status})`
  }
  if (match.tax_event) {
    return `${match.tax_event.category} (${match.tax_event.event_type}, ${match.tax_event.status})`
  }
  return 'Manual match'
}

function matchHistoryLabel(match: EvidenceMatchItem): string {
  if (match.document) {
    return match.document.original_filename
  }
  if (match.tax_event) {
    return match.tax_event.category
  }
  return 'manual match'
}

function formatHistoryTransition(previousStatus: string | null, newStatus: string | null): string {
  if (!previousStatus && !newStatus) return 'Status updated'
  if (!previousStatus) return newStatus ?? 'updated'
  if (!newStatus) return `${previousStatus} → cleared`
  return `${previousStatus} → ${newStatus}`
}

function isUndoableMatch(match: EvidenceMatchItem): boolean {
  if (!['accepted', 'rejected'].includes(match.status)) return false
  const latest = match.decision_history[0]
  if (!latest) return false
  return ['accepted', 'rejected'].includes(latest.action) && latest.new_status === match.status
}

export default function EvidenceChecklist({
  obligations,
  onDecideMatch,
  onUndoMatch,
  decidingMatchId,
}: {
  obligations: EvidenceObligation[]
  onDecideMatch?: (matchId: string, status: 'accepted' | 'rejected') => void
  onUndoMatch?: (matchId: string) => void
  decidingMatchId?: string | null
}) {
  const [expandedExplanationIds, setExpandedExplanationIds] = useState<Record<string, boolean>>({})
  const [expandedHistoryIds, setExpandedHistoryIds] = useState<Record<string, boolean>>({})
  const grouped = obligations.reduce<Record<string, EvidenceObligation[]>>((acc, item) => {
    const key = item.category || 'other'
    acc[key] = acc[key] || []
    acc[key].push(item)
    return acc
  }, {})

  const categories = Object.keys(grouped).sort((a, b) => a.localeCompare(b))

  if (obligations.length === 0) {
    return (
      <div className="bg-surface rounded-lg shadow-sm p-6">
        <p className="text-sm font-ui text-text-muted">No checklist items yet. Reconcile after journey or evidence updates.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {categories.map((category) => (
        <section key={category} className="bg-surface rounded-lg shadow-sm p-6 space-y-4">
          <h2 className="font-ui text-sm font-semibold text-text-primary capitalize">{category.replaceAll('_', ' ')}</h2>
          <div className="space-y-3">
            {grouped[category].map((item) => (
              <article key={item.id} className="border border-border rounded-md p-4 space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-ui font-medium text-text-primary">{item.label}</p>
                    {item.reason && <p className="text-xs font-ui text-text-muted">{item.reason}</p>}
                    {item.explanation?.what_user_should_check && (
                      <p className="text-xs font-ui text-text-body">
                        <span className="text-text-muted">What to check: </span>
                        {item.explanation.what_user_should_check}
                      </p>
                    )}
                    {item.explanation && (
                      <div className="mt-1">
                        <p className="text-xs font-ui text-text-body">{item.explanation.plain_english_summary}</p>
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedExplanationIds((prev) => ({ ...prev, [item.id]: !prev[item.id] }))
                          }
                          className="mt-1 text-xs font-ui text-text-muted hover:text-text-body transition-colors"
                        >
                          {expandedExplanationIds[item.id] ? 'Hide details ↑' : 'Why this matters ↓'}
                        </button>
                        {expandedExplanationIds[item.id] && (
                          <div data-testid={`evidence-explanation-${item.id}`} className="mt-2 p-2 rounded bg-surface-raised text-xs font-ui text-text-muted space-y-1">
                            <p><span className="text-text-body">Why this matters: </span>{item.explanation.why_it_matters}</p>
                            <p><span className="text-text-body">What to check: </span>{item.explanation.what_user_should_check}</p>
                            {item.explanation.evidence_expected.length > 0 && (
                              <p>
                                <span className="text-text-body">Expected evidence: </span>
                                {item.explanation.evidence_expected.join(', ')}
                              </p>
                            )}
                            {item.explanation.rule_version && (
                              <p>
                                <span className="text-text-body">Rule version: </span>
                                {item.explanation.rule_version}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <p className={`text-xs font-ui font-medium ${statusClass(item.status)}`}>{STATUS_LABELS[item.status]}</p>
                    <p className="text-xs font-ui text-text-muted capitalize">{item.required_level}</p>
                  </div>
                </div>

                {item.matches.length > 0 && (
                  <div className="space-y-1">
                    {item.matches.map((match) => (
                      <div key={match.id} className="space-y-1">
                        <p className="text-xs font-ui text-text-body">
                          {match.status === 'candidate'
                            ? 'Possible match found: '
                            : match.status === 'rejected'
                            ? 'Rejected match: '
                            : 'Matched by: '}
                          {matchLine(match)}
                        </p>
                        {match.status === 'candidate' && onDecideMatch && (
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => onDecideMatch(match.id, 'accepted')}
                              disabled={decidingMatchId === match.id}
                              className="text-xs font-ui text-ready hover:underline disabled:opacity-60"
                            >
                              Accept match
                            </button>
                            <button
                              type="button"
                              onClick={() => onDecideMatch(match.id, 'rejected')}
                              disabled={decidingMatchId === match.id}
                              className="text-xs font-ui text-risk-high hover:underline disabled:opacity-60"
                            >
                              Reject match
                            </button>
                          </div>
                        )}
                        {isUndoableMatch(match) && onUndoMatch && (
                          <button
                            type="button"
                            onClick={() => onUndoMatch(match.id)}
                            disabled={decidingMatchId === match.id}
                            className="text-xs font-ui text-accent hover:underline disabled:opacity-60"
                          >
                            Undo last match decision
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedHistoryIds((prev) => ({ ...prev, [match.id]: !prev[match.id] }))
                          }
                          className="text-xs font-ui text-text-muted hover:text-text-body transition-colors"
                          aria-label={`Match history for ${matchHistoryLabel(match)}`}
                        >
                          {expandedHistoryIds[match.id] ? 'Hide match history ↑' : 'Match history ↓'}
                        </button>
                        {expandedHistoryIds[match.id] && (
                          <div className="rounded bg-surface-raised p-2 space-y-2">
                            {match.decision_history.length === 0 ? (
                              <p className="text-xs font-ui text-text-muted">No match history yet.</p>
                            ) : (
                              match.decision_history.map((history) => (
                                <div key={history.id} className="space-y-1 text-xs font-ui text-text-body">
                                  <p className="font-medium">
                                    {history.action}
                                    {history.actor ? ` · ${history.actor}` : ''}
                                  </p>
                                  <p className="text-text-muted">
                                    {formatHistoryTransition(history.previous_status, history.new_status)}
                                  </p>
                                  {history.note && <p>{history.note}</p>}
                                  {history.created_at && (
                                    <p className="text-text-muted">
                                      {new Date(history.created_at).toLocaleString()}
                                    </p>
                                  )}
                                </div>
                              ))
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
