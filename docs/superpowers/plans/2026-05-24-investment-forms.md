# Investment Forms Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the generic investment form in `ManualEntryForm` with 6 dedicated investment sub-type forms (Shares/ETF, Crypto, Bank Interest, Managed Fund, Foreign Income, Other), each with appropriate fields, auto-calculations, and RHF validation.

**Architecture:** Add a `metadata` JSON column to `TaxEvent` to store investment-specific fields. When the user selects "Investment" in Step 1, a new step shows a sub-type selector that routes to a dedicated form. Each form calls `createManualEvent` with a `metadata` payload; flagged types (staking, foreign income, managed fund with gains) pass `review_status: "needs_agent_review"`. Possible-duplicate flag for PAYG checkboxes flows through via a new `possible_duplicate` field.

**Tech Stack:** React Hook Form (^7.76.0, already installed), native `Date` for CGT day calculations, FastAPI + SQLAlchemy + Alembic on the backend.

---

## File Structure

**Create:**
- `frontend/lib/utils/investment.ts`
- `frontend/components/review/investment/SharesForm.tsx`
- `frontend/components/review/investment/CryptoForm.tsx`
- `frontend/components/review/investment/BankInterestForm.tsx`
- `frontend/components/review/investment/ManagedFundForm.tsx`
- `frontend/components/review/investment/ForeignIncomeForm.tsx`
- `frontend/__tests__/investment-utils.test.ts`
- `frontend/__tests__/SharesForm.test.tsx`
- `frontend/__tests__/CryptoForm.test.tsx`
- `frontend/__tests__/ForeignIncomeForm.test.tsx`

**Modify:**
- `backend/app/db/models.py` — add `metadata` column to `TaxEvent`
- `backend/app/repositories/events.py` — add `metadata`, `status`, `risk_level`, `possible_duplicate` params
- `backend/app/repositories/review.py` — inherit `status` from event instead of hardcoding
- `backend/app/engines/review.py` — add `metadata`, `review_status`, `possible_duplicate` params
- `backend/app/api/routes/events.py` — extend `ManualEventRequest`
- `backend/tests/test_events.py` — 2 new tests
- `frontend/lib/api/types.ts` — add `InvestmentSubType`, extend `ManualEventPayload`
- `frontend/components/review/ManualEntryForm.tsx` — insert investment sub-type routing
- `frontend/__tests__/ManualEntryForm.test.tsx` — 2 new tests

---

### Task 1: Backend — metadata column + repo/engine/route + tests

**Files:**
- Modify: `backend/app/db/models.py:137`
- Modify: `backend/app/repositories/events.py:19-55`
- Modify: `backend/app/repositories/review.py:31`
- Modify: `backend/app/engines/review.py:120-189`
- Modify: `backend/app/api/routes/events.py:23-72`
- Modify: `backend/tests/test_events.py` (append 2 tests)

- [ ] **Step 1: Write 2 failing tests — append to `backend/tests/test_events.py`**

```python
@pytest.mark.asyncio
async def test_create_manual_event_stores_metadata(db_session, workspace):
    """metadata dict is persisted on the TaxEvent."""
    import asyncio
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    meta = {"investment_sub_type": "shares", "transaction_type": "buy", "units": 100}

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = asyncio.sleep(0)
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="capital_gain",
            description="Shares Buy: 100 × CBA @ $82.50",
            amount=8259.95,
            date="2025-08-15",
            frequency="one_off",
            note=None,
            periods=None,
            metadata=meta,
            db=db_session,
        )

    assert events[0].metadata == meta


@pytest.mark.asyncio
async def test_create_manual_event_needs_agent_review_sets_status_on_event_and_review_item(
    db_session, workspace
):
    """review_status='needs_agent_review' propagates to TaxEvent and ReviewItem."""
    import asyncio
    from app.engines.review import ReviewEngine
    from sqlalchemy import select
    from app.db.models import ReviewItem as ReviewItemModel

    engine = ReviewEngine()

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = asyncio.sleep(0)
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="foreign_income",
            description="US Dividends",
            amount=500.0,
            date="2025-03-01",
            frequency="one_off",
            note=None,
            periods=None,
            metadata={"investment_sub_type": "foreign_income"},
            review_status="needs_agent_review",
            db=db_session,
        )

    assert events[0].status == "needs_agent_review"
    assert events[0].risk_level == "high"

    result = await db_session.execute(
        select(ReviewItemModel).where(ReviewItemModel.tax_event_id == events[0].id)
    )
    item = result.scalar_one()
    assert item.status == "needs_agent_review"
```

- [ ] **Step 2: Run tests — verify RED**

```bash
docker compose exec backend pytest tests/test_events.py -v -k "metadata or needs_agent_review" 2>&1 | tail -20
```

Expected: 2 failures (TypeError: unexpected keyword argument `metadata`)

- [ ] **Step 3: Add `metadata` column to `TaxEvent` in `backend/app/db/models.py`**

After line 138 (`correction_history`), add:
```python
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

- [ ] **Step 4: Generate and apply migration**

```bash
make migration MSG="add metadata column to tax_events"
make migrate-dev
```

Verify the generated file in `backend/alembic/versions/` shows `op.add_column('tax_events', sa.Column('metadata', sa.JSON(), nullable=True))`.

- [ ] **Step 5: Update `create_event` in `backend/app/repositories/events.py`**

Replace the function with:

```python
async def create_event(
    db: AsyncSession,
    workspace_id: str,
    financial_year: str,
    event_type: str,
    category: str,
    description: str | None,
    amount: float | None,
    date: str | None,
    source: str,
    note: str | None = None,
    group_id: str | None = None,
    group_display: str | None = None,
    is_recurring: bool = False,
    recurrence_index: int | None = None,
    metadata: dict | None = None,
    status: str = "needs_user_review",
    risk_level: str = "low",
    possible_duplicate: bool = False,
) -> TaxEvent:
    event = TaxEvent(
        workspace_id=workspace_id,
        financial_year=financial_year,
        event_type=event_type,
        category=category,
        description=description,
        amount=amount,
        date=date,
        source=source,
        user_note=note,
        group_id=group_id,
        group_display=group_display,
        is_recurring=is_recurring,
        recurrence_index=recurrence_index,
        status=status,
        risk_level=risk_level,
        metadata=metadata,
        possible_duplicate=possible_duplicate,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event
```

- [ ] **Step 6: Fix `review_repo.create` to inherit status — `backend/app/repositories/review.py:31`**

Change:
```python
        status="needs_user_review",
```
To:
```python
        status=event.status,
```

- [ ] **Step 7: Update `create_manual_event` in `backend/app/engines/review.py`**

Change the signature (add three new keyword args at the end, before `db`):
```python
    async def create_manual_event(
        self,
        workspace_id: str,
        financial_year: str,
        event_type: str,
        category: str,
        description: str,
        amount: float,
        date: str,
        frequency: str,
        note: str | None,
        periods: list[dict] | None,
        db: AsyncSession,
        metadata: dict | None = None,
        review_status: str | None = None,
        possible_duplicate: bool = False,
    ) -> list[TaxEvent]:
```

At the top of the method body, add:
```python
        _status = review_status or "needs_user_review"
        _risk = "high" if review_status == "needs_agent_review" else "low"
```

In the monthly branch, update both `create_event` calls to pass the new params:
```python
                event = await events_repo.create_event(
                    db,
                    workspace_id=workspace_id,
                    financial_year=financial_year,
                    event_type=event_type,
                    category=category,
                    description=description,
                    amount=period_amount,
                    date=date,
                    source="manual_entry",
                    note=note,
                    group_id=group_id,
                    group_display=group_display,
                    is_recurring=True,
                    recurrence_index=idx,
                    metadata=metadata,
                    status=_status,
                    risk_level=_risk,
                    possible_duplicate=possible_duplicate,
                )
```

In the one-off branch:
```python
            event = await events_repo.create_event(
                db,
                workspace_id=workspace_id,
                financial_year=financial_year,
                event_type=event_type,
                category=category,
                description=description,
                amount=amount,
                date=date,
                source="manual_entry",
                note=note,
                group_id=None,
                group_display=None,
                is_recurring=False,
                recurrence_index=None,
                metadata=metadata,
                status=_status,
                risk_level=_risk,
                possible_duplicate=possible_duplicate,
            )
```

- [ ] **Step 8: Update `ManualEventRequest` and route in `backend/app/api/routes/events.py`**

Replace `ManualEventRequest`:
```python
class ManualEventRequest(BaseModel):
    event_type: str
    category: str
    description: str
    amount: float
    date: str
    frequency: str
    note: str | None = None
    periods: list[_Period] | None = None
    metadata: dict | None = None
    review_status: str | None = None
    possible_duplicate: bool = False
```

In `create_manual_event` route, update the engine call to pass new fields:
```python
        events = await _review_engine.create_manual_event(
            workspace_id=workspace_id,
            financial_year=fy,
            event_type=body.event_type,
            category=body.category,
            description=body.description,
            amount=body.amount,
            date=body.date,
            frequency=body.frequency,
            note=body.note,
            periods=[p.model_dump() for p in body.periods] if body.periods else None,
            db=db,
            metadata=body.metadata,
            review_status=body.review_status,
            possible_duplicate=body.possible_duplicate,
        )
```

- [ ] **Step 9: Run tests — verify GREEN**

```bash
docker compose exec backend pytest tests/test_events.py -v 2>&1 | tail -20
```

Expected: all 5 tests pass.

- [ ] **Step 10: Commit**

```bash
git add backend/app/db/models.py backend/app/repositories/events.py backend/app/repositories/review.py backend/app/engines/review.py backend/app/api/routes/events.py backend/tests/test_events.py backend/alembic/versions/
git commit -m "feat: add metadata + agent-review status to manual event creation"
```

---

### Task 2: Frontend — types + utils + utility tests

**Files:**
- Create: `frontend/lib/utils/investment.ts`
- Create: `frontend/__tests__/investment-utils.test.ts`
- Modify: `frontend/lib/api/types.ts:280-308`

- [ ] **Step 1: Write failing utility tests — create `frontend/__tests__/investment-utils.test.ts`**

```typescript
import { daysBetween, cgtDiscountEligible } from '@/lib/utils/investment'

test('daysBetween returns 30 for Jan 1–31', () => {
  expect(daysBetween('2024-01-01', '2024-01-31')).toBe(30)
})

test('daysBetween is order-independent', () => {
  expect(daysBetween('2024-01-31', '2024-01-01')).toBe(30)
})

test('cgtDiscountEligible: true for exactly 365 days', () => {
  expect(cgtDiscountEligible(365)).toBe(true)
})

test('cgtDiscountEligible: true for > 365 days', () => {
  expect(cgtDiscountEligible(400)).toBe(true)
})

test('cgtDiscountEligible: false for 364 days', () => {
  expect(cgtDiscountEligible(364)).toBe(false)
})
```

- [ ] **Step 2: Run tests — verify RED**

```bash
make test 2>&1 | grep -A5 "investment-utils"
```

Expected: `Cannot find module '@/lib/utils/investment'`

- [ ] **Step 3: Create `frontend/lib/utils/investment.ts`**

```typescript
export function daysBetween(d1: string, d2: string): number {
  const ms = Math.abs(new Date(d2).getTime() - new Date(d1).getTime())
  return Math.floor(ms / (1000 * 60 * 60 * 24))
}

export function cgtDiscountEligible(days: number): boolean {
  return days >= 365
}
```

- [ ] **Step 4: Run utility tests — verify GREEN**

```bash
make test 2>&1 | grep -E "investment-utils|PASS|FAIL" | head -5
```

Expected: `PASS __tests__/investment-utils.test.ts`

- [ ] **Step 5: Update `frontend/lib/api/types.ts`**

After the existing `export type ManualEventType = ...` line (line ~280), add:

```typescript
export type InvestmentSubType = 'shares' | 'crypto' | 'bank_interest' | 'managed_fund' | 'foreign_income' | 'other'
```

Replace the `ManualEventPayload` interface:

```typescript
export interface ManualEventPayload {
  event_type: ManualEventType
  category: string
  description: string
  amount: number
  date: string
  frequency: ManualEventFrequency
  note: string | null
  periods: ManualEventPeriod[] | null
  metadata?: Record<string, unknown>
  review_status?: string
  possible_duplicate?: boolean
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/utils/investment.ts frontend/__tests__/investment-utils.test.ts frontend/lib/api/types.ts
git commit -m "feat: add investment utils (daysBetween, CGT) and extend ManualEventPayload types"
```

---

### Task 3: Frontend — SharesForm + tests

**Files:**
- Create: `frontend/components/review/investment/SharesForm.tsx`
- Create: `frontend/__tests__/SharesForm.test.tsx`

- [ ] **Step 1: Write failing tests — create `frontend/__tests__/SharesForm.test.tsx`**

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SharesForm from '@/components/review/investment/SharesForm'
import * as eventsApi from '@/lib/api/events'

jest.mock('@/lib/api/events')
const mockCreate = eventsApi.createManualEvent as jest.Mock
beforeEach(() => jest.clearAllMocks())

test('shows Buy / Sell / Dividend sub-type selector by default', () => {
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} />)
  expect(screen.getByRole('button', { name: /^buy$/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^sell$/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^dividend$/i })).toBeInTheDocument()
})

test('buy form: total cost auto-calculates (units × price + brokerage)', async () => {
  const user = userEvent.setup()
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /^buy$/i }))

  await user.type(screen.getByLabelText(/number of units/i), '100')
  await user.type(screen.getByLabelText(/price per unit/i), '82.50')
  await user.type(screen.getByLabelText(/brokerage fee/i), '9.95')

  expect(screen.getByText('$8259.95')).toBeInTheDocument()
})

test('sell form: CGT discount shown for holdings >= 365 days', async () => {
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: /^sell$/i }))

  fireEvent.change(screen.getByLabelText(/purchase date/i), { target: { value: '2023-01-01' } })
  fireEvent.change(screen.getByLabelText(/sale date/i), { target: { value: '2024-01-01' } })

  expect(screen.getByText(/50% CGT discount may apply/i)).toBeInTheDocument()
})

test('sell form: no CGT discount for holdings < 365 days', async () => {
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: /^sell$/i }))

  fireEvent.change(screen.getByLabelText(/purchase date/i), { target: { value: '2024-01-01' } })
  fireEvent.change(screen.getByLabelText(/sale date/i), { target: { value: '2024-06-30' } })

  expect(screen.getByText(/No CGT discount/i)).toBeInTheDocument()
})

test('buy form: required validation shows errors on empty submit', async () => {
  const user = userEvent.setup()
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /^buy$/i }))
  await user.click(screen.getByRole('button', { name: /add item/i }))
  const alerts = await screen.findAllByRole('alert')
  expect(alerts.length).toBeGreaterThan(0)
})
```

- [ ] **Step 2: Run tests — verify RED**

```bash
make test 2>&1 | grep -A5 "SharesForm"
```

Expected: `Cannot find module '@/components/review/investment/SharesForm'`

- [ ] **Step 3: Create `frontend/components/review/investment/SharesForm.tsx`**

```tsx
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

function CurrencyInput({ id, label, register, error, required = false, optional = false }: {
  id: string; label: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any; error?: string; required?: boolean; optional?: boolean
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
          className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
          {...register}
        />
      </div>
      {error && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{error}</p>}
    </div>
  )
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
      {totalCost !== null && <AutoCalcBox label="Total cost" value={totalCost.toFixed(2)} unit="$" />}
      <div>
        <label htmlFor="sb-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="sb-note" type="text" className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
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
          value={Math.abs(estimatedGainLoss).toFixed(2)} unit="$" />
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
        <button type="button" onClick={onBack} className="min-h-11 px-4 text-sm font-ui text-text-muted">Cancel</button>
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
            className="w-full pl-7 pr-4 py-2 rounded-md border border-border bg-surface font-mono text-sm focus:outline-none focus:border-accent"
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
        <button type="button" onClick={onBack} className="min-h-11 px-4 text-sm font-ui text-text-muted">Cancel</button>
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
```

- [ ] **Step 4: Run SharesForm tests — verify GREEN**

```bash
make test 2>&1 | grep -E "SharesForm|PASS|FAIL" | head -10
```

Expected: `PASS __tests__/SharesForm.test.tsx`

- [ ] **Step 5: Commit**

```bash
git add frontend/components/review/investment/SharesForm.tsx frontend/__tests__/SharesForm.test.tsx
git commit -m "feat: add SharesForm (Buy/Sell/Dividend) with CGT auto-calc"
```

---

### Task 4: Frontend — CryptoForm + tests

**Files:**
- Create: `frontend/components/review/investment/CryptoForm.tsx`
- Create: `frontend/__tests__/CryptoForm.test.tsx`

- [ ] **Step 1: Write failing tests — create `frontend/__tests__/CryptoForm.test.tsx`**

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CryptoForm from '@/components/review/investment/CryptoForm'
import * as eventsApi from '@/lib/api/events'

jest.mock('@/lib/api/events')
const mockCreate = eventsApi.createManualEvent as jest.Mock
beforeEach(() => jest.clearAllMocks())

test('shows Buy / Sell / Staking sub-type selector by default', () => {
  render(<CryptoForm onSuccess={jest.fn()} onBack={jest.fn()} />)
  expect(screen.getByRole('button', { name: /^buy$/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^sell$/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /staking/i })).toBeInTheDocument()
})

test('sell form: estimated gain/loss auto-calculates', async () => {
  const user = userEvent.setup()
  render(<CryptoForm onSuccess={jest.fn()} onBack={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /^sell$/i }))

  await user.type(screen.getByLabelText(/sale price \(AUD\)/i), '1000')
  await user.type(screen.getByLabelText(/transaction fee/i), '10')
  await user.type(screen.getByLabelText(/purchase price \(AUD\)/i), '800')

  // (1000 - 10) - 800 = 190
  expect(screen.getByText('$190.00')).toBeInTheDocument()
})

test('staking form: submits with review_status = needs_agent_review', async () => {
  mockCreate.mockResolvedValue({ data: { data: { items: [], count: 0 } } })
  const user = userEvent.setup()
  render(<CryptoForm onSuccess={jest.fn()} onBack={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /staking/i }))

  await user.type(screen.getByLabelText(/platform/i), 'CoinSpot')
  await user.type(screen.getByLabelText(/coin/i), 'ETH')
  await user.type(screen.getByLabelText(/income amount/i), '500')
  fireEvent.change(screen.getByLabelText(/income date/i), { target: { value: '2024-11-01' } })

  await user.click(screen.getByRole('button', { name: /add item/i }))

  await waitFor(() => {
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({ review_status: 'needs_agent_review' })
    )
  })
})

test('staking form: validation shows error on empty submit', async () => {
  const user = userEvent.setup()
  render(<CryptoForm onSuccess={jest.fn()} onBack={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /staking/i }))
  await user.click(screen.getByRole('button', { name: /add item/i }))
  const alerts = await screen.findAllByRole('alert')
  expect(alerts.length).toBeGreaterThan(0)
})
```

- [ ] **Step 2: Run tests — verify RED**

```bash
make test 2>&1 | grep -A5 "CryptoForm"
```

- [ ] **Step 3: Create `frontend/components/review/investment/CryptoForm.tsx`**

```tsx
'use client'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { createManualEvent } from '@/lib/api/events'
import { daysBetween, cgtDiscountEligible } from '@/lib/utils/investment'

type CryptoSubType = 'buy' | 'sell' | 'staking'

interface InvestmentFormProps { onSuccess: () => void; onBack: () => void }

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

function AutoCalcBox({ label, value, unit = '' }: { label: string; value: string; unit?: string }) {
  return (
    <div className="rounded-md bg-surface-raised px-4 py-2 space-y-0.5">
      <p className="text-xs font-ui text-text-muted uppercase tracking-wide">{label}</p>
      <p className="font-mono text-text-muted">{unit}{value}</p>
      <p className="text-xs font-ui text-text-muted italic">Estimate only — confirm with your tax agent</p>
    </div>
  )
}

function CryptoBuySubForm({ onSuccess, onBack }: InvestmentFormProps) {
  const { register, handleSubmit, formState: { errors } } = useForm<CryptoBuyFields>()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(data: CryptoBuyFields) {
    const price = parseFloat(data.purchase_price)
    const fee = parseFloat(data.transaction_fee || '0') || 0
    setPending(true); setError(null)
    try {
      await createManualEvent({
        event_type: 'investment', category: 'crypto',
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
      onSuccess()
    } catch { setError('Something went wrong. Please try again.') }
    finally { setPending(false) }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
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
          {...register('purchase_date', { required: 'Purchase date is required.' })} />
        {errors.purchase_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.purchase_date.message}</p>}
      </div>
      <div>
        <label htmlFor="cb-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="cb-note" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
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

function CryptoSellSubForm({ onSuccess, onBack }: InvestmentFormProps) {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<CryptoSellFields>()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const purchaseDate = watch('purchase_date')
  const saleDate = watch('sale_date')
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
    setPending(true); setError(null)
    try {
      await createManualEvent({
        event_type: 'investment', category: 'crypto',
        description: `Crypto Sell: ${data.amount_units} ${data.coin.toUpperCase()}`,
        amount: sp - f, date: data.sale_date,
        frequency: 'one_off', note: data.note?.trim() || null, periods: null,
        metadata: {
          investment_sub_type: 'crypto', transaction_type: 'sell',
          exchange: data.exchange, coin: data.coin.toUpperCase(),
          amount_units: data.amount_units, sale_price: sp,
          purchase_price: parseFloat(data.purchase_price),
          transaction_fee: f, sale_date: data.sale_date, purchase_date: data.purchase_date,
          cost_basis_method: data.cost_basis_method,
        },
      })
      onSuccess()
    } catch { setError('Something went wrong. Please try again.') }
    finally { setPending(false) }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
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
          {...register('sale_date', { required: 'Sale date is required.' })} />
        {errors.sale_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.sale_date.message}</p>}
      </div>
      <div>
        <label htmlFor="cs-purchase-date" className="text-sm font-ui text-text-body block mb-1">Purchase date</label>
        <input id="cs-purchase-date" type="date"
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
      {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
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

function CryptoStakingSubForm({ onSuccess, onBack }: InvestmentFormProps) {
  const { register, handleSubmit, formState: { errors } } = useForm<CryptoStakingFields>()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
      onSuccess()
    } catch { setError('Something went wrong. Please try again.') }
    finally { setPending(false) }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
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
        <div className="flex items-start gap-2 mb-1">
          <label htmlFor="cst-amount" className="text-sm font-ui text-text-body">Income amount (AUD)</label>
        </div>
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
          {...register('income_date', { required: 'Income date is required.' })} />
        {errors.income_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.income_date.message}</p>}
      </div>
      <div>
        <label htmlFor="cst-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="cst-note" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
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

export default function CryptoForm({ onSuccess, onBack }: InvestmentFormProps) {
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
      </div>
    )
  }

  const backToSubType = () => setSubType(null)
  if (subType === 'buy') return <CryptoBuySubForm onSuccess={onSuccess} onBack={backToSubType} />
  if (subType === 'sell') return <CryptoSellSubForm onSuccess={onSuccess} onBack={backToSubType} />
  return <CryptoStakingSubForm onSuccess={onSuccess} onBack={backToSubType} />
}
```

- [ ] **Step 4: Run CryptoForm tests — verify GREEN**

```bash
make test 2>&1 | grep -E "CryptoForm|PASS|FAIL" | head -10
```

- [ ] **Step 5: Commit**

```bash
git add frontend/components/review/investment/CryptoForm.tsx frontend/__tests__/CryptoForm.test.tsx
git commit -m "feat: add CryptoForm (Buy/Sell/Staking) with CGT auto-calc and agent-review flag"
```

---

### Task 5: Frontend — BankInterestForm + ManagedFundForm + ForeignIncomeForm + tests

**Files:**
- Create: `frontend/components/review/investment/BankInterestForm.tsx`
- Create: `frontend/components/review/investment/ManagedFundForm.tsx`
- Create: `frontend/components/review/investment/ForeignIncomeForm.tsx`
- Create: `frontend/__tests__/ForeignIncomeForm.test.tsx`

- [ ] **Step 1: Write failing ForeignIncomeForm tests — create `frontend/__tests__/ForeignIncomeForm.test.tsx`**

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ForeignIncomeForm from '@/components/review/investment/ForeignIncomeForm'
import * as eventsApi from '@/lib/api/events'

jest.mock('@/lib/api/events')
const mockCreate = eventsApi.createManualEvent as jest.Mock
beforeEach(() => jest.clearAllMocks())

test('AUD amount auto-calculates from foreign amount × exchange rate', async () => {
  const user = userEvent.setup()
  render(<ForeignIncomeForm onSuccess={jest.fn()} onBack={jest.fn()} />)

  await user.type(screen.getByLabelText(/amount \(foreign currency\)/i), '1000')
  await user.type(screen.getByLabelText(/exchange rate/i), '0.65')

  expect(screen.getByText('$650.00')).toBeInTheDocument()
})

test('always submits with review_status = needs_agent_review', async () => {
  mockCreate.mockResolvedValue({ data: { data: { items: [], count: 0 } } })
  const user = userEvent.setup()
  render(<ForeignIncomeForm onSuccess={jest.fn()} onBack={jest.fn()} />)

  await user.type(screen.getByLabelText(/country of origin/i), 'United States')
  await user.selectOptions(screen.getByLabelText(/income type/i), 'Dividends')
  await user.type(screen.getByLabelText(/amount \(foreign currency\)/i), '1000')
  await user.type(screen.getByLabelText(/currency/i), 'USD')
  await user.type(screen.getByLabelText(/exchange rate/i), '0.65')
  fireEvent.change(screen.getByLabelText(/income date/i), { target: { value: '2024-12-01' } })

  await user.click(screen.getByRole('button', { name: /add item/i }))

  await waitFor(() => {
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({ review_status: 'needs_agent_review' })
    )
  })
})

test('required validation shows errors on empty submit', async () => {
  const user = userEvent.setup()
  render(<ForeignIncomeForm onSuccess={jest.fn()} onBack={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /add item/i }))
  const alerts = await screen.findAllByRole('alert')
  expect(alerts.length).toBeGreaterThan(0)
})
```

- [ ] **Step 2: Run tests — verify RED**

```bash
make test 2>&1 | grep -A5 "ForeignIncomeForm"
```

- [ ] **Step 3: Create `frontend/components/review/investment/BankInterestForm.tsx`**

```tsx
'use client'
import { useForm } from 'react-hook-form'
import { useState } from 'react'
import { createManualEvent } from '@/lib/api/events'

interface InvestmentFormProps { onSuccess: () => void; onBack: () => void }

interface BankInterestFields {
  bank_name: string; account_type: string
  interest_amount: string; in_payg: boolean; note: string
}

export default function BankInterestForm({ onSuccess, onBack }: InvestmentFormProps) {
  const { register, handleSubmit, formState: { errors } } = useForm<BankInterestFields>()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(data: BankInterestFields) {
    const amt = parseFloat(data.interest_amount)
    setPending(true); setError(null)
    try {
      await createManualEvent({
        event_type: 'investment', category: 'bank_interest',
        description: `Bank Interest: ${data.bank_name} (${data.account_type})`,
        amount: amt, date: new Date().toISOString().slice(0, 10),
        frequency: 'annual', note: data.note?.trim() || null, periods: null,
        possible_duplicate: data.in_payg,
        metadata: {
          investment_sub_type: 'bank_interest',
          bank_name: data.bank_name, account_type: data.account_type,
          interest_amount: amt, in_payg: data.in_payg,
        },
      })
      onSuccess()
    } catch { setError('Something went wrong. Please try again.') }
    finally { setPending(false) }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <button type="button" onClick={onBack} className="text-sm font-ui text-text-muted">← Back</button>
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
        <label htmlFor="bi-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="bi-note" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
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
```

- [ ] **Step 4: Create `frontend/components/review/investment/ManagedFundForm.tsx`**

```tsx
'use client'
import { useForm } from 'react-hook-form'
import { useState } from 'react'
import { createManualEvent } from '@/lib/api/events'
import { Info } from 'lucide-react'

interface InvestmentFormProps { onSuccess: () => void; onBack: () => void }

interface ManagedFundFields {
  fund_name: string; fund_manager: string
  distribution_amount: string; capital_gains_component: string
  foreign_income_component: string; tfn_withholding_tax: string
  distribution_date: string; note: string
}

export default function ManagedFundForm({ onSuccess, onBack }: InvestmentFormProps) {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<ManagedFundFields>()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const capitalGains = parseFloat(watch('capital_gains_component') || '0') || 0

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
          tfn_withholding_tax: parseFloat(data.tfn_withholding_tax || '0') || 0,
          distribution_date: data.distribution_date,
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
        Please provide your fund's annual tax statement to your tax agent
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
          {...register('distribution_date', { required: 'Distribution date is required.' })} />
        {errors.distribution_date && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.distribution_date.message}</p>}
      </div>
      <div>
        <label htmlFor="mf-note" className="text-sm font-ui text-text-body block mb-1">Note (optional)</label>
        <input id="mf-note" type="text"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          {...register('note')} />
      </div>
      {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
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
```

- [ ] **Step 5: Create `frontend/components/review/investment/ForeignIncomeForm.tsx`**

```tsx
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

  const foreignAmount = parseFloat(watch('foreign_amount') || '0')
  const exchangeRate = parseFloat(watch('exchange_rate') || '0')
  const audAmount = foreignAmount > 0 && exchangeRate > 0 ? foreignAmount * exchangeRate : null

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
        <label htmlFor="fi-amount" className="text-sm font-ui text-text-body block mb-1">Amount (foreign currency)</label>
        <input id="fi-amount" type="number" min="0" step="0.01"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          {...register('foreign_amount', { required: 'Amount is required.' })} />
        {errors.foreign_amount && <p role="alert" className="text-sm font-ui text-risk-high mt-1">{errors.foreign_amount.message}</p>}
      </div>
      <div>
        <label htmlFor="fi-currency" className="text-sm font-ui text-text-body block mb-1">Currency</label>
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
          Use the ATO's average annual rate or the rate on the date received
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
      {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
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
```

- [ ] **Step 6: Run ForeignIncomeForm tests — verify GREEN**

```bash
make test 2>&1 | grep -E "ForeignIncomeForm|PASS|FAIL" | head -10
```

- [ ] **Step 7: Commit**

```bash
git add frontend/components/review/investment/BankInterestForm.tsx frontend/components/review/investment/ManagedFundForm.tsx frontend/components/review/investment/ForeignIncomeForm.tsx frontend/__tests__/ForeignIncomeForm.test.tsx
git commit -m "feat: add BankInterestForm, ManagedFundForm, ForeignIncomeForm"
```

---

### Task 6: Frontend — ManualEntryForm update + test updates

**Files:**
- Modify: `frontend/components/review/ManualEntryForm.tsx`
- Modify: `frontend/__tests__/ManualEntryForm.test.tsx`

- [ ] **Step 1: Add 2 failing tests to `frontend/__tests__/ManualEntryForm.test.tsx`**

After the existing `describe('ManualEntryForm', () => {` block, append inside the describe:

```tsx
  it('clicking Investment shows investment sub-type selector', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^investment$/i))
    expect(screen.getByRole('button', { name: /shares \/ ETF/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cryptocurrency/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /bank interest/i })).toBeInTheDocument()
  })

  it('selecting Shares/ETF sub-type renders SharesForm', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^investment$/i))
    fireEvent.click(screen.getByRole('button', { name: /shares \/ ETF/i }))
    expect(screen.getByRole('button', { name: /^buy$/i })).toBeInTheDocument()
  })
```

- [ ] **Step 2: Run tests — verify RED**

```bash
make test 2>&1 | grep -A5 "ManualEntryForm"
```

Expected: the 2 new tests fail.

- [ ] **Step 3: Update `frontend/components/review/ManualEntryForm.tsx`**

Add imports at the top (after existing imports):

```tsx
import type { InvestmentSubType } from '@/lib/api/types'
import SharesForm from './investment/SharesForm'
import CryptoForm from './investment/CryptoForm'
import BankInterestForm from './investment/BankInterestForm'
import ManagedFundForm from './investment/ManagedFundForm'
import ForeignIncomeForm from './investment/ForeignIncomeForm'
```

Add state inside the component (after `const [error, setError] = useState<string | null>(null)`):

```tsx
  const [investmentSubType, setInvestmentSubType] = useState<InvestmentSubType | null>(null)
```

Add a reset of `investmentSubType` when going back to step 1. In the existing step 1 button handler `onClick`:
```tsx
onClick={() => {
  setEventType(opt.value)
  setCategory(TYPE_CATEGORIES[opt.value][0])
  setInvestmentSubType(null)
  setStep(2)
}}
```

Before the existing `if (step === 1) { return ... }` block, insert the investment routing blocks. Add these immediately before the existing `return (` that renders the generic form (i.e., immediately after the `if (step === 1)` block):

```tsx
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
      </div>
    )
  }

  // Investment: specific sub-form
  if (step === 2 && eventType === 'investment' && investmentSubType !== null && investmentSubType !== 'other') {
    const backToSubType = () => setInvestmentSubType(null)
    if (investmentSubType === 'shares') return <SharesForm onSuccess={onSuccess} onBack={backToSubType} />
    if (investmentSubType === 'crypto') return <CryptoForm onSuccess={onSuccess} onBack={backToSubType} />
    if (investmentSubType === 'bank_interest') return <BankInterestForm onSuccess={onSuccess} onBack={backToSubType} />
    if (investmentSubType === 'managed_fund') return <ManagedFundForm onSuccess={onSuccess} onBack={backToSubType} />
    if (investmentSubType === 'foreign_income') return <ForeignIncomeForm onSuccess={onSuccess} onBack={backToSubType} />
  }
```

The existing generic form (the `return (<form ...>` block) now handles: non-investment types AND `investmentSubType === 'other'`.

- [ ] **Step 4: Run ManualEntryForm tests — verify GREEN**

```bash
make test 2>&1 | grep -E "ManualEntryForm|PASS|FAIL" | head -10
```

- [ ] **Step 5: Commit**

```bash
git add frontend/components/review/ManualEntryForm.tsx frontend/__tests__/ManualEntryForm.test.tsx
git commit -m "feat: route investment sub-types to dedicated forms in ManualEntryForm"
```

---

### Task 7: Full test suite verification

- [ ] **Step 1: Run full backend test suite**

```bash
docker compose exec backend pytest tests/ -v 2>&1 | tail -20
```

Expected: all existing tests pass plus 2 new ones = 192+ tests passing.

- [ ] **Step 2: Run full frontend test suite**

```bash
make test 2>&1 | tail -20
```

Expected: all existing tests pass plus new investment form tests.

- [ ] **Step 3: If any tests fail, fix before proceeding**

Common failure points:
- `TypeError: create_manual_event() got unexpected keyword` — check `review.py` engine signature
- Missing `metadata` import in test — the test fixture creates a `TaxEvent` directly; ensure the model column is migrated
- Frontend: `Cannot read properties of undefined` — check `watch()` returns for unset fields use `|| '0'` fallback

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "test: verify full suite passes after investment forms redesign"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Investment sub-type selector (Shares, Crypto, Bank Interest, Managed Fund, Foreign, Other) | Task 6 |
| Form A: Shares — Buy/Sell/Dividend with all fields | Task 3 |
| Buy total cost auto-calc | Task 3 |
| Sell CGT discount + gain/loss auto-calc | Task 3 |
| Dividend franking credits + PAYG possible_duplicate | Task 3 |
| Form B: Crypto — Buy/Sell/Staking | Task 4 |
| Staking → needs_agent_review | Task 4 |
| Crypto sell gain/loss auto-calc | Task 4 |
| Form C: Bank Interest with PAYG checkbox | Task 5 |
| Form D: Managed Fund with CGT component flag | Task 5 |
| Form E: Foreign Income with AUD auto-calc + needs_agent_review | Task 5 |
| Form F: Other — existing generic form | Task 6 (fallback path) |
| Backend metadata JSON column | Task 1 |
| Alembic migration | Task 1 |
| All forms: RHF validation, no HTML required | Tasks 3–6 |
| Tests: total cost, CGT discount, gain/loss, staking flag, foreign AUD, foreign flag | Tasks 3–5 |

**Placeholder scan:** None found — every step has complete code.

**Type consistency:**
- `InvestmentSubType` defined in Task 2, used in Task 6 ✓
- `createManualEvent` payload extended in Task 2, used in Tasks 3–6 ✓
- `metadata`, `review_status`, `possible_duplicate` added to backend in Task 1, passed from frontend in Tasks 3–5 ✓
- `daysBetween` / `cgtDiscountEligible` defined in Task 2, imported in Tasks 3–4 ✓
