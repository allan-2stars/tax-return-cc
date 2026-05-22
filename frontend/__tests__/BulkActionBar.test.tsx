import { render, screen, fireEvent } from '@testing-library/react'
import BulkActionBar from '@/components/review/BulkActionBar'

const mockOnBulkConfirm = jest.fn()

beforeEach(() => jest.clearAllMocks())

describe('BulkActionBar', () => {
  it('renders nothing when itemIds has fewer than 2 items', () => {
    const { container } = render(
      <BulkActionBar
        itemIds={['item-1']}
        groupLabel="Spotify subscription"
        onBulkConfirm={mockOnBulkConfirm}
      />
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders when itemIds has 2 or more items', () => {
    render(
      <BulkActionBar
        itemIds={['item-1', 'item-2', 'item-3']}
        groupLabel="Spotify subscription"
        onBulkConfirm={mockOnBulkConfirm}
      />
    )
    expect(screen.getByText(/3 items/i)).toBeInTheDocument()
    expect(screen.getByText(/spotify subscription/i)).toBeInTheDocument()
  })

  it('calls onBulkConfirm with all item IDs on "Confirm all" click', () => {
    render(
      <BulkActionBar
        itemIds={['item-1', 'item-2']}
        groupLabel="Spotify subscription"
        onBulkConfirm={mockOnBulkConfirm}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /confirm all/i }))
    expect(mockOnBulkConfirm).toHaveBeenCalledWith(['item-1', 'item-2'])
  })

  it('shows item count in the label', () => {
    render(
      <BulkActionBar
        itemIds={['item-1', 'item-2', 'item-3', 'item-4']}
        groupLabel="Weekly groceries"
        onBulkConfirm={mockOnBulkConfirm}
      />
    )
    expect(screen.getByText(/4 items/i)).toBeInTheDocument()
  })
})
