import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CryptoForm from '@/components/review/investment/CryptoForm'
import * as eventsApi from '@/lib/api/events'

jest.mock('@/lib/api/events')
const mockCreate = eventsApi.createManualEvent as jest.Mock
beforeEach(() => jest.clearAllMocks())

test('shows Buy / Sell / Staking sub-type selector by default', () => {
  render(<CryptoForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  expect(screen.getByRole('button', { name: /^← Back$/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^buy$/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^sell$/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /staking/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument()
})

test('sell form: estimated gain/loss auto-calculates', async () => {
  const user = userEvent.setup()
  render(<CryptoForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /^sell$/i }))
  expect(screen.getByRole('button', { name: /^← Back$/i })).toBeInTheDocument()

  await user.type(screen.getByLabelText(/sale price \(AUD\)/i), '1000')
  await user.type(screen.getByLabelText(/transaction fee/i), '10')
  await user.type(screen.getByLabelText(/purchase price \(AUD\)/i), '800')

  // (1000 - 10) - 800 = 190
  await waitFor(() => expect(screen.getByText('$190.00')).toBeInTheDocument())
})

test('buy form renders top-left ← Back and no bare bottom Back', async () => {
  const user = userEvent.setup()
  render(<CryptoForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /^buy$/i }))
  expect(screen.getByRole('button', { name: /^← Back$/i })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /^Back$/ })).not.toBeInTheDocument()
})

test('staking form: submits with review_status = needs_agent_review', async () => {
  mockCreate.mockResolvedValue({ data: { data: { items: [], count: 0 } } })
  const user = userEvent.setup()
  render(<CryptoForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
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
  render(<CryptoForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /staking/i }))
  await user.click(screen.getByRole('button', { name: /add item/i }))
  const alerts = await screen.findAllByRole('alert')
  expect(alerts.length).toBeGreaterThan(0)
})
