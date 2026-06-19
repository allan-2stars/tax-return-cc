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
  decision_history: [],
  source: null,
  event_metadata: null,
  source_document: null,
  explanation: {
    explanation_id: 'review_item:item-1',
    target_type: 'review_item',
    target_id: 'item-1',
    category: 'deduction',
    plain_english_summary: 'This work item was captured for review.',
    why_it_matters: 'It can affect deduction totals.',
    what_user_should_check: 'Confirm amount, date, and category.',
    evidence_expected: ['receipt', 'invoice'],
    confidence_level: 'medium',
    rule_version: null,
    source: 'review',
  },
}

const extractedShareBuyItem: ReviewItem = {
  ...baseItem,
  id: 'item-extracted-buy',
  tax_event_id: 'evt-extracted-buy',
  title: 'BHP contract note',
  category: 'shares_acquisition',
  source: 'document_extracted',
  confidence: 0.92,
  source_document: {
    document_id: 'doc-1',
    original_filename: 'BHP_Contract_Note.pdf',
  },
  event_metadata: {
    stock_code: 'BHP',
    exchange: 'ASX',
    units: 100,
    price_per_unit: 52.10,
    brokerage_fee: 19.95,
    transaction_type: 'buy',
  },
}

const mockOnAction = jest.fn()
const mockOnInlineAnswer = jest.fn().mockResolvedValue({ new_skill_pending: false })
const mockOnUndo = jest.fn()
const mockOnUndoBulk = jest.fn()

beforeEach(() => jest.clearAllMocks())

describe('ReviewCard', () => {
  it('renders title and amount in font-mono', () => {
    render(<ReviewCard item={baseItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />)
    expect(screen.getByText('Work laptop purchase')).toBeInTheDocument()
    const amountEl = screen.getByText('$1,299.00')
    expect(amountEl).toHaveClass('font-mono')
  })

  it('renders Document Extracted badge and source document details for extracted items', () => {
    render(<ReviewCard item={extractedShareBuyItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />)
    expect(screen.getByText('Document Extracted')).toBeInTheDocument()
    expect(screen.getByText(/source document:/i)).toBeInTheDocument()
    expect(screen.getByText('BHP_Contract_Note.pdf')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view source document/i })).toHaveAttribute('href', '/api/v1/documents/doc-1/file')
  })

  it('does not show extracted badge for manual entries', () => {
    render(
      <ReviewCard
        item={{ ...baseItem, source: 'manual_entry' }}
        onAction={mockOnAction}
        onInlineAnswer={mockOnInlineAnswer}
      />
    )
    expect(screen.queryByText('Document Extracted')).not.toBeInTheDocument()
  })

  it('renders share acquisition extraction preview', () => {
    render(<ReviewCard item={extractedShareBuyItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />)
    expect(screen.getByText('BHP')).toBeInTheDocument()
    expect(screen.getByText('ASX')).toBeInTheDocument()
    expect(screen.getByText('100 units')).toBeInTheDocument()
    expect(screen.getByText('$52.10 each')).toBeInTheDocument()
    expect(screen.getByText('Brokerage $19.95')).toBeInTheDocument()
  })

  it('renders share disposal extraction preview', () => {
    render(
      <ReviewCard
        item={{
          ...extractedShareBuyItem,
          id: 'item-sell',
          category: 'capital_gain_candidate',
          event_metadata: {
            stock_code: 'BHP',
            units: 100,
            price_per_unit: 58.2,
            brokerage_fee: 19.95,
            transaction_type: 'sell',
          },
        }}
        onAction={mockOnAction}
        onInlineAnswer={mockOnInlineAnswer}
      />
    )
    expect(screen.getByText('100 units sold')).toBeInTheDocument()
    expect(screen.getByText('$58.20 each')).toBeInTheDocument()
  })

  it('renders dividend extraction preview', () => {
    render(
      <ReviewCard
        item={{
          ...extractedShareBuyItem,
          id: 'item-dividend',
          category: 'dividend',
          event_metadata: {
            dividend_amount: 145.2,
            franking_credits: 62.23,
            payment_date: '2025-09-15',
          },
        }}
        onAction={mockOnAction}
        onInlineAnswer={mockOnInlineAnswer}
      />
    )
    expect(screen.getByText('Dividend $145.20')).toBeInTheDocument()
    expect(screen.getByText('Franking $62.23')).toBeInTheDocument()
    expect(screen.getByText((text) => /^Payment 15 Sep[t]? 2025$/.test(text))).toBeInTheDocument()
  })

  it('renders managed fund extraction preview', () => {
    render(
      <ReviewCard
        item={{
          ...extractedShareBuyItem,
          id: 'item-managed',
          category: 'managed_fund_distribution',
          event_metadata: {
            distribution_amount: 1245.8,
            capital_gains_component: 215.4,
            foreign_income_component: 37.2,
          },
        }}
        onAction={mockOnAction}
        onInlineAnswer={mockOnInlineAnswer}
      />
    )
    expect(screen.getByText('Distribution $1,245.80')).toBeInTheDocument()
    expect(screen.getByText('Capital gains component $215.40')).toBeInTheDocument()
    expect(screen.getByText('Foreign income component $37.20')).toBeInTheDocument()
  })

  it('renders broker annual summary extraction preview', () => {
    render(
      <ReviewCard
        item={{
          ...extractedShareBuyItem,
          id: 'item-summary',
          category: 'share_annual_summary',
          event_metadata: {
            total_purchase_value: 12400,
            total_sale_value: 8700,
            total_dividend_income: 640,
            total_brokerage_fees: 95,
          },
        }}
        onAction={mockOnAction}
        onInlineAnswer={mockOnInlineAnswer}
      />
    )
    expect(screen.getByText('Purchases $12,400.00')).toBeInTheDocument()
    expect(screen.getByText('Sales $8,700.00')).toBeInTheDocument()
    expect(screen.getByText('Dividends $640.00')).toBeInTheDocument()
    expect(screen.getByText('Brokerage $95.00')).toBeInTheDocument()
  })

  it('renders extracted confidence indicator and auditability hint when confidence exists', () => {
    render(<ReviewCard item={extractedShareBuyItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />)
    expect(screen.getByText('Extraction confidence: High')).toBeInTheDocument()
    expect(screen.getByText(/review extracted information and correct any fields that appear inaccurate/i)).toBeInTheDocument()
  })

  it('hides extracted confidence indicator when confidence is unavailable', () => {
    render(
      <ReviewCard
        item={{ ...extractedShareBuyItem, confidence: null }}
        onAction={mockOnAction}
        onInlineAnswer={mockOnInlineAnswer}
      />
    )
    expect(screen.queryByText(/extraction confidence:/i)).not.toBeInTheDocument()
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

  it('renders explanation summary and expandable details', () => {
    render(<ReviewCard item={baseItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />)
    expect(screen.getByText(/this work item was captured for review/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /why this matters/i }))
    expect(screen.getByTestId('review-explanation-details')).toBeInTheDocument()
    expect(screen.getByText(/what to check:/i)).toBeInTheDocument()
    expect(screen.getByText(/expected evidence:/i)).toBeInTheDocument()
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

  it('renders review history empty state', () => {
    render(<ReviewCard item={baseItem} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />)
    fireEvent.click(screen.getByRole('button', { name: /review history/i }))
    expect(screen.getByText(/no review history yet/i)).toBeInTheDocument()
  })

  it('renders review history changed fields', () => {
    render(
      <ReviewCard
        item={{
          ...baseItem,
          decision_history: [
            {
              id: 'hist-1',
              workspace_id: 'ws-1',
              review_item_id: 'item-1',
              tax_event_id: 'evt-1',
              action: 'amended',
              actor: 'user',
              previous_status: 'needs_user_review',
              new_status: 'confirmed',
              changed_fields: {
                amount: { old: 1299, new: 1199 },
                category: { old: 'work_equipment', new: 'work_expense' },
              },
              note: 'Corrected after checking receipt',
              bulk_action_id: null,
              created_at: '2026-06-03T10:00:00+00:00',
            },
          ],
        }}
        onAction={mockOnAction}
        onInlineAnswer={mockOnInlineAnswer}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /review history/i }))

    expect(screen.getByText(/amended/i)).toBeInTheDocument()
    expect(screen.getByText(/amount:/i)).toHaveTextContent('1299')
    expect(screen.getByText(/category:/i)).toHaveTextContent('work_equipment')
    expect(screen.getByText(/corrected after checking receipt/i)).toBeInTheDocument()
  })

  it('renders bulk action marker in review history', () => {
    render(
      <ReviewCard
        item={{
          ...baseItem,
          decision_history: [
            {
              id: 'hist-1',
              workspace_id: 'ws-1',
              review_item_id: 'item-1',
              tax_event_id: 'evt-1',
              action: 'confirmed',
              actor: 'user',
              previous_status: 'needs_user_review',
              new_status: 'confirmed',
              changed_fields: {
                status: { old: 'needs_user_review', new: 'confirmed' },
              },
              note: null,
              bulk_action_id: 'bulk-1',
              created_at: '2026-06-03T10:00:00+00:00',
            },
          ],
        }}
        onAction={mockOnAction}
        onInlineAnswer={mockOnInlineAnswer}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /review history/i }))
    expect(screen.getByText(/bulk action/i)).toBeInTheDocument()
  })

  it('renders Undo last decision for undoable latest history and calls onUndo', () => {
    render(
      <ReviewCard
        item={{
          ...baseItem,
          status: 'confirmed',
          decision_history: [
            {
              id: 'hist-1',
              workspace_id: 'ws-1',
              review_item_id: 'item-1',
              tax_event_id: 'evt-1',
              action: 'confirmed',
              actor: 'user',
              previous_status: 'needs_user_review',
              new_status: 'confirmed',
              changed_fields: {
                status: { old: 'needs_user_review', new: 'confirmed' },
              },
              note: null,
              bulk_action_id: null,
              created_at: '2026-06-03T10:00:00+00:00',
            },
          ],
        }}
        onAction={mockOnAction}
        onInlineAnswer={mockOnInlineAnswer}
        onUndo={mockOnUndo}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /review history/i }))
    fireEvent.click(screen.getByRole('button', { name: /undo last decision/i }))
    expect(mockOnUndo).toHaveBeenCalledWith('item-1')
  })

  it('uses bulk undo callback when latest history has bulk action id', () => {
    render(
      <ReviewCard
        item={{
          ...baseItem,
          status: 'confirmed',
          decision_history: [
            {
              id: 'hist-1',
              workspace_id: 'ws-1',
              review_item_id: 'item-1',
              tax_event_id: 'evt-1',
              action: 'confirmed',
              actor: 'user',
              previous_status: 'needs_user_review',
              new_status: 'confirmed',
              changed_fields: {
                status: { old: 'needs_user_review', new: 'confirmed' },
              },
              note: null,
              bulk_action_id: 'bulk-1',
              created_at: '2026-06-03T10:00:00+00:00',
            },
          ],
        }}
        onAction={mockOnAction}
        onInlineAnswer={mockOnInlineAnswer}
        onUndo={mockOnUndo}
        onUndoBulk={mockOnUndoBulk}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /review history/i }))
    fireEvent.click(screen.getByRole('button', { name: /undo last decision/i }))
    expect(mockOnUndoBulk).toHaveBeenCalledWith('bulk-1')
    expect(mockOnUndo).not.toHaveBeenCalled()
  })
})
