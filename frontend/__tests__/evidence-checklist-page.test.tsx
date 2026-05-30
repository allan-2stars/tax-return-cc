import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EvidenceChecklistPage from '@/app/(dashboard)/readiness/checklist/page'

jest.mock('@/lib/api/evidence', () => ({
  getEvidenceObligations: jest.fn(),
  reconcileEvidence: jest.fn(),
  updateEvidenceMatch: jest.fn(),
  __esModule: true,
}))

import { getEvidenceObligations, updateEvidenceMatch } from '@/lib/api/evidence'

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
    matches: [{ ...candidatePayload[0].matches[0], status: 'accepted' }],
  },
]

const rejectedPayload = [
  {
    ...candidatePayload[0],
    status: 'missing',
    matches: [{ ...candidatePayload[0].matches[0], status: 'rejected' }],
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
})
