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

  it('shows all-done empty state when pending is 0 and total is 0', async () => {
    mockGetReviewQueue.mockResolvedValue({ data: { data: emptyQueue } })
    wrap(<ReviewPage />)
    await waitFor(() =>
      expect(screen.getByText(/no items to review yet/i)).toBeInTheDocument()
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
    mockGetReviewQueue.mockResolvedValue({ data: { data: queue } })
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
    mockGetReviewQueue.mockResolvedValue({ data: { data: queue } })
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
    mockGetReviewQueue.mockResolvedValue({ data: { data: queue } })
    wrap(<ReviewPage />)
    await waitFor(() =>
      expect(screen.getByText(/3 items? to review/i)).toBeInTheDocument()
    )
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
    group_id: null,
    group_display: null,
  }
}
