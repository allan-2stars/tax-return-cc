'use client'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { createManualEvent } from '@/lib/api/events'
import { daysBetween, cgtDiscountEligible } from '@/lib/utils/investment'
import { validateDate } from '@/lib/utils/fy'
import useWorkspaceStore from '@/lib/stores/workspace.store'
import { useSessionDraft } from '@/lib/hooks/useSessionDraft'
import DraftStatus from '../DraftStatus'

type CryptoSubType = 'buy' | 'sell' | 'staking'

interface InvestmentFormProps { onSuccess: () => void; onBack: () => void; onCancel: () => void }

interface CryptoBuyFields {
  exchange: string; coin: string; amount_units: string
  purchase_price: string; transaction_fee: string
  purchase_date: string; note: string
}

interface CryptoSellFields {
  exchange: string; coin: string; amount_units: string
  sale_price: string; transaction_fee: string
  sale_date: string; purchase_date: string; purchase_price: string
  cost_basis_method: string; note: string
}

interface CryptoStakingFields {
  platform: string; coin: string
  income_amount: string; income_date: string; note: string
}

function hasDraftContent(draft: Partial<CryptoBuyFields | CryptoSellFields | CryptoStakingFields>): boolean {
  return Object.values(draft).some((value) => Boolean(String(value ?? '').trim()))
}

function AutoCalcBox({ label, value, unit = '' }: { label: string; value: string; unit?: string }) {
  return (
    <div className="rounded-md bg-surface-raised px-4 py-2 space-y-0.5">
      <p className="text-xs font-ui text-text-muted uppercase tracking-wide">{label}</p>
      <p className="font-mono text-text-muted">{unit}{value}</p>
      <p className="text-xs font-ui text-text-muted italic">Estimate only — confirm with your tax agent</p>
    </div>
  )
}

function CryptoBuySubForm({ onSuccess, onBack, onCancel }: InvestmentFormProps) {
  const { register, handleSubmit, watch, reset, formState: { errors } } = useForm<CryptoBuyFields>()
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
    keyParts: [workspaceId, financialYear, 'investment', 'crypto', 'buy'],
    draft: watch(),
    hasContent: hasDraftContent,
    applyDraft: (draft) => reset(draft as CryptoBuyFields),
  })

  const purchaseDateValue = watch('purchase_date')
  const purchaseDateWarning = !errors.purchase_date && purchaseDateValue
    ? validateDate(purchaseDateValue, financialYear ?? null).warning : undefined

  async function onSubmit(data: CryptoBuyFields) {
    const price = parseFloat(data.purchase_price)
    const fee = parseFloat(data.transaction_fee || '0') || 0
    setPending(true); setError(null)
    try {
      await createManualEvent({
        event_type: 'investment', category: 'crypto_acquisition',
        description: `Crypto Buy: ${data.amount_units} ${data.coin.toUpperCase()}`,
        amount: price + fee, date: data.purchase_date,
        frequency: 'one_off', note: data.note?.trim() || null, periods: null,
        metadata: {
          investment_sub_type: 'crypto', transaction_type: 'buy',
          exchange: data.exchange, coin: data.coin.toUpperCase(),
          amount_units: data.amount_units, purchase_price: price,
          transaction_fee: fee, purchase_date: data.purchase_date,
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
      <div>
        <label htmlFor="cb-exchange" className="text-sm font-ui text-text-body block mb-1">Exchange / Wallet</label>
        <input id="cb-exchange" type="text" placeholder="CoinSpot, Binance, Coinbase…"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('exchange', { required: 'Exchange is required.' })} />
        {errors.exchange && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.exchange.message}</p>}
      </div>
      <div>
        <label htmlFor="cb-coin" className="text-sm font-ui text-text-body block mb-1">Coin / Token</label>
        <input id="cb-coin" type="text" placeholder="BTC, ETH, SOL…"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui uppercase"
          {...register('coin', { required: 'Coin is required.' })} />
        {errors.coin && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.coin.message}</p>}
      </div>
      <div>
        <label htmlFor="cb-units" className="text-sm font-ui text-text-body block mb-1">Amount (units)</label>
        <input id="cb-units" type="number" min="0" step="any"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('amount_units', { required: 'Amount is required.' })} />
        {errors.amount_units && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.amount_units.message}</p>}
      </div>
      <div>
        <label htmlFor="cb-price" className="text-sm font-ui text-text-body block mb-1">Purchase price (AUD)</label>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="cb-price" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
            {...register('purchase_price', { required: 'Purchase price is required.' })} />
        </div>
        {errors.purchase_price && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.purchase_price.message}</p>}
      </div>
      <div>
        <label htmlFor="cb-fee" className="text-sm font-ui text-text-body block mb-1">Transaction fee (AUD, optional)</label>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="cb-fee" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
            {...register('transaction_fee')} />
        </div>
      </div>
      <div>
        <label htmlFor="cb-date" className="text-sm font-ui text-text-body block mb-1">Purchase date</label>
        <input id="cb-date" type="date"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('purchase_date', {
            required: 'Purchase date is required.',
            validate: { notFuture: (v) => { const e = validateDate(v, null).error; return e === undefined ? true : e } },
          })} />
        {errors.purchase_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.purchase_date.message}</p>}
        {purchaseDateWarning && <p className="text-sm font-ui text-review mt-1">⚠ {purchaseDateWarning}</p>}
      </div>
      <div>
        <label htmlFor="cb-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="cb-note" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p role="alert" className="text-sm font-ui text-risk-high">{error}</p>}
      <div className="flex gap-3">
        <button type="submit" disabled={pending}
          className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50">
          {pending ? 'Saving…' : 'Add item'}
        </button>
      </div>
      <button type="button" onClick={onCancel} className="text-sm font-ui text-text-muted">Cancel</button>
    </form>
  )
}

function CryptoSellSubForm({ onSuccess, onBack, onCancel }: InvestmentFormProps) {
  const { register, handleSubmit, watch, reset, formState: { errors } } = useForm<CryptoSellFields>()
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
    keyParts: [workspaceId, financialYear, 'investment', 'crypto', 'sell'],
    draft: watch(),
    hasContent: hasDraftContent,
    applyDraft: (draft) => reset(draft as CryptoSellFields),
  })

  const purchaseDate = watch('purchase_date')
  const saleDate = watch('sale_date')
  const saleDateWarning = !errors.sale_date && saleDate
    ? validateDate(saleDate, financialYear ?? null).warning : undefined
  const purchaseDateWarning = !errors.purchase_date && purchaseDate
    ? validateDate(purchaseDate, financialYear ?? null).warning : undefined
  const holdingDays = purchaseDate && saleDate ? daysBetween(purchaseDate, saleDate) : null
  const cgtEligible = holdingDays !== null ? cgtDiscountEligible(holdingDays) : null

  const salePrice = parseFloat(watch('sale_price') || '0')
  const fee = parseFloat(watch('transaction_fee') || '0') || 0
  const purchasePrice = parseFloat(watch('purchase_price') || '0')
  const estimatedGainLoss = salePrice > 0 && purchasePrice > 0
    ? (salePrice - fee) - purchasePrice
    : null

  async function onSubmit(data: CryptoSellFields) {
    const sp = parseFloat(data.sale_price)
    const f = parseFloat(data.transaction_fee || '0') || 0
    const pp = parseFloat(data.purchase_price)
    const gainLoss = (sp - f) - pp
    setPending(true); setError(null)
    try {
      await createManualEvent({
        event_type: 'investment', category: gainLoss < 0 ? 'capital_loss' : 'capital_gain',
        description: `Crypto Sell: ${data.amount_units} ${data.coin.toUpperCase()}`,
        amount: sp - f, date: data.sale_date,
        frequency: 'one_off', note: data.note?.trim() || null, periods: null,
        metadata: {
          investment_sub_type: 'crypto', transaction_type: 'sell',
          exchange: data.exchange, coin: data.coin.toUpperCase(),
          amount_units: data.amount_units, sale_price: sp,
          purchase_price: pp,
          transaction_fee: f, sale_date: data.sale_date, purchase_date: data.purchase_date,
          cost_basis_method: data.cost_basis_method,
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
      <div>
        <label htmlFor="cs-exchange" className="text-sm font-ui text-text-body block mb-1">Exchange / Wallet</label>
        <input id="cs-exchange" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('exchange', { required: 'Exchange is required.' })} />
        {errors.exchange && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.exchange.message}</p>}
      </div>
      <div>
        <label htmlFor="cs-coin" className="text-sm font-ui text-text-body block mb-1">Coin / Token</label>
        <input id="cs-coin" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui uppercase"
          {...register('coin', { required: 'Coin is required.' })} />
        {errors.coin && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.coin.message}</p>}
      </div>
      <div>
        <label htmlFor="cs-units" className="text-sm font-ui text-text-body block mb-1">Amount sold (units)</label>
        <input id="cs-units" type="number" min="0" step="any"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('amount_units', { required: 'Amount is required.' })} />
        {errors.amount_units && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.amount_units.message}</p>}
      </div>
      <div>
        <label htmlFor="cs-sale-price" className="text-sm font-ui text-text-body block mb-1">Sale price (AUD)</label>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="cs-sale-price" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
            {...register('sale_price', { required: 'Sale price is required.' })} />
        </div>
        {errors.sale_price && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.sale_price.message}</p>}
      </div>
      <div>
        <label htmlFor="cs-purchase-price" className="text-sm font-ui text-text-body block mb-1">Purchase price (AUD)</label>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="cs-purchase-price" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
            {...register('purchase_price', { required: 'Purchase price is required.' })} />
        </div>
        {errors.purchase_price && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.purchase_price.message}</p>}
      </div>
      <div>
        <label htmlFor="cs-fee" className="text-sm font-ui text-text-body block mb-1">Transaction fee (AUD, optional)</label>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="cs-fee" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
            {...register('transaction_fee')} />
        </div>
      </div>
      <div>
        <label htmlFor="cs-sale-date" className="text-sm font-ui text-text-body block mb-1">Sale date</label>
        <input id="cs-sale-date" type="date"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('sale_date', {
            required: 'Sale date is required.',
            validate: { notFuture: (v) => { const e = validateDate(v, null).error; return e === undefined ? true : e } },
          })} />
        {errors.sale_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.sale_date.message}</p>}
        {saleDateWarning && <p className="text-sm font-ui text-review mt-1">⚠ {saleDateWarning}</p>}
      </div>
      <div>
        <label htmlFor="cs-purchase-date" className="text-sm font-ui text-text-body block mb-1">Purchase date</label>
        <input id="cs-purchase-date" type="date"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('purchase_date', {
            required: 'Purchase date is required.',
            validate: { notFuture: (v) => { const e = validateDate(v, null).error; return e === undefined ? true : e } },
          })} />
        {errors.purchase_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.purchase_date.message}</p>}
        {purchaseDateWarning && <p className="text-sm font-ui text-review mt-1">⚠ {purchaseDateWarning}</p>}
      </div>
      {holdingDays !== null && (
        <div className="space-y-2">
          <div className="rounded-md bg-surface-raised px-4 py-2">
            <p className="text-xs font-ui text-text-muted uppercase tracking-wide">Holding period</p>
            <p className="font-mono text-text-muted">{holdingDays} days</p>
          </div>
          <p className={`text-sm font-ui ${cgtEligible ? 'text-ready' : 'text-text-muted'}`}>
            {cgtEligible ? '50% CGT discount may apply' : 'No CGT discount (held less than 12 months)'}
          </p>
        </div>
      )}
      {estimatedGainLoss !== null && (
        <AutoCalcBox
          label={estimatedGainLoss >= 0 ? 'Estimated capital gain' : 'Estimated capital loss'}
          value={Math.abs(estimatedGainLoss).toFixed(2)} unit="$" />
      )}
      <div>
        <label htmlFor="cs-basis" className="text-sm font-ui text-text-body block mb-1">Cost basis method</label>
        <select id="cs-basis" className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('cost_basis_method')}>
          <option value="FIFO">FIFO (recommended)</option>
          <option value="Other">Other</option>
        </select>
        <p className="text-xs font-ui text-text-muted italic mt-1">ATO generally accepts FIFO (first in, first out)</p>
      </div>
      <div>
        <label htmlFor="cs-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="cs-note" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p role="alert" className="text-sm font-ui text-risk-high">{error}</p>}
      <div className="flex gap-3">
        <button type="submit" disabled={pending}
          className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50">
          {pending ? 'Saving…' : 'Add item'}
        </button>
      </div>
      <button type="button" onClick={onCancel} className="text-sm font-ui text-text-muted">Cancel</button>
    </form>
  )
}

function CryptoStakingSubForm({ onSuccess, onBack, onCancel }: InvestmentFormProps) {
  const { register, handleSubmit, watch, reset, formState: { errors } } = useForm<CryptoStakingFields>()
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
    keyParts: [workspaceId, financialYear, 'investment', 'crypto', 'staking'],
    draft: watch(),
    hasContent: hasDraftContent,
    applyDraft: (draft) => reset(draft as CryptoStakingFields),
  })

  const incomeDateValue = watch('income_date')
  const incomeDateWarning = !errors.income_date && incomeDateValue
    ? validateDate(incomeDateValue, financialYear ?? null).warning : undefined

  async function onSubmit(data: CryptoStakingFields) {
    const amt = parseFloat(data.income_amount)
    setPending(true); setError(null)
    try {
      await createManualEvent({
        event_type: 'investment', category: 'crypto',
        description: `Staking Income: ${data.coin.toUpperCase()} on ${data.platform}`,
        amount: amt, date: data.income_date,
        frequency: 'one_off', note: data.note?.trim() || null, periods: null,
        review_status: 'needs_agent_review',
        metadata: {
          investment_sub_type: 'crypto', transaction_type: 'staking',
          platform: data.platform, coin: data.coin.toUpperCase(),
          income_amount: amt, income_date: data.income_date,
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
        Complex crypto income — your tax agent should review this
      </div>
      <div>
        <label htmlFor="cst-platform" className="text-sm font-ui text-text-body block mb-1">Platform</label>
        <input id="cst-platform" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('platform', { required: 'Platform is required.' })} />
        {errors.platform && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.platform.message}</p>}
      </div>
      <div>
        <label htmlFor="cst-coin" className="text-sm font-ui text-text-body block mb-1">Coin / Token</label>
        <input id="cst-coin" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui uppercase"
          {...register('coin', { required: 'Coin is required.' })} />
        {errors.coin && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.coin.message}</p>}
      </div>
      <div>
        <label htmlFor="cst-amount" className="text-sm font-ui text-text-body block mb-1">Income amount (AUD)</label>
        <p className="text-xs font-ui text-text-muted italic mb-1">
          Staking rewards are taxed as ordinary income at the AUD value when received
        </p>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="cst-amount" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
            {...register('income_amount', { required: 'Income amount is required.' })} />
        </div>
        {errors.income_amount && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.income_amount.message}</p>}
      </div>
      <div>
        <label htmlFor="cst-date" className="text-sm font-ui text-text-body block mb-1">Income date</label>
        <input id="cst-date" type="date"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('income_date', {
            required: 'Income date is required.',
            validate: { notFuture: (v) => { const e = validateDate(v, null).error; return e === undefined ? true : e } },
          })} />
        {errors.income_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.income_date.message}</p>}
        {incomeDateWarning && <p className="text-sm font-ui text-review mt-1">⚠ {incomeDateWarning}</p>}
      </div>
      <div>
        <label htmlFor="cst-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="cst-note" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p role="alert" className="text-sm font-ui text-risk-high">{error}</p>}
      <div className="flex gap-3">
        <button type="submit" disabled={pending}
          className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50">
          {pending ? 'Saving…' : 'Add item'}
        </button>
      </div>
      <button type="button" onClick={onCancel} className="text-sm font-ui text-text-muted">Cancel</button>
    </form>
  )
}

export default function CryptoForm({ onSuccess, onBack, onCancel }: InvestmentFormProps) {
  const [subType, setSubType] = useState<CryptoSubType | null>(null)

  if (!subType) {
    return (
      <div className="space-y-4">
        <button type="button" onClick={onBack} className="text-sm font-ui text-text-muted">← Back</button>
        <h2 className="font-display text-xl font-semibold text-text-primary">Cryptocurrency transaction type</h2>
        <div className="flex gap-2 flex-wrap">
          {(['buy', 'sell'] as CryptoSubType[]).map((t) => (
            <button key={t} type="button" onClick={() => setSubType(t)}
              className="px-5 py-3 rounded-md border border-border bg-surface font-ui text-text-body hover:border-accent transition-colors capitalize">
              {t}
            </button>
          ))}
          <button type="button" onClick={() => setSubType('staking')}
            className="px-5 py-3 rounded-md border border-border bg-surface font-ui text-text-body hover:border-accent transition-colors">
            Staking / DeFi income
          </button>
        </div>
        <button type="button" onClick={onCancel} className="text-sm font-ui text-text-muted">Cancel</button>
      </div>
    )
  }

  const backToSubType = () => setSubType(null)
  if (subType === 'buy') return <CryptoBuySubForm onSuccess={onSuccess} onBack={backToSubType} onCancel={onCancel} />
  if (subType === 'sell') return <CryptoSellSubForm onSuccess={onSuccess} onBack={backToSubType} onCancel={onCancel} />
  return <CryptoStakingSubForm onSuccess={onSuccess} onBack={backToSubType} onCancel={onCancel} />
}
