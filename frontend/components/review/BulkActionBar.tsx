interface BulkActionBarProps {
  itemIds: string[]
  groupLabel: string
  onBulkConfirm: (ids: string[]) => void
}

export default function BulkActionBar({ itemIds, groupLabel, onBulkConfirm }: BulkActionBarProps) {
  if (itemIds.length < 2) return null

  return (
    <div className="flex items-center justify-between gap-3 rounded-md bg-review-bg border border-review px-4 py-3">
      <p className="text-sm font-ui text-review">
        <span className="font-medium">{itemIds.length} items</span> share the same description:{' '}
        <span className="italic">{groupLabel}</span>
      </p>
      <button
        type="button"
        onClick={() => onBulkConfirm(itemIds)}
        className="shrink-0 min-h-11 px-4 py-2 rounded text-sm font-ui font-medium bg-ready text-surface hover:opacity-90 transition-opacity"
      >
        Confirm all
      </button>
    </div>
  )
}
