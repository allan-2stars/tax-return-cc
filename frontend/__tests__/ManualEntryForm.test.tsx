import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ManualEntryForm from '@/components/review/ManualEntryForm'
import * as eventsApi from '@/lib/api/events'

jest.mock('@/lib/api/events')
const mockCreate = eventsApi.createManualEvent as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('ManualEntryForm', () => {
  it('step 1 heading uses improved wording', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    expect(screen.getByText(/what would you like to add\?/i)).toBeInTheDocument()
  })

  it('step 1 renders 4 top-level type options and excludes Work from home', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    expect(screen.getByText(/income/i)).toBeInTheDocument()
    expect(screen.getByText(/deduction/i)).toBeInTheDocument()
    expect(screen.getByText(/investment/i)).toBeInTheDocument()
    expect(screen.getByText(/other/i)).toBeInTheDocument()
    expect(screen.queryByText(/work from home/i)).not.toBeInTheDocument()
  })

  it('step 2 shows correct fields for Deduction', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/deduction/i))
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/amount/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/date/i)).toBeInTheDocument()
    const select = screen.getByLabelText(/category/i) as HTMLSelectElement
    const options = Array.from(select.options).map((o) => o.value)
    expect(options).toContain('work_expense')
    expect(options).toContain('work_subscription')
    expect(options).toContain('wfh_deduction')
    expect(options).not.toContain('payg_income')
  })

  it('monthly recurring calculates FY total correctly', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/deduction/i))
    fireEvent.change(screen.getByLabelText(/category/i), { target: { value: 'work_subscription' } })

    fireEvent.click(screen.getByText(/monthly/i))

    const monthsInput = screen.getByLabelText(/period 1 months/i)
    const amountInput = screen.getByLabelText(/period 1 amount per month/i)
    fireEvent.change(monthsInput, { target: { value: '12' } })
    fireEvent.change(amountInput, { target: { value: '10' } })

    expect(screen.getByText(/\$120\.00/)).toBeInTheDocument()
  })

  it('variable pricing with two periods calculates total correctly', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/deduction/i))
    fireEvent.change(screen.getByLabelText(/category/i), { target: { value: 'work_subscription' } })
    fireEvent.click(screen.getByText(/monthly/i))

    fireEvent.change(screen.getByLabelText(/period 1 months/i), { target: { value: '6' } })
    fireEvent.change(screen.getByLabelText(/period 1 amount per month/i), { target: { value: '5' } })

    fireEvent.click(screen.getByText(/add pricing period/i))

    fireEvent.change(screen.getByLabelText(/period 2 months/i), { target: { value: '6' } })
    fireEvent.change(screen.getByLabelText(/period 2 amount per month/i), { target: { value: '7' } })

    expect(screen.getByText(/\$72\.00/)).toBeInTheDocument()
  })

  it('clicking Investment shows investment sub-type selector', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^investment$/i))
    expect(screen.getByRole('button', { name: /^← Back$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /shares \/ ETF/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cryptocurrency/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /bank interest/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument()
  })

  it('selecting Shares/ETF sub-type renders SharesForm', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^investment$/i))
    fireEvent.click(screen.getByRole('button', { name: /shares \/ ETF/i }))
    expect(screen.getByRole('button', { name: /^buy$/i })).toBeInTheDocument()
  })

  it('Investment -> Crypto -> Buy: Back returns to crypto transaction selector', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^investment$/i))
    fireEvent.click(screen.getByRole('button', { name: /cryptocurrency/i }))
    fireEvent.click(screen.getByRole('button', { name: /^buy$/i }))

    fireEvent.click(screen.getByRole('button', { name: /back/i }))
    expect(screen.getByRole('button', { name: /^buy$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^sell$/i })).toBeInTheDocument()
  })

  it('Investment -> Crypto -> Buy: Cancel exits entire wizard', () => {
    const onCancel = jest.fn()
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={onCancel} />)
    fireEvent.click(screen.getByText(/^investment$/i))
    fireEvent.click(screen.getByRole('button', { name: /cryptocurrency/i }))
    fireEvent.click(screen.getByRole('button', { name: /^buy$/i }))

    const buttons = screen.getAllByRole('button', { name: /^cancel$/i })
    fireEvent.click(buttons[buttons.length - 1])
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('Investment -> Shares -> Sell: Cancel exits entire wizard', () => {
    const onCancel = jest.fn()
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={onCancel} />)
    fireEvent.click(screen.getByText(/^investment$/i))
    fireEvent.click(screen.getByRole('button', { name: /shares \/ ETF/i }))
    fireEvent.click(screen.getByRole('button', { name: /^sell$/i }))

    const buttons = screen.getAllByRole('button', { name: /^cancel$/i })
    fireEvent.click(buttons[buttons.length - 1])
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('Investment -> Bank Interest: Cancel exits entire wizard', () => {
    const onCancel = jest.fn()
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={onCancel} />)
    fireEvent.click(screen.getByText(/^investment$/i))
    fireEvent.click(screen.getByRole('button', { name: /bank interest/i }))
    fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('Investment -> Managed Fund: Cancel exits entire wizard', () => {
    const onCancel = jest.fn()
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={onCancel} />)
    fireEvent.click(screen.getByText(/^investment$/i))
    fireEvent.click(screen.getByRole('button', { name: /managed fund/i }))
    fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('Investment -> Foreign Income: Cancel exits entire wizard', () => {
    const onCancel = jest.fn()
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={onCancel} />)
    fireEvent.click(screen.getByText(/^investment$/i))
    fireEvent.click(screen.getByRole('button', { name: /foreign income \/ investment/i }))
    fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('Income simple form: Back returns to previous step', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^income$/i))
    fireEvent.click(screen.getByRole('button', { name: /^← Back$/i }))
    expect(screen.getByText(/what would you like to add\?/i)).toBeInTheDocument()
  })

  it('Deduction simple form: Back returns to previous step', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^deduction$/i))
    fireEvent.click(screen.getByRole('button', { name: /^← Back$/i }))
    expect(screen.getByText(/what would you like to add\?/i)).toBeInTheDocument()
  })

  it('manual entry flow has no bare "Back" button label', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^investment$/i))
    fireEvent.click(screen.getByRole('button', { name: /shares \/ ETF/i }))
    fireEvent.click(screen.getByRole('button', { name: /^buy$/i }))
    expect(screen.queryByRole('button', { name: /^Back$/ })).not.toBeInTheDocument()
  })

  it('donation category renders tax-specific fields', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^deduction$/i))
    fireEvent.change(screen.getByLabelText(/category/i), { target: { value: 'donation' } })
    expect(screen.getByLabelText(/charity name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/ABN/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/DGR confirmed/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/donation amount/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/donation date/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/receipt available/i)).toBeInTheDocument()
  })

  it('work_expense category renders tax-specific fields', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^deduction$/i))
    fireEvent.change(screen.getByLabelText(/category/i), { target: { value: 'work_expense' } })
    expect(screen.getByLabelText(/expense type/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/vendor/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^amount/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/purchase date/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/work-related percentage/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/receipt available/i)).toBeInTheDocument()
  })

  it('wfh_deduction category renders tax-specific fields', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^deduction$/i))
    fireEvent.change(screen.getByLabelText(/category/i), { target: { value: 'wfh_deduction' } })
    expect(screen.getByLabelText(/method/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/financial year/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/hours/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/actual cost amount/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/evidence available/i)).toBeInTheDocument()
  })

  it('donation submits expected metadata payload', async () => {
    mockCreate.mockResolvedValue({ data: { data: { items: [], count: 0 } } })
    const onSuccess = jest.fn()
    render(<ManualEntryForm onSuccess={onSuccess} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^deduction$/i))
    fireEvent.change(screen.getByLabelText(/category/i), { target: { value: 'donation' } })
    fireEvent.change(screen.getByLabelText(/charity name/i), { target: { value: 'Red Cross' } })
    fireEvent.change(screen.getByLabelText(/ABN/i), { target: { value: '12 345 678 901' } })
    fireEvent.click(screen.getByLabelText(/DGR confirmed/i))
    fireEvent.change(screen.getByLabelText(/donation amount/i), { target: { value: '150' } })
    fireEvent.change(screen.getByLabelText(/donation date/i), { target: { value: '2025-01-10' } })
    fireEvent.click(screen.getByLabelText(/receipt available/i))

    fireEvent.click(screen.getByRole('button', { name: /add item/i }))
    await waitFor(() => expect(mockCreate).toHaveBeenCalled())
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        category: 'donation',
        metadata: expect.objectContaining({
          schema_version: '2026.1',
          charity_name: 'Red Cross',
          dgr_confirmed: true,
          donation_amount: 150,
          donation_date: '2025-01-10',
          receipt_available: true,
        }),
      })
    )
    expect(onSuccess).toHaveBeenCalled()
  })

  it('shows validation error for donation when required fields missing', async () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/^deduction$/i))
    fireEvent.change(screen.getByLabelText(/category/i), { target: { value: 'donation' } })
    fireEvent.click(screen.getByRole('button', { name: /add item/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/charity name is required/i)
  })
})
