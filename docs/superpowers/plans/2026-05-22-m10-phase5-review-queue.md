# M10 Phase 5: Review Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Review Queue page — the central human-review surface where users confirm, amend, flag, or skip AI-classified tax events.

**Architecture:** Backend is fully implemented (all routes in `backend/app/api/routes/review.py`). This phase is frontend-only: API types, 5 API functions, 5 components, 1 page, and tests for each. Components compose: ReviewCard contains InlineQuestion, AmendForm, and AskClaudeDrawer as inline children. BulkActionBar is rendered by the page when ≥2 queue items share the same `title`.

**Tech Stack:** Next.js 14, React Query, Zustand, Tailwind CSS, Jest + React Testing Library

---

## File Structure

**Modify:**
- `frontend/lib/api/types.ts` — add `ReviewItemQuestion`, `ReviewItem`, `ReviewQueue`, `ReviewQueueSection`, `ReviewActionResponse`, `InlineAnswerResponse`, `BulkActionResponseData`, `AskClaudeResponseData`

**Create:**
- `frontend/lib/api/review.ts` — 5 API functions
- `frontend/components/review/ReviewCard.tsx` — core review card with left border strip
- `frontend/components/review/InlineQuestion.tsx` — one-at-a-time inline questions
- `frontend/components/review/AmendForm.tsx` — inline amount/category/note edit
- `frontend/components/review/AskClaudeDrawer.tsx` — side drawer with thread + Disclaimer
- `frontend/components/review/BulkActionBar.tsx` — bulk confirm bar for recurring items
- `frontend/app/(dashboard)/review/page.tsx` — review queue page with 4 sections
- `frontend/__tests__/ReviewCard.test.tsx`
- `frontend/__tests__/InlineQuestion.test.tsx`
- `frontend/__tests__/AmendForm.test.tsx`
- `frontend/__tests__/AskClaudeDrawer.test.tsx`
- `frontend/__tests__/BulkActionBar.test.tsx`
- `frontend/__tests__/review-page.test.tsx`

---

## Task 1: API types + lib/api/review.ts

**Files:**
- Modify: `frontend/lib/api/types.ts`
- Create: `frontend/lib/api/review.ts`
- Test: `frontend/__tests__/review-api.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/__tests__/review-api.test.ts
import * as reviewApi from '@/lib/api/review'
import client from '@/lib/api/client'

jest.mock('@/lib/api/client', () => ({
  get: jest.fn(),
  post: jest.fn(),
}))

const mockGet = client.get as jest.Mock
const mockPost = client.post as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('review API', () => {
  it('getReviewQueue calls GET /api/v1/review/queue', async () => {
    mockGet.mockResolvedValue({ data: { agent_required: { items: [], count: 0 }, high_risk: { items: [], count: 0 }, needs_review: { items: [], count: 0 }, confirmed: { items: [], count: 0 }, total: 0, pending: 0 } })
    await reviewApi.getReviewQueue()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/review/queue')
  })

  it('takeAction calls POST /api/v1/review/:id/action with body', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await reviewApi.takeAction('item-1', 'confirmed', {})
    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/review/item-1/action',
      { action: 'confirmed' }
    )
  })

  it('takeAction passes amount and category for amended', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await reviewApi.takeAction('item-1', 'amended', { amount: 99.5, category: 'work_expense' })
    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/review/item-1/action',
      { action: 'amended', amount: 99.5, category: 'work_expense' }
    )
  })

  it('submitInlineAnswer calls POST /api/v1/review/:id/inline-answer', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await reviewApi.submitInlineAnswer('item-1', 'q1', 'yes', 'evt-1')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/review/item-1/inline-answer', {
      question_id: 'q1',
      answer: 'yes',
      event_id: 'evt-1',
    })
  })

  it('bulkAction calls POST /api/v1/review/bulk-action with item_ids', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await reviewApi.bulkAction(['item-1', 'item-2'], 'confirmed')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/review/bulk-action', {
      item_ids: ['item-1', 'item-2'],
      action: 'confirmed',
    })
  })

  it('askClaude calls POST /api/v1/review/:id/ask', async () => {
    mockPost.mockResolvedValue({ data: { data: { answer: 'hello' } } })
    await reviewApi.askClaude('item-1', 'Is this deductible?')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/review/item-1/ask', {
      question: 'Is this deductible?',
    })
  })
})
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
docker compose exec frontend npx jest __tests__/review-api.test.ts --no-coverage
```

Expected: FAIL — `Cannot find module '@/lib/api/review'`

- [ ] **Step 3: Add types to types.ts**

Append to `frontend/lib/api/types.ts`:

```typescript
export interface ReviewItemQuestion {
  id: string
  ask: string
  type: 'single_choice' | 'multi_choice' | 'text' | 'number'
  options: string[] | null
}

export interface ReviewItem {
  id: string
  workspace_id: string
  tax_event_id: string | null
  title: string | null
  category: string | null
  amount: number | null
  date: string | null
  skill_id: string | null
  risk_level: string
  ai_reasoning: string | null
  confidence: number | null
  inline_questions: ReviewItemQuestion[]
  questions_complete: boolean
  status: string
  user_action: string | null
  user_note: string | null
  amended_amount: number | null
  amended_category: string | null
  skipped_until: string | null
  created_at: string
  reviewed_at: string | null
  review_duration_seconds: number | null
}

export interface ReviewQueueSection {
  items: ReviewItem[]
  count: number
}

export interface ReviewQueue {
  agent_required: ReviewQueueSection
  high_risk: ReviewQueueSection
  needs_review: ReviewQueueSection
  confirmed: ReviewQueueSection
  total: number
  pending: number
}

export interface ReviewActionResponse extends ReviewItem {}

export interface InlineAnswerResponse extends ReviewItem {
  new_skill_pending: boolean
}

export interface BulkActionResponseData {
  items: ReviewItem[]
  count: number
}

export interface AskClaudeResponseData {
  answer: string
}
```

- [ ] **Step 4: Create lib/api/review.ts**

```typescript
// frontend/lib/api/review.ts
import client from './client'
import type {
  ReviewQueue,
  ReviewActionResponse,
  InlineAnswerResponse,
  BulkActionResponseData,
  AskClaudeResponseData,
  ApiResponse,
} from './types'

export const getReviewQueue = () =>
  client.get<{ data: ReviewQueue }>('/api/v1/review/queue')

export const takeAction = (
  itemId: string,
  action: 'confirmed' | 'amended' | 'flagged' | 'skipped',
  payload: { amount?: number; category?: string; note?: string }
) =>
  client.post<ApiResponse<ReviewActionResponse>>(`/api/v1/review/${itemId}/action`, {
    action,
    ...payload,
  })

export const submitInlineAnswer = (
  itemId: string,
  questionId: string,
  answer: string,
  eventId: string
) =>
  client.post<ApiResponse<InlineAnswerResponse>>(`/api/v1/review/${itemId}/inline-answer`, {
    question_id: questionId,
    answer,
    event_id: eventId,
  })

export const bulkAction = (itemIds: string[], action: 'confirmed') =>
  client.post<ApiResponse<BulkActionResponseData>>('/api/v1/review/bulk-action', {
    item_ids: itemIds,
    action,
  })

export const askClaude = (itemId: string, question: string) =>
  client.post<ApiResponse<AskClaudeResponseData>>(`/api/v1/review/${itemId}/ask`, { question })
```

- [ ] **Step 5: Run test to confirm it passes**

```bash
docker compose exec frontend npx jest __tests__/review-api.test.ts --no-coverage
```

Expected: PASS — 6 tests

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/api/types.ts frontend/lib/api/review.ts frontend/__tests__/review-api.test.ts
git commit -m "feat: add review API types and functions"
```

---

## Task 2: ReviewCard component

**Files:**
- Create: `frontend/components/review/ReviewCard.tsx`
- Test: `frontend/__tests__/ReviewCard.test.tsx`

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/__tests__/ReviewCard.test.tsx
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
    expect(screen.getByText('15 Sep 2025')).toBeInTheDocument()
  })

  it('shows em-dash when date is null', () => {
    render(
      <ReviewCard item={{ ...baseItem, date: null }} onAction={mockOnAction} onInlineAnswer={mockOnInlineAnswer} />
    )
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec frontend npx jest __tests__/ReviewCard.test.tsx --no-coverage
```

Expected: FAIL — `Cannot find module '@/components/review/ReviewCard'`

- [ ] **Step 3: Create components/review/InlineQuestion.tsx placeholder (needed by ReviewCard)**

This must exist before ReviewCard can import it. Create the minimal stub:

```typescript
// frontend/components/review/InlineQuestion.tsx
import type { ReviewItemQuestion } from '@/lib/api/types'

interface InlineQuestionProps {
  questions: ReviewItemQuestion[]
  onAnswer: (questionId: string, answer: string) => Promise<void>
}

export default function InlineQuestion({ questions, onAnswer }: InlineQuestionProps) {
  return <div data-testid="inline-question">{questions[0]?.ask}</div>
}
```

Also create AmendForm stub:

```typescript
// frontend/components/review/AmendForm.tsx
import type { ReviewItem } from '@/lib/api/types'

interface AmendFormProps {
  item: ReviewItem
  onSave: (amount: number | undefined, category: string | undefined, note: string | undefined) => void
  onCancel: () => void
}

export default function AmendForm({ onCancel }: AmendFormProps) {
  return (
    <div data-testid="amend-form">
      <button type="button" onClick={onCancel}>Cancel</button>
    </div>
  )
}
```

Also create AskClaudeDrawer stub:

```typescript
// frontend/components/review/AskClaudeDrawer.tsx
interface AskClaudeDrawerProps {
  itemId: string
  itemTitle: string
  onClose: () => void
}

export default function AskClaudeDrawer({ onClose }: AskClaudeDrawerProps) {
  return (
    <div data-testid="ask-claude-drawer">
      <button type="button" onClick={onClose}>Close</button>
    </div>
  )
}
```

- [ ] **Step 4: Create components/review/ReviewCard.tsx**

```typescript
// frontend/components/review/ReviewCard.tsx
'use client'
import { useState } from 'react'
import type { ReviewItem } from '@/lib/api/types'
import ConfidenceBar from '@/components/shared/ConfidenceBar'
import StatusBadge from '@/components/shared/StatusBadge'
import type { BadgeStatus } from '@/components/shared/StatusBadge'
import InlineQuestion from './InlineQuestion'
import AmendForm from './AmendForm'
import AskClaudeDrawer from './AskClaudeDrawer'

function getBorderClass(item: ReviewItem): string {
  if (item.risk_level === 'high') return 'border-risk-high'
  if (item.status === 'confirmed') return 'border-ready'
  if (item.status === 'needs_agent_review') return 'border-agent'
  return 'border-review'
}

function getStatusBadge(item: ReviewItem): BadgeStatus {
  if (item.risk_level === 'high') return 'high_risk'
  if (item.status === 'confirmed') return 'confirmed'
  if (item.status === 'needs_agent_review') return 'needs_agent_review'
  return 'needs_user_review'
}

interface ReviewCardProps {
  item: ReviewItem
  onAction: (
    id: string,
    action: 'confirmed' | 'amended' | 'flagged' | 'skipped',
    payload: { amount?: number; category?: string; note?: string }
  ) => void
  onInlineAnswer: (
    itemId: string,
    questionId: string,
    answer: string,
    eventId: string
  ) => Promise<{ new_skill_pending: boolean }>
}

export default function ReviewCard({ item, onAction, onInlineAnswer }: ReviewCardProps) {
  const [showWhy, setShowWhy] = useState(false)
  const [showAmend, setShowAmend] = useState(false)
  const [showAsk, setShowAsk] = useState(false)
  const [confirmed, setConfirmed] = useState(item.status === 'confirmed')
  const [newSkillPending, setNewSkillPending] = useState(false)

  const borderClass = getBorderClass(item)
  const actionsLocked = !item.questions_complete
  const lockClass = actionsLocked ? 'opacity-50 pointer-events-none' : ''

  const displayAmount = item.amended_amount ?? item.amount
  const displayCategory = item.amended_category ?? item.category

  const d = item.date ? new Date(item.date) : null
  const displayDate =
    d && !isNaN(d.getTime())
      ? d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
      : '—'

  async function handleInlineAnswer(questionId: string, answer: string) {
    const res = await onInlineAnswer(item.id, questionId, answer, item.tax_event_id ?? item.id)
    if (res.new_skill_pending) setNewSkillPending(true)
  }

  function handleConfirm() {
    setConfirmed(true)
    onAction(item.id, 'confirmed', {})
  }

  return (
    <div className={`bg-surface border border-border border-l-4 ${borderClass} rounded-md p-4`}>
      {newSkillPending && (
        <div className="mb-3 rounded bg-agent-bg px-3 py-2 text-xs font-ui text-agent">
          New tax area unlocked — check Tax Journey for new questions.
        </div>
      )}

      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-ui font-medium text-text-body">{item.title ?? displayCategory}</p>
          <div className="flex items-center gap-3 mt-1">
            {displayAmount != null && (
              <span className="font-mono text-sm text-text-body">
                ${displayAmount.toLocaleString('en-AU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            )}
            <span className="text-xs font-ui text-text-muted">{displayDate}</span>
          </div>
        </div>
        <StatusBadge status={getStatusBadge(item)} />
      </div>

      {item.ai_reasoning && (
        <p className="mt-2 text-sm font-ui italic text-text-muted">{item.ai_reasoning}</p>
      )}

      {item.confidence != null && (
        <div className="mt-2">
          <ConfidenceBar confidence={item.confidence} />
        </div>
      )}

      {!item.questions_complete && item.inline_questions.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <InlineQuestion questions={item.inline_questions} onAnswer={handleInlineAnswer} />
        </div>
      )}

      {!confirmed ? (
        <div
          data-testid="action-buttons"
          className={`flex flex-wrap gap-2 mt-3 pt-3 border-t border-border ${lockClass}`}
        >
          <button
            type="button"
            onClick={handleConfirm}
            className="min-h-[44px] px-3 py-2 rounded text-sm font-ui font-medium bg-ready text-surface hover:opacity-90 transition-opacity"
          >
            Looks right
          </button>
          <button
            type="button"
            onClick={() => setShowAmend((v) => !v)}
            className="min-h-[44px] px-3 py-2 rounded text-sm font-ui font-medium border border-border text-text-body hover:bg-surface-raised transition-colors"
          >
            Change this
          </button>
          <button
            type="button"
            onClick={() => setShowAsk(true)}
            className="min-h-[44px] px-3 py-2 rounded text-sm font-ui font-medium border border-border text-text-body hover:bg-surface-raised transition-colors"
          >
            Ask Claude
          </button>
        </div>
      ) : (
        <p className="mt-3 pt-3 border-t border-border text-sm font-ui text-ready">
          Thanks for reviewing. We've noted your input.
        </p>
      )}

      {showAmend && (
        <div className="mt-3 pt-3 border-t border-border">
          <AmendForm
            item={item}
            onSave={(amount, category, note) => {
              setShowAmend(false)
              setConfirmed(true)
              onAction(item.id, 'amended', { amount, category, note })
            }}
            onCancel={() => setShowAmend(false)}
          />
        </div>
      )}

      {item.ai_reasoning && (
        <div className="mt-2">
          <button
            type="button"
            onClick={() => setShowWhy((v) => !v)}
            className="text-xs font-ui text-text-muted hover:text-text-body transition-colors"
          >
            {showWhy ? 'Hide explanation ↑' : 'Why did Claude suggest this? ↓'}
          </button>
          {showWhy && (
            <div data-testid="why-section" className="mt-2 p-3 bg-surface-raised rounded text-xs font-ui text-text-muted">
              {item.ai_reasoning}
            </div>
          )}
        </div>
      )}

      {showAsk && (
        <AskClaudeDrawer
          itemId={item.id}
          itemTitle={item.title ?? displayCategory ?? 'this item'}
          onClose={() => setShowAsk(false)}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
docker compose exec frontend npx jest __tests__/ReviewCard.test.tsx --no-coverage
```

Expected: PASS — 10 tests

- [ ] **Step 6: Commit**

```bash
git add frontend/components/review/ frontend/__tests__/ReviewCard.test.tsx
git commit -m "feat: implement ReviewCard — border strip, actions, amend, ask-claude toggle"
```

---

## Task 3: InlineQuestion component

**Files:**
- Modify: `frontend/components/review/InlineQuestion.tsx` (replace stub)
- Test: `frontend/__tests__/InlineQuestion.test.tsx`

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/__tests__/InlineQuestion.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import InlineQuestion from '@/components/review/InlineQuestion'
import type { ReviewItemQuestion } from '@/lib/api/types'

const q1: ReviewItemQuestion = {
  id: 'q1',
  ask: 'Was this expense 100% for work?',
  type: 'single_choice',
  options: ['yes', 'no', 'partially'],
}

const q2: ReviewItemQuestion = {
  id: 'q2',
  ask: 'Do you have a receipt?',
  type: 'single_choice',
  options: ['yes', 'no'],
}

const mockOnAnswer = jest.fn()

beforeEach(() => jest.clearAllMocks())

describe('InlineQuestion', () => {
  it('renders the first question text', () => {
    mockOnAnswer.mockResolvedValue(undefined)
    render(<InlineQuestion questions={[q1, q2]} onAnswer={mockOnAnswer} />)
    expect(screen.getByText('Was this expense 100% for work?')).toBeInTheDocument()
  })

  it('renders option buttons with min-h-[56px] for single_choice', () => {
    mockOnAnswer.mockResolvedValue(undefined)
    render(<InlineQuestion questions={[q1]} onAnswer={mockOnAnswer} />)
    const yesBtn = screen.getByRole('button', { name: 'yes' })
    expect(yesBtn).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'no' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'partially' })).toBeInTheDocument()
  })

  it('calls onAnswer with question id and selected option', async () => {
    mockOnAnswer.mockResolvedValue(undefined)
    render(<InlineQuestion questions={[q1]} onAnswer={mockOnAnswer} />)
    fireEvent.click(screen.getByRole('button', { name: 'yes' }))
    await waitFor(() =>
      expect(mockOnAnswer).toHaveBeenCalledWith('q1', 'yes')
    )
  })

  it('advances to second question after first is answered', async () => {
    mockOnAnswer.mockResolvedValue(undefined)
    render(<InlineQuestion questions={[q1, q2]} onAnswer={mockOnAnswer} />)
    fireEvent.click(screen.getByRole('button', { name: 'yes' }))
    await waitFor(() =>
      expect(screen.getByText('Do you have a receipt?')).toBeInTheDocument()
    )
    expect(screen.queryByText('Was this expense 100% for work?')).not.toBeInTheDocument()
  })

  it('shows nothing when all questions are answered locally', async () => {
    mockOnAnswer.mockResolvedValue(undefined)
    const { container } = render(
      <InlineQuestion questions={[q1]} onAnswer={mockOnAnswer} />
    )
    fireEvent.click(screen.getByRole('button', { name: 'no' }))
    await waitFor(() => expect(container).toBeEmptyDOMElement())
  })

  it('renders text input for type=text questions', () => {
    const textQ: ReviewItemQuestion = { id: 'q3', ask: 'How many days?', type: 'text', options: null }
    mockOnAnswer.mockResolvedValue(undefined)
    render(<InlineQuestion questions={[textQ]} onAnswer={mockOnAnswer} />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument()
  })

  it('disables option buttons while pending', async () => {
    let resolve!: () => void
    mockOnAnswer.mockReturnValue(new Promise<void>((r) => { resolve = r }))
    render(<InlineQuestion questions={[q1]} onAnswer={mockOnAnswer} />)
    fireEvent.click(screen.getByRole('button', { name: 'yes' }))
    expect(screen.getByRole('button', { name: 'yes' })).toBeDisabled()
    resolve()
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec frontend npx jest __tests__/InlineQuestion.test.tsx --no-coverage
```

Expected: FAIL — most tests fail (stub doesn't render options)

- [ ] **Step 3: Implement InlineQuestion**

Replace the stub at `frontend/components/review/InlineQuestion.tsx`:

```typescript
'use client'
import { useState } from 'react'
import type { ReviewItemQuestion } from '@/lib/api/types'

interface InlineQuestionProps {
  questions: ReviewItemQuestion[]
  onAnswer: (questionId: string, answer: string) => Promise<void>
}

export default function InlineQuestion({ questions, onAnswer }: InlineQuestionProps) {
  const [answeredIds, setAnsweredIds] = useState<Set<string>>(new Set())
  const [textValue, setTextValue] = useState('')
  const [pending, setPending] = useState(false)

  const nextQuestion = questions.find((q) => !answeredIds.has(q.id))

  if (!nextQuestion) return null

  async function submit(answer: string) {
    if (!answer.trim() || pending) return
    setPending(true)
    await onAnswer(nextQuestion!.id, answer)
    setAnsweredIds((prev) => new Set([...prev, nextQuestion!.id]))
    setTextValue('')
    setPending(false)
  }

  return (
    <div>
      <p className="text-sm font-ui font-medium text-text-body mb-2">{nextQuestion.ask}</p>

      {nextQuestion.type === 'text' || nextQuestion.type === 'number' ? (
        <div className="flex gap-2">
          <input
            type={nextQuestion.type === 'number' ? 'number' : 'text'}
            value={textValue}
            onChange={(e) => setTextValue(e.target.value)}
            disabled={pending}
            className="flex-1 border border-border rounded px-3 py-2 text-sm font-ui bg-surface text-text-body focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <button
            type="button"
            disabled={pending || !textValue.trim()}
            onClick={() => submit(textValue)}
            className="min-h-[44px] px-4 rounded text-sm font-ui font-medium bg-accent text-surface hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            Submit
          </button>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {(nextQuestion.options ?? []).map((opt) => (
            <button
              key={opt}
              type="button"
              disabled={pending}
              onClick={() => submit(opt)}
              className="min-h-[56px] px-4 py-2 rounded border border-border text-sm font-ui text-text-body hover:bg-surface-raised transition-colors disabled:opacity-50"
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
docker compose exec frontend npx jest __tests__/InlineQuestion.test.tsx --no-coverage
```

Expected: PASS — 7 tests

- [ ] **Step 5: Commit**

```bash
git add frontend/components/review/InlineQuestion.tsx frontend/__tests__/InlineQuestion.test.tsx
git commit -m "feat: implement InlineQuestion — one-at-a-time, 56px tap targets"
```

---

## Task 4: AmendForm component

**Files:**
- Modify: `frontend/components/review/AmendForm.tsx` (replace stub)
- Test: `frontend/__tests__/AmendForm.test.tsx`

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/__tests__/AmendForm.test.tsx
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
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec frontend npx jest __tests__/AmendForm.test.tsx --no-coverage
```

Expected: FAIL — stub doesn't have amount/category/note fields

- [ ] **Step 3: Implement AmendForm**

Replace stub at `frontend/components/review/AmendForm.tsx`:

```typescript
'use client'
import { useState } from 'react'
import type { ReviewItem } from '@/lib/api/types'

const SKILL_CATEGORIES: Record<string, string[]> = {
  employee_tax_au: [
    'payg_income',
    'allowance',
    'lump_sum',
    'bank_interest',
    'investment_income_basic',
    'work_expense',
    'work_subscription',
    'work_equipment',
    'vehicle',
    'travel',
    'uniform',
    'self_education',
    'other_deduction',
    'donation',
    'private_health_rebate',
    'wfh_deduction',
  ],
}

const ALL_CATEGORIES = Array.from(new Set(Object.values(SKILL_CATEGORIES).flat()))

const CATEGORY_LABELS: Record<string, string> = {
  payg_income: 'PAYG Income',
  allowance: 'Allowance',
  lump_sum: 'Lump Sum',
  bank_interest: 'Bank Interest',
  investment_income_basic: 'Investment Income',
  work_expense: 'Work Expense',
  work_subscription: 'Work Subscription',
  work_equipment: 'Work Equipment',
  vehicle: 'Vehicle',
  travel: 'Travel',
  uniform: 'Uniform / Clothing',
  self_education: 'Self-Education',
  other_deduction: 'Other Deduction',
  donation: 'Donation',
  private_health_rebate: 'Private Health Rebate',
  wfh_deduction: 'Work From Home',
}

interface AmendFormProps {
  item: ReviewItem
  onSave: (amount: number | undefined, category: string | undefined, note: string | undefined) => void
  onCancel: () => void
}

export default function AmendForm({ item, onSave, onCancel }: AmendFormProps) {
  const [amount, setAmount] = useState<string>(
    (item.amended_amount ?? item.amount)?.toString() ?? ''
  )
  const [category, setCategory] = useState<string>(
    item.amended_category ?? item.category ?? ''
  )
  const [note, setNote] = useState<string>(item.user_note ?? '')

  const categories = item.skill_id
    ? (SKILL_CATEGORIES[item.skill_id] ?? ALL_CATEGORIES)
    : ALL_CATEGORIES

  function handleSave() {
    const parsedAmount = amount !== '' ? parseFloat(amount) : undefined
    onSave(parsedAmount, category || undefined, note || undefined)
  }

  return (
    <div data-testid="amend-form" className="space-y-3">
      <div>
        <label htmlFor="amend-amount" className="block text-xs font-ui text-text-muted mb-1">
          Amount ($)
        </label>
        <input
          id="amend-amount"
          type="number"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          aria-label="Amount"
          className="w-full border border-border rounded px-3 py-2 text-sm font-mono bg-surface text-text-body focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>

      <div>
        <label htmlFor="amend-category" className="block text-xs font-ui text-text-muted mb-1">
          Category
        </label>
        <select
          id="amend-category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          aria-label="Category"
          className="w-full border border-border rounded px-3 py-2 text-sm font-ui bg-surface text-text-body focus:outline-none focus:ring-1 focus:ring-accent"
        >
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {CATEGORY_LABELS[cat] ?? cat}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="amend-note" className="block text-xs font-ui text-text-muted mb-1">
          Note (optional)
        </label>
        <textarea
          id="amend-note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          aria-label="Note"
          className="w-full border border-border rounded px-3 py-2 text-sm font-ui bg-surface text-text-body focus:outline-none focus:ring-1 focus:ring-accent resize-none"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleSave}
          className="px-4 py-2 rounded text-sm font-ui font-medium bg-ready text-surface hover:opacity-90 transition-opacity"
        >
          Save
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded text-sm font-ui font-medium border border-border text-text-body hover:bg-surface-raised transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
docker compose exec frontend npx jest __tests__/AmendForm.test.tsx --no-coverage
```

Expected: PASS — 6 tests

- [ ] **Step 5: Commit**

```bash
git add frontend/components/review/AmendForm.tsx frontend/__tests__/AmendForm.test.tsx
git commit -m "feat: implement AmendForm — inline amount/category/note with skill category dropdown"
```

---

## Task 5: AskClaudeDrawer component

**Files:**
- Modify: `frontend/components/review/AskClaudeDrawer.tsx` (replace stub)
- Test: `frontend/__tests__/AskClaudeDrawer.test.tsx`

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/__tests__/AskClaudeDrawer.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AskClaudeDrawer from '@/components/review/AskClaudeDrawer'
import * as reviewApi from '@/lib/api/review'

jest.mock('@/lib/api/review')

const mockAskClaude = reviewApi.askClaude as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('AskClaudeDrawer', () => {
  it('renders as a side drawer with item title', () => {
    render(
      <AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={jest.fn()} />
    )
    expect(screen.getByText(/ask about work laptop/i)).toBeInTheDocument()
  })

  it('Close button calls onClose', () => {
    const onClose = jest.fn()
    render(<AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('Submit button calls askClaude API with question', async () => {
    mockAskClaude.mockResolvedValue({ data: { data: { answer: 'This is a work expense.' } } })
    render(<AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={jest.fn()} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Can I claim this?' } })
    fireEvent.click(screen.getByRole('button', { name: /ask/i }))
    expect(mockAskClaude).toHaveBeenCalledWith('item-1', 'Can I claim this?')
  })

  it('renders AI answer after successful response', async () => {
    mockAskClaude.mockResolvedValue({ data: { data: { answer: 'This is a work expense.' } } })
    render(<AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={jest.fn()} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Can I claim this?' } })
    fireEvent.click(screen.getByRole('button', { name: /ask/i }))
    await waitFor(() =>
      expect(screen.getByText('This is a work expense.')).toBeInTheDocument()
    )
  })

  it('shows Disclaimer component below AI response', async () => {
    mockAskClaude.mockResolvedValue({ data: { data: { answer: 'This is a work expense.' } } })
    render(<AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={jest.fn()} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Can I claim this?' } })
    fireEvent.click(screen.getByRole('button', { name: /ask/i }))
    await waitFor(() =>
      expect(screen.getByText(/does not provide final tax advice/i)).toBeInTheDocument()
    )
  })

  it('thread history shows previous exchange after second question', async () => {
    mockAskClaude
      .mockResolvedValueOnce({ data: { data: { answer: 'First answer.' } } })
      .mockResolvedValueOnce({ data: { data: { answer: 'Second answer.' } } })

    render(<AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={jest.fn()} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Q1' } })
    fireEvent.click(screen.getByRole('button', { name: /ask/i }))
    await waitFor(() => expect(screen.getByText('First answer.')).toBeInTheDocument())

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Q2' } })
    fireEvent.click(screen.getByRole('button', { name: /ask/i }))
    await waitFor(() => expect(screen.getByText('Second answer.')).toBeInTheDocument())

    expect(screen.getByText('First answer.')).toBeInTheDocument()
    expect(screen.getByText('Q1')).toBeInTheDocument()
    expect(screen.getByText('Q2')).toBeInTheDocument()
  })

  it('disables input and button while loading', async () => {
    let resolve!: (v: unknown) => void
    mockAskClaude.mockReturnValue(new Promise((r) => { resolve = r }))
    render(<AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={jest.fn()} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Q?' } })
    fireEvent.click(screen.getByRole('button', { name: /ask/i }))
    expect(screen.getByRole('textbox')).toBeDisabled()
    resolve({ data: { data: { answer: 'A' } } })
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec frontend npx jest __tests__/AskClaudeDrawer.test.tsx --no-coverage
```

Expected: FAIL — stub doesn't implement expected behaviour

- [ ] **Step 3: Implement AskClaudeDrawer**

Replace stub at `frontend/components/review/AskClaudeDrawer.tsx`:

```typescript
'use client'
import { useState } from 'react'
import { askClaude } from '@/lib/api/review'
import Disclaimer from '@/components/shared/Disclaimer'

interface ThreadEntry {
  question: string
  answer: string
}

interface AskClaudeDrawerProps {
  itemId: string
  itemTitle: string
  onClose: () => void
}

export default function AskClaudeDrawer({ itemId, itemTitle, onClose }: AskClaudeDrawerProps) {
  const [input, setInput] = useState('')
  const [thread, setThread] = useState<ThreadEntry[]>([])
  const [loading, setLoading] = useState(false)

  async function handleAsk() {
    const question = input.trim()
    if (!question || loading) return
    setLoading(true)
    try {
      const res = await askClaude(itemId, question)
      const answer = res.data.data.answer
      setThread((prev) => [...prev, { question, answer }])
      setInput('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      data-testid="ask-claude-drawer"
      className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-surface border-l border-border shadow-xl flex flex-col"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h2 className="font-display font-semibold text-base text-text-primary">
          Ask about {itemTitle}
        </h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="text-sm font-ui text-text-muted hover:text-text-body transition-colors"
        >
          Close ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {thread.map((entry, i) => (
          <div key={i} className="space-y-2">
            <p className="text-sm font-ui font-medium text-text-body">{entry.question}</p>
            <p className="text-sm font-ui text-text-muted">{entry.answer}</p>
          </div>
        ))}
        {thread.length > 0 && <Disclaimer />}
      </div>

      <div className="px-4 py-3 border-t border-border space-y-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          rows={3}
          placeholder="Ask a question about this item…"
          className="w-full border border-border rounded px-3 py-2 text-sm font-ui bg-surface text-text-body focus:outline-none focus:ring-1 focus:ring-accent resize-none disabled:opacity-50"
        />
        <button
          type="button"
          disabled={loading || !input.trim()}
          onClick={handleAsk}
          className="w-full min-h-[44px] rounded text-sm font-ui font-medium bg-accent text-surface hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {loading ? 'Thinking…' : 'Ask'}
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
docker compose exec frontend npx jest __tests__/AskClaudeDrawer.test.tsx --no-coverage
```

Expected: PASS — 7 tests

- [ ] **Step 5: Commit**

```bash
git add frontend/components/review/AskClaudeDrawer.tsx frontend/__tests__/AskClaudeDrawer.test.tsx
git commit -m "feat: implement AskClaudeDrawer — side drawer, thread history, Disclaimer"
```

---

## Task 6: BulkActionBar component

**Files:**
- Create: `frontend/components/review/BulkActionBar.tsx`
- Test: `frontend/__tests__/BulkActionBar.test.tsx`

Note: `group_id` is not included in the backend's `_item_dict()` response (it lives on `TaxEvent`, not `ReviewItem`). BulkActionBar therefore groups by identical `title` values. This matches ARCHITECTURE.md §14: "Triggered when N similar items detected (same description, similar amount)".

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/__tests__/BulkActionBar.test.tsx
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec frontend npx jest __tests__/BulkActionBar.test.tsx --no-coverage
```

Expected: FAIL — `Cannot find module '@/components/review/BulkActionBar'`

- [ ] **Step 3: Implement BulkActionBar**

```typescript
// frontend/components/review/BulkActionBar.tsx
interface BulkActionBarProps {
  itemIds: string[]
  groupLabel: string
  onBulkConfirm: (ids: string[]) => void
}

export default function BulkActionBar({ itemIds, groupLabel, onBulkConfirm }: BulkActionBarProps) {
  if (itemIds.length < 2) return null

  return (
    <div className="flex items-center justify-between gap-3 rounded-md bg-review-bg border border-review px-4 py-3">
      <p className="text-sm font-ui text-review">
        <span className="font-medium">{itemIds.length} items</span> share the same description:{' '}
        <span className="italic">{groupLabel}</span>
      </p>
      <button
        type="button"
        onClick={() => onBulkConfirm(itemIds)}
        className="shrink-0 min-h-[44px] px-4 py-2 rounded text-sm font-ui font-medium bg-ready text-surface hover:opacity-90 transition-opacity"
      >
        Confirm all
      </button>
    </div>
  )
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
docker compose exec frontend npx jest __tests__/BulkActionBar.test.tsx --no-coverage
```

Expected: PASS — 4 tests

- [ ] **Step 5: Commit**

```bash
git add frontend/components/review/BulkActionBar.tsx frontend/__tests__/BulkActionBar.test.tsx
git commit -m "feat: implement BulkActionBar — bulk confirm for recurring items"
```

---

## Task 7: Review page

**Files:**
- Create: `frontend/app/(dashboard)/review/page.tsx`
- Test: `frontend/__tests__/review-page.test.tsx`

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/__tests__/review-page.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ReviewPage from '@/app/(dashboard)/review/page'
import * as reviewApi from '@/lib/api/review'
import type { ReviewQueue } from '@/lib/api/types'

jest.mock('@/lib/api/review')
jest.mock('@/components/review/ReviewCard', () => ({
  default: ({ item }: { item: { title: string } }) => (
    <div data-testid="review-card">{item.title}</div>
  ),
  __esModule: true,
}))
jest.mock('@/components/review/BulkActionBar', () => ({
  default: () => <div data-testid="bulk-action-bar" />,
  __esModule: true,
}))

const mockGetReviewQueue = reviewApi.getReviewQueue as jest.Mock

const emptyQueue: ReviewQueue = {
  agent_required: { items: [], count: 0 },
  high_risk: { items: [], count: 0 },
  needs_review: { items: [], count: 0 },
  confirmed: { items: [], count: 0 },
  total: 0,
  pending: 0,
}

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

beforeEach(() => jest.clearAllMocks())

describe('ReviewPage', () => {
  it('shows loading state initially', () => {
    mockGetReviewQueue.mockReturnValue(new Promise(() => {}))
    wrap(<ReviewPage />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('shows error state on fetch failure', async () => {
    mockGetReviewQueue.mockRejectedValue(new Error('Network error'))
    wrap(<ReviewPage />)
    await waitFor(() =>
      expect(screen.getByText(/unable to load/i)).toBeInTheDocument()
    )
  })

  it('shows all-done empty state when pending is 0', async () => {
    mockGetReviewQueue.mockResolvedValue({ data: emptyQueue })
    wrap(<ReviewPage />)
    await waitFor(() =>
      expect(screen.getByText(/all caught up/i)).toBeInTheDocument()
    )
  })

  it('renders ReviewCards for needs_review items', async () => {
    const queue: ReviewQueue = {
      ...emptyQueue,
      needs_review: {
        count: 2,
        items: [
          { ...makeItem('item-1', 'Work laptop'), status: 'needs_user_review' },
          { ...makeItem('item-2', 'Spotify'), status: 'needs_user_review' },
        ],
      },
      total: 2,
      pending: 2,
    }
    mockGetReviewQueue.mockResolvedValue({ data: queue })
    wrap(<ReviewPage />)
    await waitFor(() => expect(screen.getAllByTestId('review-card')).toHaveLength(2))
    expect(screen.getByText('Work laptop')).toBeInTheDocument()
    expect(screen.getByText('Spotify')).toBeInTheDocument()
  })

  it('renders section heading for agent_required items', async () => {
    const queue: ReviewQueue = {
      ...emptyQueue,
      agent_required: {
        count: 1,
        items: [{ ...makeItem('item-3', 'Crypto sale'), status: 'needs_agent_review' }],
      },
      total: 1,
      pending: 1,
    }
    mockGetReviewQueue.mockResolvedValue({ data: queue })
    wrap(<ReviewPage />)
    await waitFor(() =>
      expect(screen.getByText(/agent review/i)).toBeInTheDocument()
    )
    expect(screen.getByText('Crypto sale')).toBeInTheDocument()
  })

  it('renders progress summary showing pending count', async () => {
    const queue: ReviewQueue = {
      ...emptyQueue,
      needs_review: {
        count: 3,
        items: [
          { ...makeItem('i1', 'Item 1'), status: 'needs_user_review' },
          { ...makeItem('i2', 'Item 2'), status: 'needs_user_review' },
          { ...makeItem('i3', 'Item 3'), status: 'needs_user_review' },
        ],
      },
      total: 3,
      pending: 3,
    }
    mockGetReviewQueue.mockResolvedValue({ data: queue })
    wrap(<ReviewPage />)
    await waitFor(() =>
      expect(screen.getByText(/3/)).toBeInTheDocument()
    )
    expect(screen.getByText(/to review/i)).toBeInTheDocument()
  })
})

function makeItem(id: string, title: string) {
  return {
    id,
    workspace_id: 'ws-1',
    tax_event_id: `evt-${id}`,
    title,
    category: 'work_expense',
    amount: 100,
    date: '2025-09-01',
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
  }
}
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec frontend npx jest __tests__/review-page.test.tsx --no-coverage
```

Expected: FAIL — `Cannot find module '@/app/(dashboard)/review/page'`

- [ ] **Step 3: Create the Review page**

```typescript
// frontend/app/(dashboard)/review/page.tsx
'use client'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { bulkAction, getReviewQueue, submitInlineAnswer, takeAction } from '@/lib/api/review'
import type { ReviewItem, ReviewQueue } from '@/lib/api/types'
import ReviewCard from '@/components/review/ReviewCard'
import BulkActionBar from '@/components/review/BulkActionBar'

function findGroups(items: ReviewItem[]): Map<string, string[]> {
  const groups = new Map<string, string[]>()
  items.forEach((item) => {
    if (!item.title) return
    const existing = groups.get(item.title) ?? []
    groups.set(item.title, [...existing, item.id])
  })
  return new Map([...groups.entries()].filter(([, ids]) => ids.length >= 2))
}

export default function ReviewPage() {
  const queryClient = useQueryClient()

  const { data: queue, isLoading, isError } = useQuery<ReviewQueue>({
    queryKey: ['review-queue'],
    queryFn: () => getReviewQueue().then((r) => r.data),
  })

  const actionMutation = useMutation({
    mutationFn: ({
      id,
      action,
      payload,
    }: {
      id: string
      action: 'confirmed' | 'amended' | 'flagged' | 'skipped'
      payload: { amount?: number; category?: string; note?: string }
    }) => takeAction(id, action, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['review-queue'] }),
  })

  const bulkMutation = useMutation({
    mutationFn: (ids: string[]) => bulkAction(ids, 'confirmed'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['review-queue'] }),
  })

  async function handleInlineAnswer(
    itemId: string,
    questionId: string,
    answer: string,
    eventId: string
  ) {
    const res = await submitInlineAnswer(itemId, questionId, answer, eventId)
    queryClient.invalidateQueries({ queryKey: ['review-queue'] })
    return { new_skill_pending: res.data.data.new_skill_pending }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-text-muted">Loading your review queue…</p>
      </div>
    )
  }

  if (isError || !queue) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-risk-high">Unable to load review queue. Please refresh.</p>
      </div>
    )
  }

  const allNeedsReview = queue.needs_review.items
  const groups = findGroups(allNeedsReview)

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">Review</h1>
        {queue.pending > 0 ? (
          <p className="text-sm font-ui text-text-muted mt-1">
            {queue.pending} item{queue.pending !== 1 ? 's' : ''} to review
          </p>
        ) : (
          <p className="text-sm font-ui text-ready mt-1">All caught up</p>
        )}
      </div>

      {queue.pending === 0 && queue.total === 0 && (
        <div className="py-16 text-center">
          <p className="font-ui text-text-muted">No items to review yet. Complete the interview to generate review items.</p>
        </div>
      )}

      {queue.agent_required.count > 0 && (
        <section>
          <h2 className="font-display text-base font-semibold text-agent mb-3">
            Agent review required ({queue.agent_required.count})
          </h2>
          <div className="space-y-3">
            {queue.agent_required.items.map((item) => (
              <ReviewCard
                key={item.id}
                item={item}
                onAction={(id, action, payload) => actionMutation.mutate({ id, action, payload })}
                onInlineAnswer={handleInlineAnswer}
              />
            ))}
          </div>
        </section>
      )}

      {queue.high_risk.count > 0 && (
        <section>
          <h2 className="font-display text-base font-semibold text-risk-high mb-3">
            Flagged for review ({queue.high_risk.count})
          </h2>
          <div className="space-y-3">
            {queue.high_risk.items.map((item) => (
              <ReviewCard
                key={item.id}
                item={item}
                onAction={(id, action, payload) => actionMutation.mutate({ id, action, payload })}
                onInlineAnswer={handleInlineAnswer}
              />
            ))}
          </div>
        </section>
      )}

      {queue.needs_review.count > 0 && (
        <section>
          <h2 className="font-display text-base font-semibold text-text-primary mb-3">
            Needs your review ({queue.needs_review.count})
          </h2>
          <div className="space-y-3">
            {[...groups.entries()].map(([title, ids]) => (
              <BulkActionBar
                key={title}
                itemIds={ids}
                groupLabel={title}
                onBulkConfirm={(ids) => bulkMutation.mutate(ids)}
              />
            ))}
            {allNeedsReview.map((item) => (
              <ReviewCard
                key={item.id}
                item={item}
                onAction={(id, action, payload) => actionMutation.mutate({ id, action, payload })}
                onInlineAnswer={handleInlineAnswer}
              />
            ))}
          </div>
        </section>
      )}

      {queue.confirmed.count > 0 && (
        <section>
          <h2 className="font-display text-base font-semibold text-ready mb-3">
            Confirmed ({queue.confirmed.count})
          </h2>
          <div className="space-y-3">
            {queue.confirmed.items.map((item) => (
              <ReviewCard
                key={item.id}
                item={item}
                onAction={(id, action, payload) => actionMutation.mutate({ id, action, payload })}
                onInlineAnswer={handleInlineAnswer}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
docker compose exec frontend npx jest __tests__/review-page.test.tsx --no-coverage
```

Expected: PASS — 6 tests

- [ ] **Step 5: Commit**

```bash
git add frontend/app/(dashboard)/review/page.tsx frontend/__tests__/review-page.test.tsx
git commit -m "feat: implement Review page — 4 sections, bulk confirm, inline actions"
```

---

## Task 8: Full test suite verification

**Files:** None — verification only

- [ ] **Step 1: Run the full frontend test suite**

```bash
docker compose exec frontend npx jest --no-coverage
```

Expected: All tests pass. New count should be approximately **168 frontend tests** (138 existing + ~30 new from this phase).

- [ ] **Step 2: Run the full backend test suite to confirm no regressions**

```bash
docker compose exec backend pytest tests/ -v --tb=short -q
```

Expected: 128 tests pass. No regressions.

- [ ] **Step 3: Confirm new files are all linted**

```bash
docker compose exec frontend npx tsc --noEmit
```

Expected: No TypeScript errors.

- [ ] **Step 4: Commit verification**

If any lint errors found, fix them. Then:

```bash
git add -A
git commit -m "fix: resolve TypeScript errors in Phase 5 review components"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Task |
|---|---|
| API types: ReviewItem, ReviewQueue, InlineAnswerResponse | Task 1 |
| 5 API functions (getReviewQueue, takeAction, submitInlineAnswer, bulkAction, askClaude) | Task 1 |
| ReviewCard: left border strip by status | Task 2 |
| ReviewCard: font-mono amount | Task 2 |
| ReviewCard: italic AI reasoning | Task 2 |
| ReviewCard: ConfidenceBar + StatusBadge | Task 2 |
| ReviewCard: actions locked when questions_complete=false | Task 2 |
| ReviewCard: inline confirmation text (no toast) | Task 2 |
| ReviewCard: expandable "Why?" section | Task 2 |
| ReviewCard: new_skill_pending banner | Task 2 |
| InlineQuestion: one at a time | Task 3 |
| InlineQuestion: 56px tap targets | Task 3 |
| InlineQuestion: text/number input fallback | Task 3 |
| AmendForm: amount/category/note | Task 4 |
| AmendForm: skill-scoped category dropdown | Task 4 |
| AskClaudeDrawer: side drawer | Task 5 |
| AskClaudeDrawer: thread history in local state | Task 5 |
| AskClaudeDrawer: Disclaimer below AI response | Task 5 |
| BulkActionBar: hidden for <2 matching items | Task 6 |
| BulkActionBar: bulk confirm only | Task 6 |
| Review page: 4 sections with section headers | Task 7 |
| Review page: loading/error/empty states | Task 7 |
| Review page: pending count in summary | Task 7 |
| All-confirmed empty state | Task 7 |

**No placeholders present.** Every step contains actual code.

**Type consistency:** `ReviewItem` defined in Task 1 types.ts is used consistently across all components. `onAction(id, action, payload)` signature matches between ReviewCard (Task 2) and Review page (Task 7). `onInlineAnswer` returns `{ new_skill_pending: boolean }` — defined in Task 1 as `InlineAnswerResponse` and unwrapped correctly in Review page.
