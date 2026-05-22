import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ReviewCard from '@/components/review/ReviewCard'
import type { ReviewItem } from '@/lib/api/types'

const baseItem: ReviewItem = {
  id: 'item-1',
  workspace_id: 'ws-1',
  tax_event_id: 'evt-1',
  title: 'Work laptop purchase',
  category: 'work_equipment',
  amount: 1299.00,
  date: '2025-09-15',
  skill_id: 'employee_tax_au',
  risk_level: 'low',
  ai_reasoning: 'This looks like a work-related equipment purchase.',
  confidence: 0.85,
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
}

const mockOnAction = jest.fn()
const mockOnInlineAnswer = jest.fn().mockResolvedValue({ new_skill_pending: false })

beforeEach(() => jest.clearAllMocks())

describe('ReviewCard', () => {
  it('renders title and amount in font-mono', () => {
    render(<ReviewCard item={baseItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />)
    expect(screen.getByText('Work laptop purchase')).toBeInTheDocument()
    const amountEl = screen.getByText('$1,299.00')
    expect(amountEl).toHaveClass('font-mono')
  })

  it('renders AI reasoning in italic', () => {
    render(<ReviewCard item={baseItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />)
    const reasoning = screen.getByText('This looks like a work-related equipment purchase.')
    expect(reasoning).toHaveClass('italic')
  })

  it('applies border-review class for needs_user_review status', () => {
    const { container } = render(
      <ReviewCard item={baseItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />
    )
    expect(container.firstChild).toHaveClass('border-review')
  })

  it('applies border-risk-high for high risk_level regardless of status', () => {
    const highRisk = { ...baseItem, risk_level: 'high' }
    const { container } = render(
      <ReviewCard item={highRisk} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />
    )
    expect(container.firstChild).toHaveClass('border-risk-high')
  })

  it('applies border-ready for confirmed status', () => {
    const confirmed = { ...baseItem, status: 'confirmed' }
    const { container } = render(
      <ReviewCard item={confirmed} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />
    )
    expect(container.firstChild).toHaveClass('border-ready')
  })

  it('action buttons are locked when questions_complete is false', () => {
    const withQuestions: ReviewItem = {
      ...baseItem,
      questions_complete: false,
      inline_questions: [{ id: 'q1', ask: 'Was this 100% for work?', type: 'single_choice', options: ['yes', 'no'] }],
    }
    const { container } = render(
      <ReviewCard item={withQuestions} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />
    )
    const actionArea = container.querySelector('[data-testid="action-buttons"]')
    expect(actionArea).toHaveClass('pointer-events-none')
    expect(actionArea).toHaveClass('opacity-50')
  })

  it('"Looks right" button calls onAction with confirmed and shows inline confirmation text', async () => {
    render(<ReviewCard item={baseItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />)
    fireEvent.click(screen.getByRole('button', { name: /looks right/i }))
    expect(mockOnAction).toHaveBeenCalledWith('item-1', 'confirmed', {})
    await waitFor(() =>
      expect(screen.getByText(/thanks for reviewing/i)).toBeInTheDocument()
    )
    expect(screen.queryByRole('button', { name: /looks right/i })).not.toBeInTheDocument()
  })

  it('"Change this" button toggles AmendForm', () => {
    render(<ReviewCard item={baseItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />)
    expect(screen.queryByTestId('amend-form')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /change this/i }))
    expect(screen.getByTestId('amend-form')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /change this/i }))
    expect(screen.queryByTestId('amend-form')).not.toBeInTheDocument()
  })

  it('"Why did Claude suggest this?" toggle reveals reasoning section', () => {
    render(<ReviewCard item={baseItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />)
    expect(screen.queryByTestId('why-section')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /why did claude/i }))
    expect(screen.getByTestId('why-section')).toBeInTheDocument()
  })

  it('shows new skill banner when onInlineAnswer returns new_skill_pending=true', async () => {
    const withQuestion: ReviewItem = {
      ...baseItem,
      questions_complete: false,
      inline_questions: [{ id: 'q1', ask: 'Work use?', type: 'single_choice', options: ['yes', 'no'] }],
    }
    const mockAnswer = jest.fn().mockResolvedValue({ new_skill_pending: true })
    render(<ReviewCard item={withQuestion} onAction={mockOnAction} onInlineAnswer={mockAnswer} />)
    fireEvent.click(screen.getByRole('button', { name: 'yes' }))
    await waitFor(() =>
      expect(screen.getByText(/new tax area unlocked/i)).toBeInTheDocument()
    )
  })

  it('shows formatted date in en-AU locale', () => {
    render(<ReviewCard item={baseItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />)
    // Node 18+ ICU data renders "Sept" for September in en-AU; accept either abbreviation
    expect(
      screen.getByText((text) => /^15 Sep[t]? 2025$/.test(text))
    ).toBeInTheDocument()
  })

  it('shows em-dash when date is null', () => {
    render(
      <ReviewCard item={{ ...baseItem, date: null }} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />
    )
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})
