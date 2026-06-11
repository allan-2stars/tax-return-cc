import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EvidenceChecklistPage from '@/app/(dashboard)/readiness/checklist/page'

jest.mock('@/lib/api/evidence', () => ({
  getEvidenceObligations: jest.fn(),
  reconcileEvidence: jest.fn(),
  updateEvidenceMatch: jest.fn(),
  undoEvidenceMatch: jest.fn(),
  __esModule: true,
}))

import { getEvidenceObligations, reconcileEvidence, undoEvidenceMatch, updateEvidenceMatch } from '@/lib/api/evidence'

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const candidatePayload = [
  {
    id: 'o1',
    workspace_id: 'ws1',
    financial_year: '2024-25',
    source_type: 'tax_event',
    source_id: null,
    obligation_key: 'bank_interest_statement',
    category: 'bank_interest',
    label: 'Bank Interest Statement',
    description: null,
    required_level: 'recommended',
    status: 'partially_matched',
    reason: 'Bank interest events are present.',
    metadata_json: {},
    created_at: null,
    updated_at: null,
    matches: [
      {
        id: 'm1',
        match_type: 'document',
        status: 'candidate',
        confidence: 0.8,
        reason: 'Possible',
        decision_history: [],
        document: {
          id: 'd1',
          original_filename: 'bank-july.pdf',
          document_type: 'bank_statement',
          status: 'ready',
        },
        tax_event: null,
      },
    ],
  },
]

const acceptedPayload = [
  {
    ...candidatePayload[0],
    status: 'matched',
    matches: [
      {
        ...candidatePayload[0].matches[0],
        status: 'accepted',
        decision_history: [
          {
            id: 'h1',
            workspace_id: 'ws1',
            evidence_match_id: 'm1',
            evidence_obligation_id: 'o1',
            action: 'accepted',
            actor: 'user',
            previous_status: 'candidate',
            new_status: 'accepted',
            note: null,
            created_at: '2026-06-10T09:30:00+00:00',
          },
        ],
      },
    ],
  },
]

const rejectedPayload = [
  {
    ...candidatePayload[0],
    status: 'missing',
    matches: [
      {
        ...candidatePayload[0].matches[0],
        status: 'rejected',
        decision_history: [
          {
            id: 'h2',
            workspace_id: 'ws1',
            evidence_match_id: 'm1',
            evidence_obligation_id: 'o1',
            action: 'rejected',
            actor: 'user',
            previous_status: 'candidate',
            new_status: 'rejected',
            note: null,
            created_at: '2026-06-10T09:31:00+00:00',
          },
        ],
      },
    ],
  },
]

describe('EvidenceChecklistPage decisions', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('clicking accept updates UI via refetch', async () => {
    ;(getEvidenceObligations as jest.Mock)
      .mockResolvedValueOnce({ data: { data: { obligations: candidatePayload } } })
      .mockResolvedValueOnce({ data: { data: { obligations: acceptedPayload } } })
    ;(updateEvidenceMatch as jest.Mock).mockResolvedValue({ data: { data: {} } })

    wrap(<EvidenceChecklistPage />)
    fireEvent.click(await screen.findByRole('button', { name: /accept match/i }))

    await waitFor(() => expect(updateEvidenceMatch).toHaveBeenCalledWith('m1', 'accepted'))
    expect(await screen.findByText(/Matched by:/i)).toBeInTheDocument()
  })

  it('clicking reject updates UI via refetch', async () => {
    ;(getEvidenceObligations as jest.Mock)
      .mockResolvedValueOnce({ data: { data: { obligations: candidatePayload } } })
      .mockResolvedValueOnce({ data: { data: { obligations: rejectedPayload } } })
    ;(updateEvidenceMatch as jest.Mock).mockResolvedValue({ data: { data: {} } })

    wrap(<EvidenceChecklistPage />)
    fireEvent.click(await screen.findByRole('button', { name: /reject match/i }))

    await waitFor(() => expect(updateEvidenceMatch).toHaveBeenCalledWith('m1', 'rejected'))
    expect(await screen.findByText(/Rejected match:/i)).toBeInTheDocument()
  })

  it('Evidence decision failure shows retryable error', async () => {
    ;(getEvidenceObligations as jest.Mock).mockResolvedValue({ data: { data: { obligations: candidatePayload } } })
    ;(updateEvidenceMatch as jest.Mock).mockRejectedValue(new Error('network'))

    wrap(<EvidenceChecklistPage />)
    fireEvent.click(await screen.findByRole('button', { name: /accept match/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/unable to update evidence match/i)
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /accept match/i })).toBeInTheDocument()
  })

  it('undo button calls API, refetches, and shows success message', async () => {
    ;(getEvidenceObligations as jest.Mock)
      .mockResolvedValueOnce({ data: { data: { obligations: acceptedPayload } } })
      .mockResolvedValueOnce({ data: { data: { obligations: candidatePayload } } })
    ;(undoEvidenceMatch as jest.Mock).mockResolvedValue({ data: { data: {} } })

    wrap(<EvidenceChecklistPage />)
    fireEvent.click(await screen.findByRole('button', { name: /undo last match decision/i }))

    await waitFor(() => expect(undoEvidenceMatch).toHaveBeenCalledWith('m1'))
    expect(await screen.findByText(/evidence match decision undone/i)).toBeInTheDocument()
    expect(await screen.findByText(/Possible match found:/i)).toBeInTheDocument()
  })

  it('undo failure shows clear error', async () => {
    ;(getEvidenceObligations as jest.Mock).mockResolvedValue({ data: { data: { obligations: acceptedPayload } } })
    ;(undoEvidenceMatch as jest.Mock).mockRejectedValue(new Error('network'))

    wrap(<EvidenceChecklistPage />)
    fireEvent.click(await screen.findByRole('button', { name: /undo last match decision/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/unable to undo evidence match decision/i)
  })

  it.each([
    ['fresh', 'Fresh'],
    ['reconciling', 'Reconciling'],
    ['stale', 'Stale'],
    ['failed', 'Failed'],
  ])('renders %s evidence freshness state', async (freshnessState, label) => {
    ;(getEvidenceObligations as jest.Mock).mockResolvedValue({
      data: {
        data: {
          obligations: candidatePayload,
          freshness: {
            freshness_state: freshnessState,
            last_reconciled_at: '2026-06-01T10:00:00+00:00',
            last_attempted_at: '2026-06-01T10:05:00+00:00',
            last_failure_at: freshnessState === 'failed' ? '2026-06-01T10:05:00+00:00' : null,
            freshness_reason: 'Evidence status is current.',
          },
        },
      },
    })

    wrap(<EvidenceChecklistPage />)

    expect(await screen.findByText(label)).toBeInTheDocument()
    expect(await screen.findByText(/last reconciled/i)).toBeInTheDocument()
    expect(screen.getByText(/last attempted/i)).toBeInTheDocument()
  })

  it('reconcile button shows progress and success feedback', async () => {
    let resolveReconcile!: (value: unknown) => void
    ;(getEvidenceObligations as jest.Mock).mockResolvedValue({
      data: { data: { obligations: candidatePayload, freshness: { freshness_state: 'stale' } } },
    })
    ;(reconcileEvidence as jest.Mock).mockReturnValue(
      new Promise((resolve) => {
        resolveReconcile = resolve
      })
    )

    wrap(<EvidenceChecklistPage />)
    fireEvent.click(await screen.findByRole('button', { name: /refresh checklist/i }))

    await waitFor(() => expect(screen.getByRole('button', { name: /reconciling/i })).toBeDisabled())
    await act(async () => {
      resolveReconcile({
        data: { data: { status: 'ok', obligations_count: 1, freshness: { freshness_state: 'fresh' } } },
      })
    })
    expect(await screen.findByText(/checklist refreshed/i)).toBeInTheDocument()
  })

  it('reconcile button shows failed feedback', async () => {
    ;(getEvidenceObligations as jest.Mock).mockResolvedValue({
      data: { data: { obligations: candidatePayload, freshness: { freshness_state: 'failed' } } },
    })
    ;(reconcileEvidence as jest.Mock).mockRejectedValue(new Error('network'))

    wrap(<EvidenceChecklistPage />)
    fireEvent.click(await screen.findByRole('button', { name: /refresh checklist/i }))

    expect(await screen.findByText(/unable to refresh evidence checklist/i)).toBeInTheDocument()
  })
})
