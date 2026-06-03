import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ManagedFundForm from '@/components/review/investment/ManagedFundForm'
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
const draftKey = 'tax-return-draft:workspace-1:2024-25:investment:managed_fund'

beforeEach(() => {
  jest.clearAllMocks()
  sessionStorage.clear()
})

test('submits expected managed fund metadata', async () => {
  mockCreate.mockResolvedValue({ data: { data: { items: [], count: 0 } } })
  const user = userEvent.setup()
  render(<ManagedFundForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  await user.type(screen.getByLabelText(/fund name/i), 'Vanguard High Growth')
  await user.type(screen.getByLabelText(/distribution amount/i), '500')
  await user.type(screen.getByLabelText(/capital gains component/i), '100')
  await user.type(screen.getByLabelText(/foreign income component/i), '50')
  await user.type(screen.getByLabelText(/tfn withholding tax/i), '10')
  fireEvent.change(screen.getByLabelText(/distribution date/i), { target: { value: '2025-06-30' } })

  await user.click(screen.getByRole('button', { name: /add item/i }))

  await waitFor(() =>
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        event_type: 'investment',
        category: 'managed_fund_distribution',
        metadata: expect.objectContaining({
          investment_sub_type: 'managed_fund',
          fund_name: 'Vanguard High Growth',
          distribution_amount: 500,
          capital_gains_component: 100,
          foreign_income_component: 50,
          tfn_withholding: 10,
          distribution_date: '2025-06-30',
        }),
      })
    )
  )
})

test('shows validation error on missing required fund name', async () => {
  const user = userEvent.setup()
  render(<ManagedFundForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  await user.click(screen.getByRole('button', { name: /add item/i }))

  const alerts = await screen.findAllByRole('alert')
  expect(alerts.length).toBeGreaterThan(0)
})

test('saves and restores managed fund draft fields', async () => {
  const user = userEvent.setup()
  const { unmount } = render(<ManagedFundForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  await user.type(screen.getByLabelText(/fund name/i), 'Vanguard High Growth')

  await waitFor(() => {
    expect(screen.getByText(/draft saved/i)).toBeInTheDocument()
    expect(sessionStorage.getItem(draftKey)).toContain('Vanguard High Growth')
  })

  unmount()
  render(<ManagedFundForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  expect(screen.getByText(/draft found/i)).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: /restore draft/i }))
  expect(screen.getByLabelText(/fund name/i)).toHaveValue('Vanguard High Growth')
})
