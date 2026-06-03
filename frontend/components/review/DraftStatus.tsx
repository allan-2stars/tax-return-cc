'use client'

interface DraftStatusProps {
  notice: 'found' | 'saved' | null
  hasRestorableDraft: boolean
  onRestore: () => void
  onDiscard: () => void
}

export default function DraftStatus({
  notice,
  hasRestorableDraft,
  onRestore,
  onDiscard,
}: DraftStatusProps) {
  if (notice === 'found' && hasRestorableDraft) {
    return (
      <div className="rounded-md border border-review bg-review-bg p-3 space-y-2">
        <p className="text-sm font-ui text-text-body">Draft found.</p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onRestore}
            className="text-sm font-ui text-accent underline"
          >
            Restore draft
          </button>
          <button
            type="button"
            onClick={onDiscard}
            className="text-sm font-ui text-text-muted underline"
          >
            Discard draft
          </button>
        </div>
      </div>
    )
  }

  if (notice === 'saved') {
    return <p className="text-xs font-ui text-ready">Draft saved.</p>
  }

  return null
}
