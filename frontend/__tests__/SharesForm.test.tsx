import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SharesForm from '@/components/review/investment/SharesForm'
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
const buyDraftKey = 'tax-return-draft:workspace-1:2024-25:investment:shares:buy'

beforeEach(() => {
  jest.clearAllMocks()
  sessionStorage.clear()
})

test('shows Buy / Sell / Dividend sub-type selector by default', () => {
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  expect(screen.getByRole('button', { name: /^← Back$/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^buy$/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^sell$/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^dividend$/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument()
})

test('buy form: total cost auto-calculates (units × price + brokerage)', async () => {
  const user = userEvent.setup()
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /^buy$/i }))
  expect(screen.getByRole('button', { name: /^← Back$/i })).toBeInTheDocument()

  await user.type(screen.getByLabelText(/number of units/i), '100')
  await user.type(screen.getByLabelText(/price per unit/i), '82.50')
  await user.type(screen.getByLabelText(/brokerage fee/i), '9.95')

  await waitFor(() => expect(screen.getByText('$8259.95')).toBeInTheDocument())
  expect(screen.queryByRole('button', { name: /^Back$/ })).not.toBeInTheDocument()
})

test('sell form: CGT discount shown for holdings >= 365 days', async () => {
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: /^sell$/i }))
  expect(screen.getByRole('button', { name: /^← Back$/i })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /^Back$/ })).not.toBeInTheDocument()

  fireEvent.change(screen.getByLabelText(/purchase date/i), { target: { value: '2023-01-01' } })
  fireEvent.change(screen.getByLabelText(/sale date/i), { target: { value: '2024-01-01' } })

  expect(screen.getByText(/50% CGT discount may apply/i)).toBeInTheDocument()
})

test('sell form: no CGT discount for holdings < 365 days', async () => {
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: /^sell$/i }))
  expect(screen.getByRole('button', { name: /^← Back$/i })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /^Back$/ })).not.toBeInTheDocument()

  fireEvent.change(screen.getByLabelText(/purchase date/i), { target: { value: '2024-01-01' } })
  fireEvent.change(screen.getByLabelText(/sale date/i), { target: { value: '2024-06-30' } })

  expect(screen.getByText(/No CGT discount/i)).toBeInTheDocument()
})

test('buy form: required validation shows errors on empty submit', async () => {
  const user = userEvent.setup()
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /^buy$/i }))
  await user.click(screen.getByRole('button', { name: /add item/i }))
  const alerts = await screen.findAllByRole('alert')
  expect(alerts.length).toBeGreaterThan(0)
})

test('dividend form renders ← Back and no bare bottom Back', async () => {
  const user = userEvent.setup()
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /^dividend$/i }))
  expect(screen.getByRole('button', { name: /^← Back$/i })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /^Back$/ })).not.toBeInTheDocument()
})

test('buy form submits acquisition category', async () => {
  mockCreate.mockResolvedValue({ data: { data: { items: [], count: 0 } } })
  const user = userEvent.setup()
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /^buy$/i }))

  await user.type(screen.getByLabelText(/platform \/ broker/i), 'CommSec')
  await user.type(screen.getByLabelText(/stock code/i), 'CBA')
  await user.selectOptions(screen.getByLabelText(/^exchange$/i), 'ASX')
  await user.type(screen.getByLabelText(/number of units/i), '100')
  await user.type(screen.getByLabelText(/price per unit/i), '82.5')
  await user.type(screen.getByLabelText(/brokerage fee/i), '9.95')
  fireEvent.change(screen.getByLabelText(/purchase date/i), { target: { value: '2025-01-10' } })

  await user.click(screen.getByRole('button', { name: /add item/i }))

  await waitFor(() =>
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        event_type: 'investment',
        category: 'shares_acquisition',
      })
    )
  )
})

test('buy form saves and restores draft fields', async () => {
  const user = userEvent.setup()
  const { unmount } = render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /^buy$/i }))

  await user.type(screen.getByLabelText(/platform \/ broker/i), 'CommSec')

  await waitFor(() => {
    expect(screen.getByText(/draft saved/i)).toBeInTheDocument()
    expect(sessionStorage.getItem(buyDraftKey)).toContain('CommSec')
  })

  unmount()
  render(<SharesForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /^buy$/i }))

  expect(screen.getByText(/draft found/i)).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: /restore draft/i }))
  expect(screen.getByLabelText(/platform \/ broker/i)).toHaveValue('CommSec')
})
