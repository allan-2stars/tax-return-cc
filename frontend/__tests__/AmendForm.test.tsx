import { render, screen, fireEvent } from '@testing-library/react'
import AmendForm from '@/components/review/AmendForm'
import type { ReviewItem } from '@/lib/api/types'

const baseItem: ReviewItem = {
  id: 'item-1',
  workspace_id: 'ws-1',
  tax_event_id: 'evt-1',
  title: 'Work laptop',
  category: 'work_equipment',
  amount: 1299.00,
  date: '2025-09-15',
  skill_id: 'employee_tax_au',
  risk_level: 'low',
  ai_reasoning: null,
  confidence: null,
  inline_questions: [],
  questions_complete: true,
  status: 'needs_user_review',
  user_action: null,
  user_note: null,
  amended_amount: null,
  amended_category: null,
  skipped_until: null,
  created_at: '2026-05-01T10:00:00+00:00',
  reviewed_at: null,
  review_duration_seconds: null,
  group_id: null,
  group_display: null,
  source: null,
  event_metadata: null,
  source_document: null,
}

const mockOnSave = jest.fn()
const mockOnCancel = jest.fn()

beforeEach(() => jest.clearAllMocks())

describe('AmendForm', () => {
  it('renders with pre-filled amount from item', () => {
    render(<AmendForm item={baseItem} onSave={mockOnSave} onCancel={mockOnCancel} />)
    const amountInput = screen.getByLabelText(/amount/i)
    expect(amountInput).toHaveValue(1299)
  })

  it('renders category dropdown pre-selected to item category', () => {
    render(<AmendForm item={baseItem} onSave={mockOnSave} onCancel={mockOnCancel} />)
    const select = screen.getByLabelText(/category/i)
    expect(select).toHaveValue('work_equipment')
  })

  it('category dropdown only shows categories for the item skill_id', () => {
    render(<AmendForm item={baseItem} onSave={mockOnSave} onCancel={mockOnCancel} />)
    const select = screen.getByLabelText(/category/i)
    const options = Array.from(select.querySelectorAll('option')).map((o) => o.getAttribute('value'))
    expect(options).toContain('work_equipment')
    expect(options).toContain('work_expense')
    expect(options).toContain('payg_income')
  })

  it('Save button calls onSave with updated amount, category, note', () => {
    render(<AmendForm item={baseItem} onSave={mockOnSave} onCancel={mockOnCancel} />)
    fireEvent.change(screen.getByLabelText(/amount/i), { target: { value: '999' } })
    fireEvent.change(screen.getByLabelText(/category/i), { target: { value: 'work_expense' } })
    fireEvent.change(screen.getByLabelText(/note/i), { target: { value: 'Only 50% work use' } })
    fireEvent.click(screen.getByRole('button', { name: /save/i }))
    expect(mockOnSave).toHaveBeenCalledWith(999, 'work_expense', 'Only 50% work use')
  })

  it('Cancel button calls onCancel', () => {
    render(<AmendForm item={baseItem} onSave={mockOnSave} onCancel={mockOnCancel} />)
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(mockOnCancel).toHaveBeenCalledTimes(1)
  })

  it('shows all categories when skill_id is unknown', () => {
    render(
      <AmendForm
        item={{ ...baseItem, skill_id: 'unknown_skill' }}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )
    const select = screen.getByLabelText(/category/i)
    expect(select.querySelectorAll('option').length).toBeGreaterThan(0)
  })

  it('shows document extraction source context when editing extracted items', () => {
    render(
      <AmendForm
        item={{ ...baseItem, source: 'document_extracted' }}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    )
    expect(
      screen.getByText((_, element) => element?.textContent?.replace(/\s+/g, ' ').trim() === 'Source: Document Extraction')
    ).toBeInTheDocument()
  })
})
