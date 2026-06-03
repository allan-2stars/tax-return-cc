import { useState } from 'react'

interface BulkActionItem {
  id: string
  title?: string | null
  amount?: number | null
  date?: string | null
}

interface BulkActionBarProps {
  items: BulkActionItem[]
  groupLabel: string
  onBulkConfirm: (ids: string[]) => void
}

function formatAmount(amount?: number | null) {
  if (amount == null) return '—'
  return amount.toLocaleString('en-AU', {
    style: 'currency',
    currency: 'AUD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function formatDate(date?: string | null) {
  if (!date) return '—'
  const parsed = new Date(date)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function BulkActionBar({ items, groupLabel, onBulkConfirm }: BulkActionBarProps) {
  const [confirming, setConfirming] = useState(false)

  if (items.length < 2) return null

  const itemIds = items.map((item) => item.id)
  const totalAmount = items.reduce((total, item) => total + (item.amount ?? 0), 0)
  const hasAmount = items.some((item) => item.amount != null)

  function handleConfirm() {
    setConfirming(false)
    onBulkConfirm(itemIds)
  }

  return (
    <>
      <div className="flex items-center justify-between gap-3 rounded-md bg-review-bg border border-review px-4 py-3">
        <p className="text-sm font-ui text-review">
          <span className="font-medium">{items.length} items</span> share the same description:{' '}
          <span className="italic">{groupLabel}</span>
        </p>
        <button
          type="button"
          onClick={() => setConfirming(true)}
          className="shrink-0 min-h-11 px-4 py-2 rounded text-sm font-ui font-medium bg-ready text-surface hover:opacity-90 transition-opacity"
        >
          Confirm all
        </button>
      </div>

      {confirming && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="bulk-confirm-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4"
        >
          <div className="w-full max-w-lg rounded-lg bg-surface p-5 shadow-lg space-y-4">
            <div>
              <h2 id="bulk-confirm-title" className="font-display text-xl font-semibold text-text-primary">
                Confirm all review items
              </h2>
              <p className="mt-2 text-sm font-ui text-review">
                You&apos;re about to confirm {items.length} review items. Confirm only if all displayed items are correct.
              </p>
            </div>

            <div className="max-h-72 overflow-y-auto rounded-md border border-border">
              <ul className="divide-y divide-border">
                {items.map((item) => (
                  <li key={item.id} className="p-3">
                    <p className="text-sm font-ui font-medium text-text-primary">
                      {item.title ?? item.id}
                    </p>
                    <p className="text-xs font-ui text-text-muted">
                      {formatAmount(item.amount)} · {formatDate(item.date)}
                    </p>
                  </li>
                ))}
              </ul>
            </div>

            {hasAmount && (
              <p className="text-sm font-ui text-text-body">
                Total amount: {formatAmount(totalAmount)}
              </p>
            )}

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirming(false)}
                className="px-4 py-2 rounded text-sm font-ui font-medium border border-border text-text-body hover:bg-surface-raised transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                className="px-4 py-2 rounded text-sm font-ui font-medium bg-ready text-surface hover:opacity-90 transition-opacity"
              >
                Confirm All
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
