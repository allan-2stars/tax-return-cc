import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MissingPage from '@/app/(dashboard)/readiness/missing/page'

jest.mock('@/lib/hooks/useReadiness', () => ({
  useMissing: jest.fn(),
  __esModule: true,
}))
jest.mock('@/lib/api/interview', () => ({
  getSession: jest.fn(() => Promise.resolve({
    data: { data: { state: 'awaiting_evidence', has_incomplete_questions: false, incomplete_questions: [] } },
  })),
  __esModule: true,
}))

jest.mock('@/lib/stores/workspace.store', () => ({
  default: () => ({
    workspaceId: 'ws-1',
    financialYear: '2024-25',
  }),
  __esModule: true,
}))

import { useMissing as mockUseMissing } from '@/lib/hooks/useReadiness'
import { getSession as mockGetSession } from '@/lib/api/interview'

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const MOCK_MISSING = {
  available_now: [
    { requirement_id: 'receipt', display: 'Work receipts', weight: 1.0, skill_id: 'employee_tax_au', how_to_get: 'Keep your receipts' },
  ],
  available_after_fy: [
    { requirement_id: 'payg', display: 'PAYG payment summary', weight: 2.0, skill_id: 'employee_tax_au', how_to_get: 'Download from myGov' },
  ],
}

beforeEach(() => jest.clearAllMocks())

describe('MissingPage', () => {
  it('shows loading state while data is fetching', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: true, data: undefined })
    wrap(<MissingPage />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('shows page heading', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_MISSING })
    wrap(<MissingPage />)
    expect(screen.getByRole('heading', { name: /missing evidence/i })).toBeInTheDocument()
  })

  it('renders upload evidence CTA and source explanation', async () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_MISSING })
    wrap(<MissingPage />)
    expect(await screen.findByRole('link', { name: /upload evidence/i })).toHaveAttribute('href', '/evidence')
    expect(
      screen.getByText(/this list is based on your current tax journey answers and reviewed tax events/i)
    ).toBeInTheDocument()
    expect(
      screen.getByText(/if you skipped questions, more evidence may be required after you answer them/i)
    ).toBeInTheDocument()
  })

  it('renders skipped journey warning when interview has incomplete answers', async () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_MISSING })
    ;(mockGetSession as jest.Mock).mockResolvedValue({
      data: {
        data: {
          state: 'awaiting_evidence',
          has_incomplete_questions: true,
          incomplete_questions: [{ question_id: 'wfh', question_label: 'Did you work from home?', editable: true }],
        },
      },
    })
    wrap(<MissingPage />)
    expect(await screen.findByRole('link', { name: /review skipped journey answers/i })).toHaveAttribute('href', '/journey')
  })

  it('renders available now items', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_MISSING })
    wrap(<MissingPage />)
    expect(screen.getByText('Work receipts')).toBeInTheDocument()
  })

  it('renders available after FY items', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_MISSING })
    wrap(<MissingPage />)
    expect(screen.getByText('PAYG payment summary')).toBeInTheDocument()
  })

  it('shows empty state when both lists are empty', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({
      isLoading: false,
      data: { available_now: [], available_after_fy: [] },
    })
    wrap(<MissingPage />)
    expect(screen.getByText(/nothing missing/i)).toBeInTheDocument()
  })

  it('shows error state when query fails', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: false, data: undefined, isError: true })
    wrap(<MissingPage />)
    expect(screen.getByText(/unable to load missing items/i)).toBeInTheDocument()
  })
})
