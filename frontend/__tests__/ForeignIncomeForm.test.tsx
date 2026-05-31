import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ForeignIncomeForm from '@/components/review/investment/ForeignIncomeForm'
import * as eventsApi from '@/lib/api/events'

jest.mock('@/lib/api/events')
const mockCreate = eventsApi.createManualEvent as jest.Mock
beforeEach(() => jest.clearAllMocks())

test('AUD amount auto-calculates from foreign amount × exchange rate', async () => {
  const user = userEvent.setup()
  render(<ForeignIncomeForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  await user.type(screen.getByLabelText(/amount \(foreign currency\)/i), '1000')
  await user.type(screen.getByLabelText(/exchange rate/i), '0.65')

  await waitFor(() => expect(screen.getByText('$650.00')).toBeInTheDocument())
})

test('always submits with review_status = needs_agent_review', async () => {
  mockCreate.mockResolvedValue({ data: { data: { items: [], count: 0 } } })
  const user = userEvent.setup()
  render(<ForeignIncomeForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)

  await user.type(screen.getByLabelText(/country of origin/i), 'United States')
  await user.selectOptions(screen.getByLabelText(/income type/i), 'Dividends')
  await user.type(screen.getByLabelText(/amount \(foreign currency\)/i), '1000')
  await user.type(screen.getByLabelText(/currency/i), 'USD')
  await user.type(screen.getByLabelText(/exchange rate/i), '0.65')
  fireEvent.change(screen.getByLabelText(/income date/i), { target: { value: '2024-12-01' } })
  await user.type(screen.getByLabelText(/fx source/i), 'ATO annual average')
  await user.type(screen.getByLabelText(/source document reference/i), 'Broker-Statement-2024-12')

  await user.click(screen.getByRole('button', { name: /add item/i }))

  await waitFor(() => {
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        review_status: 'needs_agent_review',
        metadata: expect.objectContaining({
          schema_version: '2026.1',
          fx_source: 'ATO annual average',
          source_document_reference: 'Broker-Statement-2024-12',
        }),
      })
    )
  })
})

test('required validation shows errors on empty submit', async () => {
  const user = userEvent.setup()
  render(<ForeignIncomeForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /add item/i }))
  const alerts = await screen.findAllByRole('alert')
  expect(alerts.length).toBeGreaterThan(0)
})

test('renders audit fields for fx source and source document reference', () => {
  render(<ForeignIncomeForm onSuccess={jest.fn()} onBack={jest.fn()} onCancel={jest.fn()} />)
  expect(screen.getByLabelText(/fx source/i)).toBeInTheDocument()
  expect(screen.getByLabelText(/source document reference/i)).toBeInTheDocument()
})
