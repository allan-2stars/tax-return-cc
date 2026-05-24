'use client'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Info } from 'lucide-react'
import { createManualEvent } from '@/lib/api/events'
import { daysBetween, cgtDiscountEligible } from '@/lib/utils/investment'

type SharesSubType = 'buy' | 'sell' | 'dividend'

interface InvestmentFormProps {
  onSuccess: () => void
  onBack: () => void
}

interface BuyFields {
  platform: string; stock_code: string; exchange: string
  units: string; price_per_unit: string; brokerage_fee: string
  purchase_date: string; note: string
}

interface SellFields {
  platform: string; stock_code: string; exchange: string
  units: string; sale_price_per_unit: string; brokerage_fee: string
  sale_date: string; purchase_date: string; purchase_price_per_unit: string; note: string
}

interface DividendFields {
  company_name: string; stock_code: string
  dividend_amount: string; franking_credits: string
  payment_date: string; in_payg: boolean; note: string
}

function CurrencyInput({ id, label, register, error, optional = false }: {
  id: string; label: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any; error?: string; optional?: boolean
}) {
  return (
    <div>
      <label htmlFor={id} className="text-sm font-ui text-text-body block mb-1">
        {label}{optional && ' (optional)'}
      </label>
      <div className="relative flex items-center">
        <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
        <input
          id={id}
          type="number"
          min="0"
          step="0.01"
          placeholder="0.00"
          className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm text-text-primary focus:outline-none focus:border-accent"
          {...register}
        />
      </div>
      {error && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{error}</p>}
    </div>
  )
}

function AutoCalcBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-surface-raised px-4 py-2 space-y-0.5">
      <p className="text-xs font-ui text-text-muted uppercase tracking-wide">{label}</p>
      <p className="font-mono text-text-muted">${value}</p>
      <p className="text-xs font-ui text-text-muted italic">Estimate only — confirm with your tax agent</p>
    </div>
  )
}

function SharesBuySubForm({ onSuccess, onBack }: InvestmentFormProps) {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<BuyFields>()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const units = parseFloat(watch('units') || '0')
  const price = parseFloat(watch('price_per_unit') || '0')
  const brokerage = parseFloat(watch('brokerage_fee') || '0') || 0
  const totalCost = units > 0 && price > 0 ? units * price + brokerage : null

  async function onSubmit(data: BuyFields) {
    const u = parseFloat(data.units)
    const p = parseFloat(data.price_per_unit)
    const b = parseFloat(data.brokerage_fee || '0') || 0
    setPending(true); setError(null)
    try {
      await createManualEvent({
        event_type: 'investment', category: 'capital_gain',
        description: `Shares Buy: ${u} × ${data.stock_code.toUpperCase()} @ $${p.toFixed(2)}`,
        amount: u * p + b, date: data.purchase_date,
        frequency: 'one_off', note: data.note?.trim() || null, periods: null,
        metadata: {
          investment_sub_type: 'shares', transaction_type: 'buy',
          platform: data.platform, stock_code: data.stock_code.toUpperCase(),
          exchange: data.exchange, units: u, price_per_unit: p, brokerage_fee: b,
          purchase_date: data.purchase_date,
        },
      })
      onSuccess()
    } catch { setError('Something went wrong. Please try again.') }
    finally { setPending(false) }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div>
        <label htmlFor="sb-platform" className="text-sm font-ui text-text-body block mb-1">Platform / Broker</label>
        <input id="sb-platform" type="text" placeholder="CommSec, Nabtrade, moomoo…"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('platform', { required: 'Platform is required.' })} />
        {errors.platform && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.platform.message}</p>}
      </div>
      <div>
        <label htmlFor="sb-code" className="text-sm font-ui text-text-body block mb-1">Stock code</label>
        <input id="sb-code" type="text" placeholder="e.g. CBA, VAS, MSFT"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui uppercase"
          {...register('stock_code', { required: 'Stock code is required.' })} />
        {errors.stock_code && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.stock_code.message}</p>}
      </div>
      <div>
        <label htmlFor="sb-exchange" className="text-sm font-ui text-text-body block mb-1">Exchange</label>
        <select id="sb-exchange" className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('exchange', { required: 'Exchange is required.' })}>
          <option value="">Select exchange</option>
          <option value="ASX">ASX</option>
          <option value="NYSE">NYSE</option>
          <option value="NASDAQ">NASDAQ</option>
          <option value="Other">Other</option>
        </select>
        {errors.exchange && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.exchange.message}</p>}
      </div>
      <div>
        <label htmlFor="sb-units" className="text-sm font-ui text-text-body block mb-1">Number of units</label>
        <input id="sb-units" type="number" min="0" step="1"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('units', { required: 'Units is required.' })} />
        {errors.units && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.units.message}</p>}
      </div>
      <CurrencyInput id="sb-price" label="Price per unit (AUD)"
        register={register('price_per_unit', { required: 'Price per unit is required.' })}
        error={errors.price_per_unit?.message} />
      <CurrencyInput id="sb-brokerage" label="Brokerage fee (AUD)"
        register={register('brokerage_fee')} optional />
      <div>
        <label htmlFor="sb-date" className="text-sm font-ui text-text-body block mb-1">Purchase date</label>
        <input id="sb-date" type="date"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('purchase_date', { required: 'Purchase date is required.' })} />
        {errors.purchase_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.purchase_date.message}</p>}
      </div>
      {totalCost !== null && <AutoCalcBox label="Total cost" value={totalCost.toFixed(2)} />}
      <div>
        <label htmlFor="sb-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="sb-note" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
      <div className="flex gap-3">
        <button type="submit" disabled={pending}
          className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50">
          {pending ? 'Saving…' : 'Add item'}
        </button>
        <button type="button" onClick={onBack}
          className="min-h-11 px-4 text-sm font-ui text-text-muted">Cancel</button>
      </div>
    </form>
  )
}

function SharesSellSubForm({ onSuccess, onBack }: InvestmentFormProps) {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<SellFields>()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const purchaseDate = watch('purchase_date')
  const saleDate = watch('sale_date')
  const holdingDays = purchaseDate && saleDate ? daysBetween(purchaseDate, saleDate) : null
  const cgtEligible = holdingDays !== null ? cgtDiscountEligible(holdingDays) : null

  const units = parseFloat(watch('units') || '0')
  const salePrice = parseFloat(watch('sale_price_per_unit') || '0')
  const brokerage = parseFloat(watch('brokerage_fee') || '0') || 0
  const purchasePrice = parseFloat(watch('purchase_price_per_unit') || '0')
  const estimatedGainLoss = units > 0 && salePrice > 0 && purchasePrice > 0
    ? units * salePrice - brokerage - units * purchasePrice
    : null

  async function onSubmit(data: SellFields) {
    const u = parseFloat(data.units)
    const sp = parseFloat(data.sale_price_per_unit)
    const b = parseFloat(data.brokerage_fee || '0') || 0
    const isForeignExchange = data.exchange !== 'ASX'
    setPending(true); setError(null)
    try {
      await createManualEvent({
        event_type: 'investment',
        category: estimatedGainLoss !== null && estimatedGainLoss < 0 ? 'capital_loss' : 'capital_gain',
        description: `Shares Sell: ${u} × ${data.stock_code.toUpperCase()} @ $${sp.toFixed(2)}`,
        amount: u * sp - b, date: data.sale_date,
        frequency: 'one_off', note: data.note?.trim() || null, periods: null,
        review_status: isForeignExchange ? 'needs_agent_review' : undefined,
        metadata: {
          investment_sub_type: 'shares', transaction_type: 'sell',
          platform: data.platform, stock_code: data.stock_code.toUpperCase(),
          exchange: data.exchange, units: u, sale_price_per_unit: sp,
          purchase_price_per_unit: parseFloat(data.purchase_price_per_unit),
          brokerage_fee: b, sale_date: data.sale_date, purchase_date: data.purchase_date,
        },
      })
      onSuccess()
    } catch { setError('Something went wrong. Please try again.') }
    finally { setPending(false) }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div>
        <label htmlFor="ss-platform" className="text-sm font-ui text-text-body block mb-1">Platform / Broker</label>
        <input id="ss-platform" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('platform', { required: 'Platform is required.' })} />
        {errors.platform && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.platform.message}</p>}
      </div>
      <div>
        <label htmlFor="ss-code" className="text-sm font-ui text-text-body block mb-1">Stock code</label>
        <input id="ss-code" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui uppercase"
          {...register('stock_code', { required: 'Stock code is required.' })} />
        {errors.stock_code && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.stock_code.message}</p>}
      </div>
      <div>
        <label htmlFor="ss-exchange" className="text-sm font-ui text-text-body block mb-1">Exchange</label>
        <select id="ss-exchange" className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('exchange', { required: 'Exchange is required.' })}>
          <option value="">Select exchange</option>
          <option value="ASX">ASX</option>
          <option value="NYSE">NYSE</option>
          <option value="NASDAQ">NASDAQ</option>
          <option value="Other">Other</option>
        </select>
        {errors.exchange && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.exchange.message}</p>}
      </div>
      <div>
        <label htmlFor="ss-units" className="text-sm font-ui text-text-body block mb-1">Number of units</label>
        <input id="ss-units" type="number" min="0" step="1"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('units', { required: 'Units is required.' })} />
        {errors.units && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.units.message}</p>}
      </div>
      <CurrencyInput id="ss-sale-price" label="Sale price per unit (AUD)"
        register={register('sale_price_per_unit', { required: 'Sale price is required.' })}
        error={errors.sale_price_per_unit?.message} />
      <CurrencyInput id="ss-purchase-price" label="Purchase price per unit (AUD)"
        register={register('purchase_price_per_unit', { required: 'Purchase price is required.' })}
        error={errors.purchase_price_per_unit?.message} />
      <CurrencyInput id="ss-brokerage" label="Brokerage fee (AUD)"
        register={register('brokerage_fee')} optional />
      <div>
        <label htmlFor="ss-sale-date" className="text-sm font-ui text-text-body block mb-1">Sale date</label>
        <input id="ss-sale-date" type="date"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('sale_date', { required: 'Sale date is required.' })} />
        {errors.sale_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.sale_date.message}</p>}
      </div>
      <div>
        <label htmlFor="ss-purchase-date" className="text-sm font-ui text-text-body block mb-1">Purchase date</label>
        <input id="ss-purchase-date" type="date"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('purchase_date', { required: 'Purchase date is required.' })} />
        {errors.purchase_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.purchase_date.message}</p>}
      </div>
      {holdingDays !== null && (
        <div className="space-y-2">
          <div className="rounded-md bg-surface-raised px-4 py-2">
            <p className="text-xs font-ui text-text-muted uppercase tracking-wide">Holding period</p>
            <p className="font-mono text-text-muted">{holdingDays} days</p>
          </div>
          <p className={`text-sm font-ui ${cgtEligible ? 'text-ready' : 'text-text-muted'}`}>
            {cgtEligible
              ? '50% CGT discount may apply'
              : 'No CGT discount (held less than 12 months)'}
          </p>
          {cgtEligible && (
            <p className="text-xs font-ui text-text-muted italic">
              Assets held for more than 12 months may qualify for a 50% CGT discount
            </p>
          )}
        </div>
      )}
      {estimatedGainLoss !== null && (
        <AutoCalcBox
          label={estimatedGainLoss >= 0 ? 'Estimated capital gain' : 'Estimated capital loss'}
          value={Math.abs(estimatedGainLoss).toFixed(2)} />
      )}
      <div>
        <label htmlFor="ss-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="ss-note" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
      <div className="flex gap-3">
        <button type="submit" disabled={pending}
          className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50">
          {pending ? 'Saving…' : 'Add item'}
        </button>
        <button type="button" onClick={onBack}
          className="min-h-11 px-4 text-sm font-ui text-text-muted">Cancel</button>
      </div>
    </form>
  )
}

function SharesDividendSubForm({ onSuccess, onBack }: InvestmentFormProps) {
  const { register, handleSubmit, formState: { errors } } = useForm<DividendFields>()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(data: DividendFields) {
    const amt = parseFloat(data.dividend_amount)
    const fc = parseFloat(data.franking_credits || '0') || 0
    setPending(true); setError(null)
    try {
      await createManualEvent({
        event_type: 'investment', category: 'dividend',
        description: `Dividend: ${data.company_name}${data.stock_code ? ` (${data.stock_code.toUpperCase()})` : ''}`,
        amount: amt, date: data.payment_date,
        frequency: 'one_off', note: data.note?.trim() || null, periods: null,
        possible_duplicate: data.in_payg,
        metadata: {
          investment_sub_type: 'shares', transaction_type: 'dividend',
          company_name: data.company_name,
          stock_code: data.stock_code ? data.stock_code.toUpperCase() : null,
          dividend_amount: amt, franking_credits: fc,
          payment_date: data.payment_date, in_payg: data.in_payg,
        },
      })
      onSuccess()
    } catch { setError('Something went wrong. Please try again.') }
    finally { setPending(false) }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div>
        <label htmlFor="sd-company" className="text-sm font-ui text-text-body block mb-1">Company name</label>
        <input id="sd-company" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('company_name', { required: 'Company name is required.' })} />
        {errors.company_name && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.company_name.message}</p>}
      </div>
      <div>
        <label htmlFor="sd-code" className="text-sm font-ui text-text-body block mb-1">Stock code (optional)</label>
        <input id="sd-code" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui uppercase"
          {...register('stock_code')} />
      </div>
      <CurrencyInput id="sd-amount" label="Dividend amount (AUD)"
        register={register('dividend_amount', { required: 'Dividend amount is required.' })}
        error={errors.dividend_amount?.message} />
      <div>
        <div className="flex items-center gap-2 mb-1">
          <label htmlFor="sd-franking" className="text-sm font-ui text-text-body">Franking credits (AUD, optional)</label>
          <Info size={14} className="text-text-muted" aria-hidden />
        </div>
        <p className="text-xs font-ui text-text-muted italic mb-1">Franking credits offset tax already paid by the company</p>
        <div className="relative flex items-center">
          <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
          <input id="sd-franking" type="number" min="0" step="0.01" placeholder="0.00"
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm text-text-primary focus:outline-none focus:border-accent"
            {...register('franking_credits')} />
        </div>
      </div>
      <div>
        <label htmlFor="sd-date" className="text-sm font-ui text-text-body block mb-1">Payment date</label>
        <input id="sd-date" type="date"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('payment_date', { required: 'Payment date is required.' })} />
        {errors.payment_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.payment_date.message}</p>}
      </div>
      <label className="flex items-start gap-2 cursor-pointer">
        <input type="checkbox" className="mt-0.5" {...register('in_payg')} />
        <span className="text-sm font-ui text-text-body">This dividend is already included in my PAYG summary</span>
      </label>
      <div>
        <label htmlFor="sd-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="sd-note" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
      <div className="flex gap-3">
        <button type="submit" disabled={pending}
          className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50">
          {pending ? 'Saving…' : 'Add item'}
        </button>
        <button type="button" onClick={onBack}
          className="min-h-11 px-4 text-sm font-ui text-text-muted">Cancel</button>
      </div>
    </form>
  )
}

export default function SharesForm({ onSuccess, onBack }: InvestmentFormProps) {
  const [subType, setSubType] = useState<SharesSubType | null>(null)

  if (!subType) {
    return (
      <div className="space-y-4">
        <button type="button" onClick={onBack} className="text-sm font-ui text-text-muted">← Back</button>
        <h2 className="font-display text-xl font-semibold text-text-primary">Shares / ETF transaction type</h2>
        <div className="flex gap-2 flex-wrap">
          {(['buy', 'sell', 'dividend'] as SharesSubType[]).map((t) => (
            <button key={t} type="button" onClick={() => setSubType(t)}
              className="px-5 py-3 rounded-md border border-border bg-surface font-ui text-text-body hover:border-accent transition-colors capitalize">
              {t}
            </button>
          ))}
        </div>
      </div>
    )
  }

  const backToSubType = () => setSubType(null)
  if (subType === 'buy') return <SharesBuySubForm onSuccess={onSuccess} onBack={backToSubType} />
  if (subType === 'sell') return <SharesSellSubForm onSuccess={onSuccess} onBack={backToSubType} />
  return <SharesDividendSubForm onSuccess={onSuccess} onBack={backToSubType} />
}
