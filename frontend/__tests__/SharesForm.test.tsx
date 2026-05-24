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

  await waitFor(() => expect(screen.getByText('$8259.95')).toBeInTheDocument())
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
