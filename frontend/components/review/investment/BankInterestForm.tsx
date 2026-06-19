'use client'
import { useForm } from 'react-hook-form'
import { useState } from 'react'
import { createManualEvent } from '@/lib/api/events'
import { normalizeApiError } from '@/lib/api/errors'
import { validateDate } from '@/lib/utils/fy'
import useWorkspaceStore from '@/lib/stores/workspace.store'
import { useSessionDraft } from '@/lib/hooks/useSessionDraft'
import DraftStatus from '../DraftStatus'

interface InvestmentFormProps { onSuccess: () => void; onBack: () => void; onCancel: () => void }

interface BankInterestFields {
  bank_name: string; account_type: string
  interest_amount: string
  statement_period_start: string
  statement_period_end: string
  in_payg: boolean
  note: string
}

function hasDraftContent(draft: Partial<BankInterestFields>): boolean {
  return Object.values(draft).some((value) =>
    typeof value === 'boolean' ? value : Boolean(String(value ?? '').trim())
  )
}

export default function BankInterestForm({ onSuccess, onBack, onCancel }: InvestmentFormProps) {
  const { register, handleSubmit, watch, reset, formState: { errors } } = useForm<BankInterestFields>()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { workspaceId, financialYear } = useWorkspaceStore()
  const {
    notice: draftNotice,
    restoredDraft,
    restoreDraft,
    discardDraft,
    clearDraft,
  } = useSessionDraft({
    keyParts: [workspaceId, financialYear, 'investment', 'bank_interest'],
    draft: watch(),
    hasContent: hasDraftContent,
    applyDraft: (draft) => reset(draft),
  })

  const statementPeriodStart = watch('statement_period_start')
  const statementPeriodEnd = watch('statement_period_end')
  const statementPeriodStartWarning = !errors.statement_period_start && statementPeriodStart
    ? validateDate(statementPeriodStart, financialYear ?? null).warning : undefined
  const statementPeriodEndWarning = !errors.statement_period_end && statementPeriodEnd
    ? validateDate(statementPeriodEnd, financialYear ?? null).warning : undefined

  async function onSubmit(data: BankInterestFields) {
    const amt = parseFloat(data.interest_amount)
    setPending(true); setError(null)
    try {
      await createManualEvent({
        event_type: 'investment', category: 'bank_interest',
        description: `Bank Interest: ${data.bank_name} (${data.account_type})`,
        amount: amt, date: data.statement_period_end,
        frequency: 'annual', note: data.note?.trim() || null, periods: null,
        possible_duplicate: data.in_payg,
        metadata: {
          investment_sub_type: 'bank_interest',
          bank_name: data.bank_name, account_type: data.account_type,
          interest_amount: amt,
          statement_period_start: data.statement_period_start,
          statement_period_end: data.statement_period_end,
          financial_year: financialYear ?? null,
          in_payg: data.in_payg,
        },
      })
      clearDraft(true)
      onSuccess()
    } catch (err: unknown) { setError(normalizeApiError(err).message) }
    finally { setPending(false) }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <button type="button" onClick={onBack} className="text-sm font-ui text-text-muted">← Back</button>
      <DraftStatus
        notice={draftNotice}
        hasRestorableDraft={Boolean(restoredDraft)}
        onRestore={restoreDraft}
        onDiscard={discardDraft}
      />
      <div>
        <label htmlFor="bi-bank" className="text-sm font-ui text-text-body block mb-1">Bank name</label>
        <input id="bi-bank" type="text" placeholder="Commonwealth Bank, ANZ…"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('bank_name', { required: 'Bank name is required.' })} />
        {errors.bank_name && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.bank_name.message}</p>}
      </div>
      <div>
        <label htmlFor="bi-type" className="text-sm font-ui text-text-body block mb-1">Account type</label>
        <select id="bi-type" className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('account_type', { required: 'Account type is required.' })}>
          <option value="">Select type</option>
          <option value="Savings">Savings</option>
          <option value="Term Deposit">Term Deposit</option>
          <option value="Offset">Offset</option>
          <option value="Other">Other</option>
        </select>
        {errors.account_type && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.account_type.message}</p>}
      </div>
      <div>
        <label htmlFor="bi-amount" className="text-sm font-ui text-text-body block mb-1">Interest amount (AUD)</label>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="bi-amount" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
            {...register('interest_amount', { required: 'Interest amount is required.' })} />
        </div>
        {errors.interest_amount && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.interest_amount.message}</p>}
      </div>
      <label className="flex items-start gap-2 cursor-pointer">
        <input type="checkbox" className="mt-0.5" {...register('in_payg')} />
        <span className="text-sm font-ui text-text-body">This interest is already in my PAYG summary</span>
      </label>
      <div>
        <label htmlFor="bi-period-start" className="text-sm font-ui text-text-body block mb-1">Statement period start</label>
        <input id="bi-period-start" type="date"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('statement_period_start', {
            required: 'Statement period start is required.',
            validate: {
              validDate: (v) => {
                const validation = validateDate(v, financialYear ?? null)
                return validation.error === undefined ? true : validation.error
              },
            },
          })} />
        {errors.statement_period_start && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.statement_period_start.message}</p>}
        {!errors.statement_period_start && statementPeriodStartWarning && (
          <p className="text-sm font-ui text-review mt-1">⚠ {statementPeriodStartWarning}</p>
        )}
      </div>
      <div>
        <label htmlFor="bi-period-end" className="text-sm font-ui text-text-body block mb-1">Statement period end</label>
        <input id="bi-period-end" type="date"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('statement_period_end', {
            required: 'Statement period end is required.',
            validate: {
              validDate: (v) => {
                const validation = validateDate(v, financialYear ?? null)
                return validation.error === undefined ? true : validation.error
              },
              periodOrder: (v) => {
                if (!statementPeriodStart || !v) return true
                return v >= statementPeriodStart ? true : 'Statement period end must be on or after statement period start.'
              },
            },
          })} />
        {errors.statement_period_end && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.statement_period_end.message}</p>}
        {!errors.statement_period_end && statementPeriodEndWarning && (
          <p className="text-sm font-ui text-review mt-1">⚠ {statementPeriodEndWarning}</p>
        )}
      </div>
      <div>
        <label htmlFor="bi-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="bi-note" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p role="alert" className="text-sm font-ui text-risk-high">{error}</p>}
      <div className="flex gap-3">
        <button type="submit" disabled={pending}
          className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50">
          {pending ? 'Saving…' : 'Add item'}
        </button>
        <button type="button" onClick={onCancel} className="min-h-11 px-4 text-sm font-ui text-text-muted">Cancel</button>
      </div>
    </form>
  )
}
