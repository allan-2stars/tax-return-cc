import type { ReviewItem } from '@/lib/api/types'

interface AmendFormProps {
  item: ReviewItem
  onSave: (amount: number | undefined, category: string | undefined, note: string | undefined) => void
  onCancel: () => void
}

export default function AmendForm({ onCancel }: AmendFormProps) {
  return (
    <div data-testid="amend-form">
      <button type="button" onClick={onCancel}>Cancel</button>
    </div>
  )
}
