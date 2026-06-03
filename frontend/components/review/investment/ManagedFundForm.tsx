'use client'
import { useForm } from 'react-hook-form'
import { useState } from 'react'
import { createManualEvent } from '@/lib/api/events'
import { Info } from 'lucide-react'
import { validateDate } from '@/lib/utils/fy'
import useWorkspaceStore from '@/lib/stores/workspace.store'
import { useSessionDraft } from '@/lib/hooks/useSessionDraft'
import DraftStatus from '../DraftStatus'

interface InvestmentFormProps { onSuccess: () => void; onBack: () => void; onCancel: () => void }

interface ManagedFundFields {
  fund_name: string; fund_manager: string
  distribution_amount: string; capital_gains_component: string
  foreign_income_component: string; tfn_withholding_tax: string
  distribution_date: string; note: string
}

function hasDraftContent(draft: Partial<ManagedFundFields>): boolean {
  return Object.values(draft).some((value) => Boolean(String(value ?? '').trim()))
}

export default function ManagedFundForm({ onSuccess, onBack, onCancel }: InvestmentFormProps) {
  const { register, handleSubmit, watch, reset, formState: { errors } } = useForm<ManagedFundFields>()
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
    keyParts: [workspaceId, financialYear, 'investment', 'managed_fund'],
    draft: watch(),
    hasContent: hasDraftContent,
    applyDraft: (draft) => reset(draft),
  })

  const capitalGains = parseFloat(watch('capital_gains_component') || '0') || 0
  const distributionDateValue = watch('distribution_date')
  const distributionDateWarning = !errors.distribution_date && distributionDateValue
    ? validateDate(distributionDateValue, financialYear ?? null).warning : undefined

  async function onSubmit(data: ManagedFundFields) {
    const dist = parseFloat(data.distribution_amount)
    const cg = parseFloat(data.capital_gains_component || '0') || 0
    setPending(true); setError(null)
    try {
      await createManualEvent({
        event_type: 'investment', category: 'managed_fund_distribution',
        description: `Managed Fund Distribution: ${data.fund_name}`,
        amount: dist, date: data.distribution_date,
        frequency: 'one_off', note: data.note?.trim() || null, periods: null,
        review_status: cg > 0 ? 'needs_agent_review' : undefined,
        metadata: {
          investment_sub_type: 'managed_fund',
          fund_name: data.fund_name, fund_manager: data.fund_manager || null,
          distribution_amount: dist, capital_gains_component: cg,
          foreign_income_component: parseFloat(data.foreign_income_component || '0') || 0,
          tfn_withholding: parseFloat(data.tfn_withholding_tax || '0') || 0,
          distribution_date: data.distribution_date,
        },
      })
      clearDraft(true)
      onSuccess()
    } catch { setError('Something went wrong. Please try again.') }
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
      <div className="rounded-md bg-surface-raised px-4 py-3 text-sm font-ui text-text-muted">
        Please provide your fund&#39;s annual tax statement to your tax agent
      </div>
      <div>
        <label htmlFor="mf-name" className="text-sm font-ui text-text-body block mb-1">Fund name</label>
        <input id="mf-name" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('fund_name', { required: 'Fund name is required.' })} />
        {errors.fund_name && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.fund_name.message}</p>}
      </div>
      <div>
        <label htmlFor="mf-manager" className="text-sm font-ui text-text-body block mb-1">Fund manager (optional)</label>
        <input id="mf-manager" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('fund_manager')} />
      </div>
      <div>
        <label htmlFor="mf-dist" className="text-sm font-ui text-text-body block mb-1">Distribution amount (AUD)</label>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="mf-dist" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
            {...register('distribution_amount', { required: 'Distribution amount is required.' })} />
        </div>
        {errors.distribution_amount && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.distribution_amount.message}</p>}
      </div>
      <div>
        <div className="flex items-center gap-2 mb-1">
          <label htmlFor="mf-cg" className="text-sm font-ui text-text-body">Capital gains component (AUD, optional)</label>
          <Info size={14} className="text-text-muted" aria-hidden />
        </div>
        <p className="text-xs font-ui text-text-muted italic mb-1">From your annual tax statement from the fund manager</p>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="mf-cg" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
            {...register('capital_gains_component')} />
        </div>
        {capitalGains > 0 && (
          <p className="text-xs font-ui text-text-muted mt-1">This item will be flagged for your tax agent to review</p>
        )}
      </div>
      <div>
        <label htmlFor="mf-foreign" className="text-sm font-ui text-text-body block mb-1">Foreign income component (AUD, optional)</label>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="mf-foreign" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
            {...register('foreign_income_component')} />
        </div>
      </div>
      <div>
        <label htmlFor="mf-tfn" className="text-sm font-ui text-text-body block mb-1">TFN withholding tax (AUD, optional)</label>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="mf-tfn" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
            {...register('tfn_withholding_tax')} />
        </div>
      </div>
      <div>
        <label htmlFor="mf-date" className="text-sm font-ui text-text-body block mb-1">Distribution date</label>
        <input id="mf-date" type="date"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('distribution_date', {
            required: 'Distribution date is required.',
            validate: { notFuture: (v) => { const e = validateDate(v, null).error; return e === undefined ? true : e } },
          })} />
        {errors.distribution_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.distribution_date.message}</p>}
        {distributionDateWarning && <p className="text-sm font-ui text-review mt-1">⚠ {distributionDateWarning}</p>}
      </div>
      <div>
        <label htmlFor="mf-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="mf-note" type="text"
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
