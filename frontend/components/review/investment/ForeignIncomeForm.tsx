'use client'
import { useForm } from 'react-hook-form'
import { useState } from 'react'
import { createManualEvent } from '@/lib/api/events'
import { Info } from 'lucide-react'

interface InvestmentFormProps { onSuccess: () => void; onBack: () => void }

interface ForeignIncomeFields {
  country: string; income_type: string
  foreign_amount: string; currency: string; exchange_rate: string
  income_date: string; foreign_tax_paid: string; note: string
}

export default function ForeignIncomeForm({ onSuccess, onBack }: InvestmentFormProps) {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<ForeignIncomeFields>()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const foreignAmountValue = watch('foreign_amount') || ''
  const foreignAmount = parseFloat(foreignAmountValue || '0')
  const exchangeRate = parseFloat(watch('exchange_rate') || '0')
  const audAmount = foreignAmount > 0 && exchangeRate > 0 ? foreignAmount * exchangeRate : null
  const amountLabel = foreignAmountValue ? 'Foreign amount' : 'Amount (foreign currency)'

  async function onSubmit(data: ForeignIncomeFields) {
    const fa = parseFloat(data.foreign_amount)
    const rate = parseFloat(data.exchange_rate)
    const aud = fa * rate
    const ftp = parseFloat(data.foreign_tax_paid || '0') || 0
    setPending(true); setError(null)
    try {
      await createManualEvent({
        event_type: 'investment', category: 'foreign_income',
        description: `Foreign Income: ${data.income_type} from ${data.country}`,
        amount: aud, date: data.income_date,
        frequency: 'one_off', note: data.note?.trim() || null, periods: null,
        review_status: 'needs_agent_review',
        metadata: {
          investment_sub_type: 'foreign_income',
          country: data.country, income_type: data.income_type,
          foreign_amount: fa, currency: data.currency.toUpperCase(),
          exchange_rate: rate, aud_amount: aud,
          income_date: data.income_date, foreign_tax_paid: ftp,
        },
      })
      onSuccess()
    } catch { setError('Something went wrong. Please try again.') }
    finally { setPending(false) }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <button type="button" onClick={onBack} className="text-sm font-ui text-text-muted">← Back</button>
      <div className="rounded-md bg-surface-raised px-4 py-3 text-sm font-ui text-text-muted">
        Foreign income is complex — your tax agent must review this
      </div>
      <div>
        <label htmlFor="fi-country" className="text-sm font-ui text-text-body block mb-1">Country of origin</label>
        <input id="fi-country" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('country', { required: 'Country is required.' })} />
        {errors.country && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.country.message}</p>}
      </div>
      <div>
        <label htmlFor="fi-type" className="text-sm font-ui text-text-body block mb-1">Income type</label>
        <select id="fi-type" className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('income_type', { required: 'Income type is required.' })}>
          <option value="">Select type</option>
          <option value="Dividends">Dividends</option>
          <option value="Interest">Interest</option>
          <option value="Capital gain">Capital gain</option>
          <option value="Employment">Employment</option>
          <option value="Other">Other</option>
        </select>
        {errors.income_type && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.income_type.message}</p>}
      </div>
      <div>
        <label htmlFor="fi-amount" className="text-sm font-ui text-text-body block mb-1">{amountLabel}</label>
        <input id="fi-amount" type="number" min="0" step="0.01"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('foreign_amount', { required: 'Amount is required.' })} />
        {errors.foreign_amount && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.foreign_amount.message}</p>}
      </div>
      <div>
        <label htmlFor="fi-currency" className="text-sm font-ui text-text-body block mb-1">Currency code</label>
        <input id="fi-currency" type="text" placeholder="USD, GBP, HKD…"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui uppercase"
          {...register('currency', { required: 'Currency is required.' })} />
        {errors.currency && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.currency.message}</p>}
      </div>
      <div>
        <div className="flex items-center gap-2 mb-1">
          <label htmlFor="fi-rate" className="text-sm font-ui text-text-body">Exchange rate (AUD)</label>
          <Info size={14} className="text-text-muted" aria-hidden />
        </div>
        <p className="text-xs font-ui text-text-muted italic mb-1">
          Use the ATO&#39;s average annual rate or the rate on the date received
        </p>
        <input id="fi-rate" type="number" min="0" step="0.0001"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('exchange_rate', { required: 'Exchange rate is required.' })} />
        {errors.exchange_rate && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.exchange_rate.message}</p>}
      </div>
      {audAmount !== null && (
        <div className="rounded-md bg-surface-raised px-4 py-2 space-y-0.5">
          <p className="text-xs font-ui text-text-muted uppercase tracking-wide">Amount (AUD)</p>
          <p className="font-mono text-text-muted">${audAmount.toFixed(2)}</p>
          <p className="text-xs font-ui text-text-muted italic">Estimate only — confirm with your tax agent</p>
        </div>
      )}
      <div>
        <label htmlFor="fi-date" className="text-sm font-ui text-text-body block mb-1">Income date</label>
        <input id="fi-date" type="date"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('income_date', { required: 'Income date is required.' })} />
        {errors.income_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.income_date.message}</p>}
      </div>
      <div>
        <div className="flex items-center gap-2 mb-1">
          <label htmlFor="fi-foreign-tax" className="text-sm font-ui text-text-body">Foreign tax paid, AUD equivalent (optional)</label>
          <Info size={14} className="text-text-muted" aria-hidden />
        </div>
        <p className="text-xs font-ui text-text-muted italic mb-1">Foreign tax paid may be credited against your Australian tax</p>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="fi-foreign-tax" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
            {...register('foreign_tax_paid')} />
        </div>
      </div>
      <div>
        <label htmlFor="fi-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="fi-note" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p role="alert" className="text-sm font-ui text-risk-high">{error}</p>}
      <div className="flex gap-3">
        <button type="submit" disabled={pending}
          className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50">
          {pending ? 'Saving…' : 'Add item'}
        </button>
        <button type="button" onClick={onBack} className="min-h-11 px-4 text-sm font-ui text-text-muted">Cancel</button>
      </div>
    </form>
  )
}
