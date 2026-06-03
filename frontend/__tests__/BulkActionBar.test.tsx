import { render, screen, fireEvent, within } from '@testing-library/react'
import BulkActionBar from '@/components/review/BulkActionBar'

const mockOnBulkConfirm = jest.fn()

beforeEach(() => jest.clearAllMocks())

describe('BulkActionBar', () => {
  it('renders nothing when itemIds has fewer than 2 items', () => {
    const { container } = render(
      <BulkActionBar
        items={[{ id: 'item-1', title: 'Spotify subscription' }]}
        groupLabel="Spotify subscription"
        onBulkConfirm={mockOnBulkConfirm}
      />
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders when itemIds has 2 or more items', () => {
    render(
      <BulkActionBar
        items={[
          { id: 'item-1', title: 'Spotify subscription' },
          { id: 'item-2', title: 'Spotify subscription' },
          { id: 'item-3', title: 'Spotify subscription' },
        ]}
        groupLabel="Spotify subscription"
        onBulkConfirm={mockOnBulkConfirm}
      />
    )
    expect(screen.getByText(/3 items/i)).toBeInTheDocument()
    expect(screen.getByText(/spotify subscription/i)).toBeInTheDocument()
  })

  it('opens confirmation dialog before confirming all items', () => {
    render(
      <BulkActionBar
        items={[
          { id: 'item-1', title: 'Spotify subscription', amount: 12.99, date: '2026-05-01' },
          { id: 'item-2', title: 'Spotify subscription', amount: 12.99, date: '2026-05-15' },
        ]}
        groupLabel="Spotify subscription"
        onBulkConfirm={mockOnBulkConfirm}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /confirm all/i }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText(/you're about to confirm 2 review items/i)).toBeInTheDocument()
    expect(mockOnBulkConfirm).not.toHaveBeenCalled()
  })

  it('cancel closes confirmation dialog without confirming', () => {
    render(
      <BulkActionBar
        items={[
          { id: 'item-1', title: 'Spotify subscription' },
          { id: 'item-2', title: 'Spotify subscription' },
        ]}
        groupLabel="Spotify subscription"
        onBulkConfirm={mockOnBulkConfirm}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /confirm all/i }))
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(mockOnBulkConfirm).not.toHaveBeenCalled()
  })

  it('confirm triggers existing bulk action with all item IDs', () => {
    render(
      <BulkActionBar
        items={[
          { id: 'item-1', title: 'Spotify subscription' },
          { id: 'item-2', title: 'Spotify subscription' },
        ]}
        groupLabel="Spotify subscription"
        onBulkConfirm={mockOnBulkConfirm}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /confirm all/i }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /^confirm all$/i }))
    expect(mockOnBulkConfirm).toHaveBeenCalledWith(['item-1', 'item-2'])
  })

  it('shows item count in the label', () => {
    render(
      <BulkActionBar
        items={[
          { id: 'item-1', title: 'Weekly groceries' },
          { id: 'item-2', title: 'Weekly groceries' },
          { id: 'item-3', title: 'Weekly groceries' },
          { id: 'item-4', title: 'Weekly groceries' },
        ]}
        groupLabel="Weekly groceries"
        onBulkConfirm={mockOnBulkConfirm}
      />
    )
    expect(screen.getByText(/4 items/i)).toBeInTheDocument()
  })

  it('renders item details and total amount in the confirmation dialog', () => {
    render(
      <BulkActionBar
        items={[
          { id: 'item-1', title: 'Work laptop', amount: 1200, date: '2026-05-01' },
          { id: 'item-2', title: 'Work monitor', amount: 400, date: '2026-05-02' },
        ]}
        groupLabel="Work equipment"
        onBulkConfirm={mockOnBulkConfirm}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /confirm all/i }))

    expect(screen.getByText(/work laptop/i)).toBeInTheDocument()
    expect(screen.getByText(/work monitor/i)).toBeInTheDocument()
    expect(screen.getByText(/\$1,200\.00/)).toBeInTheDocument()
    expect(screen.getByText(/\$400\.00/)).toBeInTheDocument()
    expect(screen.getByText(/1 May 2026/i)).toBeInTheDocument()
    expect(screen.getByText(/2 May 2026/i)).toBeInTheDocument()
    expect(screen.getByText(/total amount/i)).toHaveTextContent('$1,600.00')
  })
})
