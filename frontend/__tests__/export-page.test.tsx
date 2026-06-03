import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ExportPage from '@/app/(dashboard)/export/page'
import * as exportApi from '@/lib/api/export'
import type { ExportEligibility, ExportRecord } from '@/lib/api/types'

jest.mock('@/lib/api/export')
jest.mock('@/components/export/EligibilityCard', () => ({
  default: ({ eligibility, onGenerateAnyway }: { eligibility: ExportEligibility; onGenerateAnyway: () => void }) => (
    <div>
      {eligibility.can_export && (
        <button onClick={onGenerateAnyway} data-testid="generate-anyway">Generate anyway</button>
      )}
      {eligibility.blocking_reasons.map((r, i) => <p key={i}>{r}</p>)}
    </div>
  ),
  __esModule: true,
}))
jest.mock('@/components/export/ExportHistoryCard', () => ({
  default: ({ record }: { record: ExportRecord }) => (
    <div data-testid={`history-${record.id}`}>{record.status}</div>
  ),
  __esModule: true,
}))
jest.mock('@/components/shared/Disclaimer', () => ({
  default: () => <div data-testid="disclaimer" />,
  __esModule: true,
}))

const mockGetEligibility = exportApi.getEligibility as jest.Mock
const mockGenerateExport = exportApi.generateExport as jest.Mock
const mockGetExportStatus = exportApi.getExportStatus as jest.Mock
const mockGetExportHistory = exportApi.getExportHistory as jest.Mock

const readyEligibility: ExportEligibility = {
  can_export: true,
  blocking_reasons: [],
  warnings: [],
  evidence_required_missing_count: 0,
  evidence_required_partial_count: 0,
  evidence_required_matched_count: 2,
  evidence_recommended_missing_count: 0,
  evidence_export_status: {
    would_block_export: false,
    blocking_required_count: 0,
    missing_required_count: 0,
    partial_required_count: 0,
    blocking_evidence_obligations: [],
    mode: 'soft_block',
    message: 'Evidence requirements are currently satisfied.',
  },
  evidence_freshness: {
    freshness_state: 'fresh',
    last_reconciled_at: '2026-06-01T10:00:00+00:00',
    last_attempted_at: '2026-06-01T10:00:00+00:00',
    last_failure_at: null,
    freshness_reason: 'Evidence status is current.',
    evidence_reconciled_at: '2026-06-01T10:00:00+00:00',
    evidence_reconcile_status: 'succeeded',
  },
}
const emptyHistory: ExportRecord[] = []

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

beforeEach(() => {
  jest.clearAllMocks()
  mockGetExportHistory.mockResolvedValue({ data: { data: emptyHistory } })
})

describe('ExportPage', () => {
  it('renders soft-block warning panel when evidence would block export in future', async () => {
    mockGetEligibility.mockResolvedValue({
      data: {
        data: {
          can_export: true,
          blocking_reasons: [],
            warnings: [],
            evidence_required_missing_count: 2,
            evidence_required_partial_count: 1,
            evidence_required_matched_count: 0,
            evidence_recommended_missing_count: 1,
            evidence_export_status: {
            would_block_export: true,
            blocking_required_count: 3,
            missing_required_count: 2,
            partial_required_count: 1,
            blocking_evidence_obligations: [],
            mode: 'soft_block',
            message:
              'Export is allowed for now, but required evidence is incomplete and may block export in a future hardening milestone.',
          },
        },
      },
    })

    wrap(<ExportPage />)
    expect(await screen.findByText(/evidence preview/i)).toBeInTheDocument()
    expect(screen.getByText(/export is allowed, but evidence may be incomplete/i)).toBeInTheDocument()
    expect(screen.getByText(/required missing: 2/i)).toBeInTheDocument()
    expect(screen.getByText(/recommended missing: 1/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /review evidence checklist/i })).toHaveAttribute(
      'href',
      '/readiness/checklist'
    )
    expect(screen.getByRole('button', { name: /generate review pack/i })).toBeEnabled()
  })

  it('renders evidence ready state when soft-block is false', async () => {
    mockGetEligibility.mockResolvedValue({ data: { data: readyEligibility } })
    wrap(<ExportPage />)
    expect(await screen.findByText(/evidence preview/i)).toBeInTheDocument()
    expect(screen.getByText(/evidence requirements are currently satisfied/i)).toBeInTheDocument()
    expect(screen.getByText(/required matched: 2/i)).toBeInTheDocument()
  })

  it.each(['stale', 'failed'])('renders export evidence freshness warning when evidence is %s', async (freshnessState) => {
    mockGetEligibility.mockResolvedValue({
      data: {
        data: {
          ...readyEligibility,
          evidence_freshness: {
            ...readyEligibility.evidence_freshness,
            freshness_state: freshnessState,
            freshness_reason: 'Evidence status may not be current.',
          },
        },
      },
    })

    wrap(<ExportPage />)

    expect(await screen.findByText(freshnessState === 'stale' ? 'Stale' : 'Failed')).toBeInTheDocument()
    expect(screen.getByText(/export preview may be using stale evidence status/i)).toBeInTheDocument()
  })

  it('shows journey-incomplete blocking reason from backend eligibility', async () => {
    mockGetEligibility.mockResolvedValue({
      data: {
        data: {
          can_export: false,
          blocking_reasons: ['Complete your Tax Journey before generating export.'],
          warnings: [],
        },
      },
    })

    wrap(<ExportPage />)
    expect(await screen.findByText(/complete your tax journey before generating export/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/export password/i)).not.toBeInTheDocument()
  })

  it('clears password field immediately after generate', async () => {
    mockGetEligibility.mockResolvedValue({ data: { data: readyEligibility } })
    mockGenerateExport.mockResolvedValue({
      data: { data: { export_id: 'exp-1', status: 'generating', warnings: [] } },
    })
    mockGetExportStatus.mockReturnValue(new Promise(() => {}))

    wrap(<ExportPage />)
    await waitFor(() => screen.getByLabelText(/export password/i))

    fireEvent.change(screen.getByLabelText(/export password/i), {
      target: { value: 'mysecret123' },
    })
    expect(screen.getByLabelText(/export password/i)).toHaveValue('mysecret123')

    fireEvent.click(screen.getByRole('button', { name: /generate review pack/i }))

    await waitFor(() =>
      expect(screen.queryByLabelText(/export password/i)).not.toBeInTheDocument()
    )
    expect(mockGenerateExport).toHaveBeenCalledWith('mysecret123')
  })

  it('polls status until ready then shows download button', async () => {
    jest.useFakeTimers()
    mockGetEligibility.mockResolvedValue({ data: { data: readyEligibility } })
    mockGenerateExport.mockResolvedValue({
      data: { data: { export_id: 'exp-2', status: 'generating', warnings: [] } },
    })
    mockGetExportStatus
      .mockResolvedValueOnce({
        data: {
          data: {
            id: 'exp-2', workspace_id: 'ws-1', financial_year: '2024-25',
            status: 'generating', readiness_pct: 80, confirmed_count: 5,
            review_count: 1, agent_count: 0, missing_count: 0,
            file_size_bytes: null, expires_at: null, created_at: null,
          },
        },
      })
      .mockResolvedValue({
        data: {
          data: {
            id: 'exp-2', workspace_id: 'ws-1', financial_year: '2024-25',
            status: 'ready', readiness_pct: 80, confirmed_count: 5,
            review_count: 1, agent_count: 0, missing_count: 0,
            file_size_bytes: 102400, expires_at: '2026-05-23T10:00:00+00:00',
            created_at: '2026-05-22T10:00:00+00:00',
          },
        },
      })

    wrap(<ExportPage />)
    await waitFor(() => screen.getByLabelText(/export password/i))
    fireEvent.change(screen.getByLabelText(/export password/i), { target: { value: 'pass' } })
    fireEvent.click(screen.getByRole('button', { name: /generate review pack/i }))

    await waitFor(() => screen.getByTestId('generating-spinner'))

    await act(async () => {
      jest.advanceTimersByTime(2100)
    })

    await waitFor(() => screen.getByText(/download now/i))
    jest.useRealTimers()
  })

  it('shows failure message and generate again button when export status is failed', async () => {
    mockGetEligibility.mockResolvedValue({ data: { data: readyEligibility } })
    mockGenerateExport.mockResolvedValue({
      data: { data: { export_id: 'exp-fail', status: 'generating', warnings: [] } },
    })
    mockGetExportStatus.mockResolvedValue({
      data: {
        data: {
          id: 'exp-fail', workspace_id: 'ws-1', financial_year: '2024-25',
          status: 'failed', readiness_pct: 80, confirmed_count: 5,
          review_count: 1, agent_count: 0, missing_count: 0,
          file_size_bytes: null, expires_at: null, created_at: null,
          error_message: 'Export interrupted (server restart or worker shutdown). Please generate again.',
        },
      },
    })

    wrap(<ExportPage />)
    await waitFor(() => screen.getByLabelText(/export password/i))
    fireEvent.change(screen.getByLabelText(/export password/i), { target: { value: 'pass' } })
    fireEvent.click(screen.getByRole('button', { name: /generate review pack/i }))

    await waitFor(() => {
      expect(screen.getByText(/export interrupted/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /generate again/i })).toBeInTheDocument()
    })
  })
})
