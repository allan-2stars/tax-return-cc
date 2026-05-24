import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ManualEntryForm from '@/components/review/ManualEntryForm'
import * as eventsApi from '@/lib/api/events'

jest.mock('@/lib/api/events')
const mockCreate = eventsApi.createManualEvent as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('ManualEntryForm', () => {
  it('step 1 renders 5 type options', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    expect(screen.getByText(/income/i)).toBeInTheDocument()
    expect(screen.getByText(/deduction/i)).toBeInTheDocument()
    expect(screen.getByText(/investment/i)).toBeInTheDocument()
    expect(screen.getByText(/work from home/i)).toBeInTheDocument()
    expect(screen.getByText(/other/i)).toBeInTheDocument()
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
    expect(options).not.toContain('payg_income')
  })

  it('monthly recurring calculates FY total correctly', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/deduction/i))

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
})
