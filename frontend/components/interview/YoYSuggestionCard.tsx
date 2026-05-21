import type { YoYSuggestion } from '@/lib/api/types'

interface Props {
  suggestion: YoYSuggestion
  onAction: (id: string, action: 'confirmed' | 'dismissed' | 'not_applicable') => void
}

export default function YoYSuggestionCard({ suggestion, onAction }: Props) {
  return (
    <div className="bg-surface border border-border rounded-md p-4 space-y-3">
      <p className="font-ui text-text-body">{suggestion.description}</p>
      {suggestion.amount_last_year != null && (
        <p className="font-mono text-sm text-text-muted">
          ${suggestion.amount_last_year.toFixed(2)} last year
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onAction(suggestion.id, 'confirmed')}
          className="px-4 py-2 rounded-sm bg-ready-bg text-ready text-sm font-ui hover:opacity-80 transition-opacity"
        >
          Yes, still use it
        </button>
        <button
          type="button"
          onClick={() => onAction(suggestion.id, 'dismissed')}
          className="px-4 py-2 rounded-sm bg-surface border border-border text-text-muted text-sm font-ui hover:border-border-strong transition-colors"
        >
          No longer
        </button>
        <button
          type="button"
          onClick={() => onAction(suggestion.id, 'not_applicable')}
          className="px-4 py-2 rounded-sm bg-surface border border-border text-text-muted text-sm font-ui hover:border-border-strong transition-colors"
        >
          Already added
        </button>
      </div>
    </div>
  )
}
