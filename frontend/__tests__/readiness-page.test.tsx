import { render, screen } from '@testing-library/react'
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

import { useReadiness as mockUseReadiness } from '@/lib/hooks/useReadiness'

const MOCK_DATA = {
  percentage: 72,
  breakdown: [{ skill_id: 'employee_tax_au', percentage: 80, achieved_weight: 4, total_weight: 5 }],
  missing_items_count: 2,
  review_items_count: 3,
  agent_items_count: 1,
  is_stale: false,
  calculated_at: '2026-05-20T10:00:00+00:00',
}

beforeEach(() => jest.clearAllMocks())

describe('ReadinessPage', () => {
  it('shows loading state while data is fetching', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: true, data: undefined, isError: false })
    render(<ReadinessPage />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('shows readiness ring with correct percentage', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    render(<ReadinessPage />)
    expect(screen.getByText('72%')).toBeInTheDocument()
  })

  it('shows stale indicator when is_stale is true', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({
      isLoading: false,
      data: { ...MOCK_DATA, is_stale: true },
      isError: false,
    })
    render(<ReadinessPage />)
    expect(screen.getByText(/updating/i)).toBeInTheDocument()
  })

  it('shows CTA button linking to /journey', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    render(<ReadinessPage />)
    const cta = screen.getByRole('link', { name: /continue your tax journey/i })
    expect(cta).toHaveAttribute('href', '/journey')
  })

  it('shows empty state message when percentage is 0', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({
      isLoading: false,
      data: { ...MOCK_DATA, percentage: 0 },
      isError: false,
    })
    render(<ReadinessPage />)
    expect(screen.getByText(/upload your first document/i)).toBeInTheDocument()
  })

  it('shows ready message when percentage is 100', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({
      isLoading: false,
      data: { ...MOCK_DATA, percentage: 100 },
      isError: false,
    })
    render(<ReadinessPage />)
    expect(screen.getByText(/your tax review package is ready/i)).toBeInTheDocument()
  })

  it('shows sub-indicators for review, agent, and missing counts', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    render(<ReadinessPage />)
    expect(screen.getByText(/3.*need.*your review|your review.*3/i)).toBeInTheDocument()
    expect(screen.getByText(/1.*agent|agent.*1/i)).toBeInTheDocument()
    expect(screen.getByText(/2.*missing|missing.*2/i)).toBeInTheDocument()
  })

  it('shows error state when query fails', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: undefined, isError: true })
    render(<ReadinessPage />)
    expect(screen.getByText(/unable to load tax readiness/i)).toBeInTheDocument()
  })
})
