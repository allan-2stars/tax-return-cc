import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ReadinessPage from '@/app/(dashboard)/readiness/page'

jest.mock('@/lib/hooks/useReadiness', () => ({
  useReadiness: jest.fn(),
  __esModule: true,
}))

jest.mock('@/lib/stores/workspace.store', () => ({
  default: () => ({
    workspaceId: 'ws-1',
    financialYear: '2024-25',
    isAuthenticated: true,
    isUnlocked: true,
  }),
  __esModule: true,
}))

jest.mock('@/lib/api/estimator', () => ({
  getEstimatorSummary: jest.fn(() => new Promise(() => {})),
  __esModule: true,
}))
jest.mock('@/lib/api/interview', () => ({
  getSession: jest.fn(() => Promise.resolve({
    data: { data: { state: 'awaiting_evidence', has_incomplete_questions: false, incomplete_questions: [] } },
  })),
  __esModule: true,
}))

import { useReadiness as mockUseReadiness } from '@/lib/hooks/useReadiness'
import { getSession as mockGetSession } from '@/lib/api/interview'

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const MOCK_DATA = {
  percentage: 72,
  breakdown: [{ skill_id: 'employee_tax_au', percentage: 80, achieved_weight: 4, total_weight: 5 }],
  missing_items_count: 2,
  review_items_count: 3,
  agent_items_count: 1,
  is_stale: false,
  calculated_at: '2026-05-20T10:00:00+00:00',
  evidence_freshness: {
    freshness_state: 'fresh',
    last_reconciled_at: '2026-06-01T10:00:00+00:00',
    last_attempted_at: '2026-06-01T10:00:00+00:00',
    last_failure_at: null,
    freshness_reason: 'Evidence status is current.',
    evidence_reconciled_at: '2026-06-01T10:00:00+00:00',
    evidence_reconcile_status: 'succeeded',
  },
  evidence_obligation_summary: {
    total_obligations: 3,
    required_missing: 1,
    required_partially_matched: 1,
    required_matched: 1,
    recommended_missing: 0,
    recommended_partially_matched: 0,
    recommended_matched: 0,
    blocking_evidence_obligations: [],
  },
  readiness_2_0: {
    overall: { state: 'warning', score: 62, label: 'Needs Attention' },
    journey: {
      is_complete: true,
      has_incomplete_questions: false,
      required_blockers_count: 0,
      incomplete_questions: [],
      state: 'ready',
    },
    review: {
      unconfirmed_total: 3,
      needs_user_review_count: 2,
      needs_agent_review_count: 1,
      confirmed_count: 1,
      rejected_or_flagged_count: 0,
      state: 'warning',
    },
    evidence: {
      required_missing_count: 1,
      required_partial_count: 1,
      required_matched_count: 1,
      recommended_missing_count: 0,
      candidate_match_count: 1,
      accepted_match_count: 1,
      rejected_match_count: 0,
      blocking_obligations: [],
      state: 'blocked',
      current_rule_version: '2026.1',
    },
    blocking_reasons: ['Required evidence is incomplete.'],
    warnings: ['Some items still need your review.'],
    last_calculated_at: '2026-06-01T10:00:00+00:00',
  },
}

beforeEach(() => jest.clearAllMocks())

describe('ReadinessPage', () => {
  it('shows loading state while data is fetching', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: true, data: undefined, isError: false })
    wrap(<ReadinessPage />)
    expect(screen.getByLabelText(/loading/i)).toBeInTheDocument()
  })

  it('shows readiness ring with correct percentage', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    wrap(<ReadinessPage />)
    expect(screen.getByText('72%')).toBeInTheDocument()
    expect(screen.getByText(/overall preparation score/i)).toBeInTheDocument()
    expect(
      screen.getByText(/this score reflects evidence, review, and tax readiness checks/i)
    ).toBeInTheDocument()
  })

  it('shows stale indicator when is_stale is true', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({
      isLoading: false,
      data: { ...MOCK_DATA, is_stale: true },
      isError: false,
    })
    wrap(<ReadinessPage />)
    expect(screen.getByText(/updating/i)).toBeInTheDocument()
  })

  it('shows edit journey CTA when interview is complete', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    wrap(<ReadinessPage />)
    return screen.findByRole('link', { name: /edit your tax journey/i }).then((cta) => {
      expect(cta).toHaveAttribute('href', '/journey')
    })
  })

  it('shows continue journey CTA when interview is incomplete', async () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    ;(mockGetSession as jest.Mock).mockResolvedValue({
      data: {
        data: {
          state: 'in_progress',
          has_incomplete_questions: false,
          incomplete_questions: [],
        },
      },
    })
    wrap(<ReadinessPage />)
    expect(await screen.findByRole('link', { name: /continue your tax journey/i })).toHaveAttribute('href', '/journey')
  })

  it('shows review skipped journey answers CTA when interview has recoverable skipped answers', async () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    ;(mockGetSession as jest.Mock).mockResolvedValue({
      data: {
        data: {
          state: 'awaiting_evidence',
          has_incomplete_questions: true,
          incomplete_questions: [{ question_id: 'wfh', question_label: 'Did you work from home?', editable: true }],
        },
      },
    })
    wrap(<ReadinessPage />)
    expect(await screen.findByRole('link', { name: /review skipped journey answers/i })).toHaveAttribute('href', '/journey')
  })

  it('shows empty state message when percentage is 0', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({
      isLoading: false,
      data: { ...MOCK_DATA, percentage: 0 },
      isError: false,
    })
    wrap(<ReadinessPage />)
    expect(screen.getByText(/upload your first document/i)).toBeInTheDocument()
  })

  it('shows ready message when percentage is 100', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({
      isLoading: false,
      data: { ...MOCK_DATA, percentage: 100 },
      isError: false,
    })
    wrap(<ReadinessPage />)
    expect(screen.getByText(/your tax review package is ready/i)).toBeInTheDocument()
  })

  it('shows sub-indicators for review, agent, and missing counts', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    wrap(<ReadinessPage />)
    expect(screen.getByText(/3.*need.*your review|your review.*3/i)).toBeInTheDocument()
    expect(screen.getAllByText(/1.*agent|agent.*1/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/2.*missing|missing.*2/i)).toBeInTheDocument()
  })

  it('renders evidence readiness summary with checklist link', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    wrap(<ReadinessPage />)
    expect(screen.getAllByText(/evidence readiness/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/required missing:\s*1/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/required partial:\s*1/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/required matched:\s*1/i).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('link', { name: /open checklist/i })[0]).toHaveAttribute('href', '/readiness/checklist')
  })

  it('reduces duplicate evidence messaging when readiness_2_0 is present', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    wrap(<ReadinessPage />)
    expect(screen.queryByRole('link', { name: /view evidence checklist/i })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /open checklist/i })).toHaveAttribute('href', '/readiness/checklist')
  })

  it('renders Journey/Review/Evidence readiness cards with action links', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    wrap(<ReadinessPage />)
    expect(screen.getByText(/journey readiness/i)).toBeInTheDocument()
    expect(screen.getByText(/review readiness/i)).toBeInTheDocument()
    expect(screen.getAllByText(/evidence readiness/i).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /go to journey/i })).toHaveAttribute('href', '/journey')
    expect(screen.getByRole('link', { name: /go to review/i })).toHaveAttribute('href', '/review')
    expect(screen.getAllByRole('link', { name: /open checklist/i })[0]).toHaveAttribute('href', '/readiness/checklist')
  })

  it('renders blocked/warning/ready states from readiness_2_0', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({
      isLoading: false,
      data: {
        ...MOCK_DATA,
        readiness_2_0: {
          ...MOCK_DATA.readiness_2_0,
          journey: { ...MOCK_DATA.readiness_2_0.journey, state: 'blocked' },
          review: { ...MOCK_DATA.readiness_2_0.review, state: 'warning' },
          evidence: { ...MOCK_DATA.readiness_2_0.evidence, state: 'ready' },
        },
      },
      isError: false,
    })
    wrap(<ReadinessPage />)
    expect(screen.getByText(/state: blocked/i)).toBeInTheDocument()
    expect(screen.getByText(/state: warning/i)).toBeInTheDocument()
    expect(screen.getByText(/state: ready/i)).toBeInTheDocument()
  })

  it('renders blockers and warnings section', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    wrap(<ReadinessPage />)
    expect(screen.getByText(/blockers \(must resolve before considered ready\)/i)).toBeInTheDocument()
    expect(screen.getByText(/required evidence is incomplete/i)).toBeInTheDocument()
    expect(screen.getByText(/warnings \(should review before export\)/i)).toBeInTheDocument()
    expect(screen.getByText(/some items still need your review/i)).toBeInTheDocument()
  })

  it.each(['stale', 'failed'])('renders evidence freshness warning when evidence is %s', (freshnessState) => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({
      isLoading: false,
      data: {
        ...MOCK_DATA,
        evidence_freshness: {
          ...MOCK_DATA.evidence_freshness,
          freshness_state: freshnessState,
          freshness_reason: 'Evidence status may not be current.',
        },
      },
      isError: false,
    })
    wrap(<ReadinessPage />)
    expect(screen.getByText(new RegExp(freshnessState, 'i'))).toBeInTheDocument()
    expect(screen.getByText(/evidence status may not be current/i)).toBeInTheDocument()
  })

  it('shows error state when query fails', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: undefined, isError: true })
    wrap(<ReadinessPage />)
    expect(screen.getByText(/unable to load tax readiness/i)).toBeInTheDocument()
  })

  it('shows journey-incomplete warning with link to journey', async () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    ;(mockGetSession as jest.Mock).mockResolvedValue({
      data: {
        data: {
          state: 'awaiting_evidence',
          has_incomplete_questions: true,
          incomplete_questions: [{ question_id: 'fy_confirm', question_label: 'Financial year', editable: true }],
        },
      },
    })
    wrap(<ReadinessPage />)
    expect(await screen.findByText(/complete your tax journey before final export/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /review skipped journey answers/i })).toHaveAttribute('href', '/journey')
  })

  it('replaces ambiguous per-skill wording with tax areas checked helper copy', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    wrap(<ReadinessPage />)
    expect(screen.getByRole('button', { name: /tax areas checked/i })).toBeInTheDocument()
    expect(screen.queryByText(/per-skill breakdown/i)).not.toBeInTheDocument()
    expect(screen.getByText(/progress for each tax area reflects confirmed evidence and review progress/i)).toBeInTheDocument()
  })

  it('shows zero-progress helper when tax areas are not meaningful yet', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({
      isLoading: false,
      data: {
        ...MOCK_DATA,
        breakdown: [{ skill_id: 'employee_tax_au', percentage: 0, achieved_weight: 0, total_weight: 0 }],
      },
      isError: false,
    })
    wrap(<ReadinessPage />)
    expect(screen.getByText(/no tax areas have evidence confirmed yet/i)).toBeInTheDocument()
  })
})
