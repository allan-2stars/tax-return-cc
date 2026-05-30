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

export default function EvidenceChecklist({
  obligations,
  onDecideMatch,
  decidingMatchId,
}: {
  obligations: EvidenceObligation[]
  onDecideMatch?: (matchId: string, status: 'accepted' | 'rejected') => void
  decidingMatchId?: string | null
}) {
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
