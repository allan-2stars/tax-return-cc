import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ReviewPage from '@/app/(dashboard)/review/page'
import * as reviewApi from '@/lib/api/review'
import type { ReviewQueue } from '@/lib/api/types'

const mockRouterPush = jest.fn()
jest.mock('next/navigation', () => ({
  useSearchParams: jest.fn(() => new URLSearchParams()),
  useRouter: () => ({ push: mockRouterPush }),
}))

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

beforeEach(() => {
  jest.clearAllMocks()
  mockRouterPush.mockReset()
})

describe('ReviewPage', () => {
  it('shows loading state initially', () => {
    mockGetReviewQueue.mockReturnValue(new Promise(() => {}))
    wrap(<ReviewPage />)
    expect(screen.getByLabelText(/loading/i)).toBeInTheDocument()
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

describe('ReviewPage — filter tabs', () => {
  it('renders all filter tabs with All active by default', async () => {
    mockGetReviewQueue.mockResolvedValue({ data: { data: emptyQueue } })
    wrap(<ReviewPage />)
    await waitFor(() => screen.getByRole('tab', { name: /^all$/i }))
    expect(screen.getByRole('tab', { name: /^all$/i })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: /^income$/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /^deductions$/i })).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /^wfh$/i })).not.toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /^investments$/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /^confirmed$/i })).toBeInTheDocument()
  })

  it('shows only income items when Income filter is active', async () => {
    const queue: ReviewQueue = {
      ...emptyQueue,
      needs_review: {
        count: 2,
        items: [
          { ...makeItem('item-income', 'PAYG Income'), category: 'payg_income', status: 'needs_user_review' },
          { ...makeItem('item-expense', 'Work Laptop'), category: 'work_expense', status: 'needs_user_review' },
        ],
      },
      total: 2,
      pending: 2,
    }
    mockGetReviewQueue.mockResolvedValue({ data: { data: queue } })
    wrap(<ReviewPage />)
    await waitFor(() => screen.getByRole('tab', { name: /^income$/i }))
    fireEvent.click(screen.getByRole('tab', { name: /^income$/i }))
    await waitFor(() => expect(screen.getByText('PAYG Income')).toBeInTheDocument())
    expect(screen.queryByText('Work Laptop')).not.toBeInTheDocument()
  })

  it('pushes URL with filter param when tab is clicked', async () => {
    mockGetReviewQueue.mockResolvedValue({ data: { data: emptyQueue } })
    wrap(<ReviewPage />)
    await waitFor(() => screen.getByRole('tab', { name: /^income$/i }))
    fireEvent.click(screen.getByRole('tab', { name: /^income$/i }))
    expect(mockRouterPush).toHaveBeenCalledWith('/review?filter=income', { scroll: false })
  })

  it('pushes /review with no params when All tab is clicked after another filter', async () => {
    mockGetReviewQueue.mockResolvedValue({ data: { data: emptyQueue } })
    wrap(<ReviewPage />)
    await waitFor(() => screen.getByRole('tab', { name: /^deductions$/i }))
    fireEvent.click(screen.getByRole('tab', { name: /^deductions$/i }))
    fireEvent.click(screen.getByRole('tab', { name: /^all$/i }))
    expect(mockRouterPush).toHaveBeenLastCalledWith('/review', { scroll: false })
  })

  it('shows guidance text explaining Supporting Evidence vs Review', async () => {
    mockGetReviewQueue.mockResolvedValue({ data: { data: emptyQueue } })
    wrap(<ReviewPage />)
    await waitFor(() =>
      expect(screen.getByText(/supporting evidence = uploaded source documents/i)).toBeInTheDocument()
    )
    expect(
      screen.getByText(/review = tax items extracted or manually added for confirmation before export/i)
    ).toBeInTheDocument()
  })

  it('shows crypto in Investments filter', async () => {
    const queue: ReviewQueue = {
      ...emptyQueue,
      needs_review: {
        count: 2,
        items: [
          { ...makeItem('item-crypto', 'Crypto disposal'), category: 'crypto', status: 'needs_user_review' },
          { ...makeItem('item-income', 'PAYG Income'), category: 'payg_income', status: 'needs_user_review' },
        ],
      },
      total: 2,
      pending: 2,
    }
    mockGetReviewQueue.mockResolvedValue({ data: { data: queue } })
    wrap(<ReviewPage />)
    await waitFor(() => screen.getByRole('tab', { name: /^investments$/i }))
    fireEvent.click(screen.getByRole('tab', { name: /^investments$/i }))
    await waitFor(() => expect(screen.getByText('Crypto disposal')).toBeInTheDocument())
    expect(screen.queryByText('PAYG Income')).not.toBeInTheDocument()
  })

  it('shows managed_fund_distribution in Investments filter', async () => {
    const queue: ReviewQueue = {
      ...emptyQueue,
      needs_review: {
        count: 2,
        items: [
          { ...makeItem('item-managed', 'Managed fund annual statement'), category: 'managed_fund_distribution', status: 'needs_user_review' },
          { ...makeItem('item-expense', 'Work Laptop'), category: 'work_expense', status: 'needs_user_review' },
        ],
      },
      total: 2,
      pending: 2,
    }
    mockGetReviewQueue.mockResolvedValue({ data: { data: queue } })
    wrap(<ReviewPage />)
    await waitFor(() => screen.getByRole('tab', { name: /^investments$/i }))
    fireEvent.click(screen.getByRole('tab', { name: /^investments$/i }))
    await waitFor(() => expect(screen.getByText('Managed fund annual statement')).toBeInTheDocument())
    expect(screen.queryByText('Work Laptop')).not.toBeInTheDocument()
  })

  it('shows bank_interest in Income and not Investments', async () => {
    const queue: ReviewQueue = {
      ...emptyQueue,
      needs_review: {
        count: 2,
        items: [
          { ...makeItem('item-bank', 'Savings account interest'), category: 'bank_interest', status: 'needs_user_review' },
          { ...makeItem('item-capital', 'ETF sale'), category: 'capital_gain', status: 'needs_user_review' },
        ],
      },
      total: 2,
      pending: 2,
    }
    mockGetReviewQueue.mockResolvedValue({ data: { data: queue } })
    wrap(<ReviewPage />)
    await waitFor(() => screen.getByRole('tab', { name: /^income$/i }))

    fireEvent.click(screen.getByRole('tab', { name: /^income$/i }))
    await waitFor(() => expect(screen.getByText('Savings account interest')).toBeInTheDocument())
    expect(screen.queryByText('ETF sale')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('tab', { name: /^investments$/i }))
    await waitFor(() => expect(screen.getByText('ETF sale')).toBeInTheDocument())
    expect(screen.queryByText('Savings account interest')).not.toBeInTheDocument()
  })

  it('shows wfh_deduction in Deductions filter', async () => {
    const queue: ReviewQueue = {
      ...emptyQueue,
      needs_review: {
        count: 2,
        items: [
          { ...makeItem('item-wfh', 'WFH running costs'), category: 'wfh_deduction', status: 'needs_user_review' },
          { ...makeItem('item-income', 'PAYG Income'), category: 'payg_income', status: 'needs_user_review' },
        ],
      },
      total: 2,
      pending: 2,
    }
    mockGetReviewQueue.mockResolvedValue({ data: { data: queue } })
    wrap(<ReviewPage />)
    await waitFor(() => screen.getByRole('tab', { name: /^deductions$/i }))
    fireEvent.click(screen.getByRole('tab', { name: /^deductions$/i }))
    await waitFor(() => expect(screen.getByText('WFH running costs')).toBeInTheDocument())
    expect(screen.queryByText('PAYG Income')).not.toBeInTheDocument()
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
