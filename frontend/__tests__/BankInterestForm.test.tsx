import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BankInterestForm from '@/components/review/investment/BankInterestForm'
import * as eventsApi from '@/lib/api/events'

jest.mock('@/lib/api/events')
jest.mock('@/lib/stores/workspace.store', () => ({
  __esModule: true,
  default: jest.fn(() => ({
    financialYear: '2024-25',
  })),
}))

const mockCreate = eventsApi.createManualEvent as jest.Mock

beforeEach(() => {
  jest.clearAllMocks()
})

test('renders explicit statement period fields', () => {
  render(<BankInterestForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  expect(screen.getByLabelText(/statement period start/i)).toBeInTheDocument()
  expect(screen.getByLabelText(/statement period end/i)).toBeInTheDocument()
})

test('submits expected bank interest metadata including period and financial year', async () => {
  mockCreate.mockResolvedValue({ data: { data: { items: [], count: 0 } } })
  const user = userEvent.setup()
  render(<BankInterestForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  await user.type(screen.getByLabelText(/bank name/i), 'CBA')
  await user.selectOptions(screen.getByLabelText(/account type/i), 'Savings')
  await user.type(screen.getByLabelText(/interest amount/i), '120')
  fireEvent.change(screen.getByLabelText(/statement period start/i), { target: { value: '2024-07-01' } })
  fireEvent.change(screen.getByLabelText(/statement period end/i), { target: { value: '2025-06-30' } })

  await user.click(screen.getByRole('button', { name: /add item/i }))

  await waitFor(() =>
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        event_type: 'investment',
        category: 'bank_interest',
        date: '2025-06-30',
        metadata: expect.objectContaining({
          investment_sub_type: 'bank_interest',
          bank_name: 'CBA',
          account_type: 'Savings',
          interest_amount: 120,
          statement_period_start: '2024-07-01',
          statement_period_end: '2025-06-30',
          financial_year: '2024-25',
        }),
      })
    )
  )
})
