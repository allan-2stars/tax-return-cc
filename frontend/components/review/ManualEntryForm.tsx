'use client'
import { useState } from 'react'
import { createManualEvent } from '@/lib/api/events'
import type { ManualEventFrequency, ManualEventType, InvestmentSubType } from '@/lib/api/types'
import { validateDate } from '@/lib/utils/fy'
import useWorkspaceStore from '@/lib/stores/workspace.store'
import SharesForm from './investment/SharesForm'
import CryptoForm from './investment/CryptoForm'
import BankInterestForm from './investment/BankInterestForm'
import ManagedFundForm from './investment/ManagedFundForm'
import ForeignIncomeForm from './investment/ForeignIncomeForm'

const TYPE_OPTIONS: { value: ManualEventType; label: string; description: string }[] = [
  { value: 'income', label: 'Income', description: 'Wages, allowances, interest' },
  { value: 'deduction', label: 'Deduction', description: 'Work expenses, subscriptions' },
  { value: 'investment', label: 'Investment', description: 'Dividends, capital gains, crypto' },
  { value: 'other', label: 'Other', description: 'Anything else' },
]

const TYPE_CATEGORIES: Record<ManualEventType, string[]> = {
  income: ['payg_income', 'allowance', 'lump_sum', 'bank_interest', 'investment_income_basic'],
  deduction: [
    'work_expense', 'work_subscription', 'work_equipment', 'vehicle', 'travel',
    'uniform', 'self_education', 'other_deduction', 'donation', 'wfh_deduction',
  ],
  investment: ['dividend', 'capital_gain', 'capital_loss', 'crypto'],
  wfh: ['wfh_deduction'],
  other: ['other_deduction'],
}

interface Period {
  months: number
  amount_per_month: number
}

interface Props {
  onSuccess: () => void
  onCancel: () => void
}

export default function ManualEntryForm({ onSuccess, onCancel }: Props) {
  const { financialYear } = useWorkspaceStore()
  const [step, setStep] = useState<1 | 2>(1)
  const [eventType, setEventType] = useState<ManualEventType | null>(null)
  const [investmentSubType, setInvestmentSubType] = useState<InvestmentSubType | null>(null)
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState('')
  const [date, setDate] = useState('')
  const [frequency, setFrequency] = useState<ManualEventFrequency>('one_off')
  const [periods, setPeriods] = useState<Period[]>([{ months: 1, amount_per_month: 0 }])
  const [note, setNote] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isMonthly = frequency === 'monthly'
  const monthlyTotal = periods.reduce((sum, p) => sum + p.months * p.amount_per_month, 0)

  function updatePeriod(idx: number, field: keyof Period, value: number) {
    setPeriods((prev) => {
      const next = [...prev]
      next[idx] = { ...next[idx], [field]: value }
      return next
    })
  }

  const dateValidation = validateDate(date, financialYear ?? null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!eventType) return
    if (dateValidation.error) return
    setPending(true)
    setError(null)
    try {
      await createManualEvent({
        event_type: eventType,
        category,
        description,
        amount: isMonthly ? monthlyTotal : parseFloat(amount),
        date,
        frequency,
        note: note.trim() || null,
        periods: isMonthly
          ? periods.map((p) => ({ months: p.months, amount_per_month: p.amount_per_month }))
          : null,
      })
      onSuccess()
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setPending(false)
    }
  }

  if (step === 1) {
    return (
      <div className="space-y-4">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          What would you like to add?
        </h2>
        <div className="space-y-2">
          {TYPE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className="w-full text-left rounded-lg border border-border bg-surface p-4 min-h-14 hover:border-accent transition-colors"
              onClick={() => {
                setEventType(opt.value)
                setCategory(TYPE_CATEGORIES[opt.value][0])
                setInvestmentSubType(null)
                setStep(2)
              }}
            >
              <p className="font-ui font-semibold text-text-primary">{opt.label}</p>
              <p className="text-sm font-ui text-text-muted">{opt.description}</p>
            </button>
          ))}
        </div>
        <button
          type="button"
          className="text-sm font-ui text-text-muted"
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
    )
  }

  // Investment: sub-type selector
  if (step === 2 && eventType === 'investment' && investmentSubType === null) {
    return (
      <div className="space-y-4">
        <button type="button" onClick={() => setStep(1)} className="text-sm font-ui text-text-muted">← Back</button>
        <h2 className="font-display text-xl font-semibold text-text-primary">What type of investment?</h2>
        <div className="space-y-2">
          {(
            [
              { value: 'shares', label: 'Shares / ETF', description: 'Buy, sell, or dividend transactions' },
              { value: 'crypto', label: 'Cryptocurrency', description: 'Buy, sell, or staking income' },
              { value: 'bank_interest', label: 'Bank Interest', description: 'Savings, term deposits, offset accounts' },
              { value: 'managed_fund', label: 'Managed Fund', description: 'Fund distributions and tax statements' },
              { value: 'foreign_income', label: 'Foreign Income / Investment', description: 'Income from overseas investments' },
              { value: 'other', label: 'Other Investment', description: 'Anything not covered above' },
            ] as { value: InvestmentSubType; label: string; description: string }[]
          ).map((opt) => (
            <button
              key={opt.value}
              type="button"
              className="w-full text-left rounded-lg border border-border bg-surface p-4 min-h-14 hover:border-accent transition-colors"
              onClick={() => setInvestmentSubType(opt.value)}
            >
              <p className="font-ui font-semibold text-text-primary">{opt.label}</p>
              <p className="text-sm font-ui text-text-muted">{opt.description}</p>
            </button>
          ))}
        </div>
        <button
          type="button"
          className="text-sm font-ui text-text-muted"
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
    )
  }

  // Investment: specific sub-form
  if (step === 2 && eventType === 'investment' && investmentSubType !== null && investmentSubType !== 'other') {
    const backToSubType = () => setInvestmentSubType(null)
    if (investmentSubType === 'shares') return <SharesForm onSuccess={onSuccess} onBack={backToSubType} onCancel={onCancel} />
    if (investmentSubType === 'crypto') return <CryptoForm onSuccess={onSuccess} onBack={backToSubType} onCancel={onCancel} />
    if (investmentSubType === 'bank_interest') return <BankInterestForm onSuccess={onSuccess} onBack={backToSubType} onCancel={onCancel} />
    if (investmentSubType === 'managed_fund') return <ManagedFundForm onSuccess={onSuccess} onBack={backToSubType} onCancel={onCancel} />
    if (investmentSubType === 'foreign_income') return <ForeignIncomeForm onSuccess={onSuccess} onBack={backToSubType} onCancel={onCancel} />
  }

  const categories = TYPE_CATEGORIES[eventType!]

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setStep(1)}
          className="text-sm font-ui text-text-muted"
        >
          ← Back
        </button>
        <h2 className="font-display text-xl font-semibold text-text-primary">
          {TYPE_OPTIONS.find((o) => o.value === eventType)?.label} details
        </h2>
      </div>

      <div>
        <label htmlFor="manual-category" className="text-sm font-ui text-text-body block mb-1">
          Category
        </label>
        <select
          id="manual-category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          aria-label="Category"
        >
          {categories.map((c) => (
            <option key={c} value={c}>
              {c.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="manual-desc" className="text-sm font-ui text-text-body block mb-1">
          Description
        </label>
        <input
          id="manual-desc"
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          aria-label="Description"
          required
        />
      </div>

      <div>
        <p className="text-sm font-ui text-text-body mb-1">Frequency</p>
        <div className="flex gap-2 flex-wrap">
          {(['one_off', 'annual', 'monthly'] as ManualEventFrequency[]).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFrequency(f)}
              className={`px-3 py-1 rounded-full text-sm font-ui border transition-colors ${
                frequency === f
                  ? 'border-accent text-accent bg-accent-soft'
                  : 'border-border text-text-muted'
              }`}
            >
              {f === 'one_off' ? 'One-off' : f === 'annual' ? 'Annual' : 'Monthly'}
            </button>
          ))}
        </div>
      </div>

      {!isMonthly && (
        <div>
          <label htmlFor="manual-amount" className="text-sm font-ui text-text-body block mb-1">
            Amount (AUD)
          </label>
          <input
            id="manual-amount"
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
            aria-label="Amount"
            step="0.01"
            min="0"
            required
          />
        </div>
      )}

      {isMonthly && (
        <div className="space-y-3">
          <p className="text-sm font-ui text-text-body">Pricing periods</p>
          {periods.map((period, idx) => (
            <div key={idx} className="flex gap-3 items-end flex-wrap">
              <div>
                <label
                  htmlFor={`period-${idx}-months`}
                  className="text-xs font-ui text-text-muted block mb-1"
                >
                  Months
                </label>
                <input
                  id={`period-${idx}-months`}
                  type="number"
                  value={period.months}
                  onChange={(e) => updatePeriod(idx, 'months', parseInt(e.target.value) || 1)}
                  className="w-20 rounded-md border border-border bg-surface px-2 py-1 text-sm font-mono"
                  min="1"
                  aria-label={`Period ${idx + 1} months`}
                />
              </div>
              <div>
                <label
                  htmlFor={`period-${idx}-amount`}
                  className="text-xs font-ui text-text-muted block mb-1"
                >
                  $/month
                </label>
                <input
                  id={`period-${idx}-amount`}
                  type="number"
                  value={period.amount_per_month}
                  onChange={(e) =>
                    updatePeriod(idx, 'amount_per_month', parseFloat(e.target.value) || 0)
                  }
                  className="w-28 rounded-md border border-border bg-surface px-2 py-1 text-sm font-mono"
                  step="0.01"
                  min="0"
                  aria-label={`Period ${idx + 1} amount per month`}
                />
              </div>
              {periods.length > 1 && (
                <button
                  type="button"
                  onClick={() => setPeriods((prev) => prev.filter((_, i) => i !== idx))}
                  className="text-sm font-ui text-text-muted pb-1"
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={() =>
              setPeriods((prev) => [...prev, { months: 1, amount_per_month: 0 }])
            }
            className="text-sm font-ui text-accent"
          >
            + Add pricing period
          </button>
          <p className="text-sm font-mono text-text-body font-semibold">
            FY total: ${monthlyTotal.toFixed(2)}
          </p>
        </div>
      )}

      <div>
        <label htmlFor="manual-date" className="text-sm font-ui text-text-body block mb-1">
          Date
        </label>
        <input
          id="manual-date"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className={`w-full rounded-md border bg-surface px-3 py-2 text-sm font-mono ${
            dateValidation.error ? 'border-risk-high' : 'border-border'
          }`}
          aria-label="Date"
          required
        />
        {dateValidation.error && (
          <p role="alert" className="text-sm font-ui text-risk-high mt-1">{dateValidation.error}</p>
        )}
        {!dateValidation.error && dateValidation.warning && (
          <p className="text-sm font-ui text-review mt-1">⚠ {dateValidation.warning}</p>
        )}
      </div>

      <div>
        <label htmlFor="manual-note" className="text-sm font-ui text-text-body block mb-1">
          Note (optional)
        </label>
        <input
          id="manual-note"
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          aria-label="Note"
        />
      </div>

      {error && (
        <p className="text-sm font-ui text-risk-high">{error}</p>
      )}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={pending}
          className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
        >
          {pending ? 'Saving…' : 'Add item'}
        </button>
      </div>
      <button
        type="button"
        onClick={onCancel}
        className="text-sm font-ui text-text-muted"
      >
        Cancel
      </button>
    </form>
  )
}
