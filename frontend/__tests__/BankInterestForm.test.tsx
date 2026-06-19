import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BankInterestForm from '@/components/review/investment/BankInterestForm'
import * as eventsApi from '@/lib/api/events'

jest.mock('@/lib/api/events')
jest.mock('@/lib/stores/workspace.store', () => ({
  __esModule: true,
  default: jest.fn(() => ({
    workspaceId: 'workspace-1',
    financialYear: '2024-25',
  })),
}))

const mockCreate = eventsApi.createManualEvent as jest.Mock
const draftKey = 'tax-return-draft:workspace-1:2024-25:investment:bank_interest'

beforeEach(() => {
  jest.clearAllMocks()
  sessionStorage.clear()
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

test('saves and restores bank interest draft fields', async () => {
  const user = userEvent.setup()
  const { unmount } = render(<BankInterestForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  await user.type(screen.getByLabelText(/bank name/i), 'CBA')

  await waitFor(() => {
    expect(screen.getByText(/draft saved/i)).toBeInTheDocument()
    expect(sessionStorage.getItem(draftKey)).toContain('CBA')
  })

  unmount()
  render(<BankInterestForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  expect(screen.getByText(/draft found/i)).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: /restore draft/i }))
  expect(screen.getByLabelText(/bank name/i)).toHaveValue('CBA')
})

test('successful bank interest submit clears draft', async () => {
  mockCreate.mockResolvedValue({ data: { data: { items: [], count: 0 } } })
  const user = userEvent.setup()
  render(<BankInterestForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  await user.type(screen.getByLabelText(/bank name/i), 'CBA')
  await user.selectOptions(screen.getByLabelText(/account type/i), 'Savings')
  await user.type(screen.getByLabelText(/interest amount/i), '120')
  fireEvent.change(screen.getByLabelText(/statement period start/i), { target: { value: '2024-07-01' } })
  fireEvent.change(screen.getByLabelText(/statement period end/i), { target: { value: '2025-06-30' } })

  await waitFor(() => expect(sessionStorage.getItem(draftKey)).not.toBeNull())
  await user.click(screen.getByRole('button', { name: /add item/i }))

  await waitFor(() => expect(sessionStorage.getItem(draftKey)).toBeNull())
})

test('failed bank interest submit preserves draft', async () => {
  mockCreate.mockRejectedValue(new Error('network'))
  const user = userEvent.setup()
  render(<BankInterestForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  await user.type(screen.getByLabelText(/bank name/i), 'CBA')
  await user.selectOptions(screen.getByLabelText(/account type/i), 'Savings')
  await user.type(screen.getByLabelText(/interest amount/i), '120')
  fireEvent.change(screen.getByLabelText(/statement period start/i), { target: { value: '2024-07-01' } })
  fireEvent.change(screen.getByLabelText(/statement period end/i), { target: { value: '2025-06-30' } })

  await user.click(screen.getByRole('button', { name: /add item/i }))

  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/try again/i))
  expect(sessionStorage.getItem(draftKey)).toContain('CBA')
})

test('rejects unrealistic statement period date with field-level error and does not submit', async () => {
  const user = userEvent.setup()
  render(<BankInterestForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  await user.type(screen.getByLabelText(/bank name/i), 'CBA')
  await user.selectOptions(screen.getByLabelText(/account type/i), 'Savings')
  await user.type(screen.getByLabelText(/interest amount/i), '120')
  fireEvent.change(screen.getByLabelText(/statement period start/i), { target: { value: '0001-01-01' } })
  fireEvent.change(screen.getByLabelText(/statement period end/i), { target: { value: '2025-06-30' } })

  await user.click(screen.getByRole('button', { name: /add item/i }))

  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent(/1900/i)
  })
  expect(mockCreate).not.toHaveBeenCalled()
})

test('discard clears bank interest draft', async () => {
  const user = userEvent.setup()
  sessionStorage.setItem(draftKey, JSON.stringify({ bank_name: 'CBA' }))

  render(<BankInterestForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  await user.click(screen.getByRole('button', { name: /discard draft/i }))
  expect(sessionStorage.getItem(draftKey)).toBeNull()
})

test('bank interest draft stores only form fields', async () => {
  const user = userEvent.setup()
  render(<BankInterestForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  await user.type(screen.getByLabelText(/bank name/i), 'CBA')

  await waitFor(() => expect(sessionStorage.getItem(draftKey)).not.toBeNull())
  const stored = JSON.parse(sessionStorage.getItem(draftKey) || '{}')
  expect(stored).toHaveProperty('bank_name', 'CBA')
  expect(stored).not.toHaveProperty('recovery_key')
  expect(stored).not.toHaveProperty('auth_token')
  expect(stored).not.toHaveProperty('document_contents')
})

test('beforeunload warning is active only when bank interest draft is dirty', async () => {
  const user = userEvent.setup()
  render(<BankInterestForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  const cleanEvent = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(cleanEvent)
  expect(cleanEvent.defaultPrevented).toBe(false)

  await user.type(screen.getByLabelText(/bank name/i), 'CBA')
  await waitFor(() => expect(sessionStorage.getItem(draftKey)).not.toBeNull())

  const dirtyEvent = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(dirtyEvent)
  expect(dirtyEvent.defaultPrevented).toBe(true)
})
