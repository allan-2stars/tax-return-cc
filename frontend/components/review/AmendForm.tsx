'use client'
import { useState } from 'react'
import type { ReviewItem } from '@/lib/api/types'

const SKILL_CATEGORIES: Record<string, string[]> = {
  employee_tax_au: [
    'payg_income', 'allowance', 'lump_sum', 'bank_interest', 'investment_income_basic',
    'work_expense', 'work_subscription', 'work_equipment', 'vehicle', 'travel',
    'uniform', 'self_education', 'other_deduction', 'donation', 'private_health_rebate',
    'wfh_deduction',
  ],
}

const ALL_CATEGORIES = Array.from(new Set(Object.values(SKILL_CATEGORIES).flat()))

const CATEGORY_LABELS: Record<string, string> = {
  payg_income: 'PAYG Income',
  allowance: 'Allowance',
  lump_sum: 'Lump Sum',
  bank_interest: 'Bank Interest',
  investment_income_basic: 'Investment Income',
  work_expense: 'Work Expense',
  work_subscription: 'Work Subscription',
  work_equipment: 'Work Equipment',
  vehicle: 'Vehicle',
  travel: 'Travel',
  uniform: 'Uniform / Clothing',
  self_education: 'Self-Education',
  other_deduction: 'Other Deduction',
  donation: 'Donation',
  private_health_rebate: 'Private Health Rebate',
  wfh_deduction: 'Work From Home',
}

interface AmendFormProps {
  item: ReviewItem
  onSave: (amount: number | undefined, category: string | undefined, note: string | undefined) => void
  onCancel: () => void
}

export default function AmendForm({ item, onSave, onCancel }: AmendFormProps) {
  const [amount, setAmount] = useState<string>(
    (item.amended_amount ?? item.amount)?.toString() ?? ''
  )
  const [category, setCategory] = useState<string>(
    item.amended_category ?? item.category ?? ''
  )
  const [note, setNote] = useState<string>(item.user_note ?? '')

  const categories = item.skill_id
    ? (SKILL_CATEGORIES[item.skill_id] ?? ALL_CATEGORIES)
    : ALL_CATEGORIES

  function handleSave() {
    const parsedAmount = amount !== '' ? parseFloat(amount) : undefined
    onSave(parsedAmount, category || undefined, note || undefined)
  }

  return (
    <div data-testid="amend-form" className="space-y-3">
      <div>
        <label htmlFor="amend-amount" className="block text-xs font-ui text-text-muted mb-1">
          Amount ($)
        </label>
        <input
          id="amend-amount"
          type="number"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          aria-label="Amount"
          className="w-full border border-border rounded px-3 py-2 text-sm font-mono bg-surface text-text-body focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>

      <div>
        <label htmlFor="amend-category" className="block text-xs font-ui text-text-muted mb-1">
          Category
        </label>
        <select
          id="amend-category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          aria-label="Category"
          className="w-full border border-border rounded px-3 py-2 text-sm font-ui bg-surface text-text-body focus:outline-none focus:ring-1 focus:ring-accent"
        >
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {CATEGORY_LABELS[cat] ?? cat}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="amend-note" className="block text-xs font-ui text-text-muted mb-1">
          Note (optional)
        </label>
        <textarea
          id="amend-note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          aria-label="Note"
          className="w-full border border-border rounded px-3 py-2 text-sm font-ui bg-surface text-text-body focus:outline-none focus:ring-1 focus:ring-accent resize-none"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleSave}
          className="px-4 py-2 rounded text-sm font-ui font-medium bg-ready text-surface hover:opacity-90 transition-opacity"
        >
          Save
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded text-sm font-ui font-medium border border-border text-text-body hover:bg-surface-raised transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
