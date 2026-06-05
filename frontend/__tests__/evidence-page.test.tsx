import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EvidencePage from '@/app/(dashboard)/evidence/page'
import * as documentsApi from '@/lib/api/documents'
import * as evidenceApi from '@/lib/api/evidence'

jest.mock('@/lib/api/documents')
jest.mock('@/lib/api/evidence')
jest.mock('@/lib/stores/workspace.store', () => ({
  default: jest.fn().mockReturnValue({
    workspaceId: 'ws-1',
    financialYear: '2024-25',
    isAuthenticated: true,
    isUnlocked: true,
  }),
  __esModule: true,
}))
jest.mock('@/components/evidence/UploadZone', () => ({
  default: () => <div data-testid="upload-zone" />,
  __esModule: true,
}))
jest.mock('@/components/evidence/DocumentCard', () => ({
  default: ({ document }: { document: { original_filename: string } }) => (
    <div data-testid="document-card">{document.original_filename}</div>
  ),
  __esModule: true,
}))
jest.mock('@/lib/api/interview', () => ({
  getSession: jest.fn(() => Promise.resolve({
    data: { data: { state: 'awaiting_evidence', has_incomplete_questions: false, incomplete_questions: [] } },
  })),
  __esModule: true,
}))

const mockGetDocuments = documentsApi.getDocuments as jest.Mock
const mockGetEvidenceObligations = evidenceApi.getEvidenceObligations as jest.Mock
const mockGetSession = jest.requireMock('@/lib/api/interview').getSession as jest.Mock

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

beforeEach(() => jest.clearAllMocks())

describe('EvidencePage', () => {
  it('shows empty state when no documents exist', async () => {
    mockGetDocuments.mockResolvedValue({ data: { data: [] } })
    mockGetEvidenceObligations.mockResolvedValue({ data: { data: { obligations: [] } } })
    wrap(<EvidencePage />)
    await waitFor(() =>
      expect(screen.getByText(/upload your first document to get started/i)).toBeInTheDocument()
    )
  })

  it('shows generic upload guidance when no obligations exist', async () => {
    mockGetDocuments.mockResolvedValue({ data: { data: [] } })
    mockGetEvidenceObligations.mockResolvedValue({ data: { data: { obligations: [] } } })
    wrap(<EvidencePage />)
    expect(await screen.findByText(/you can upload documents such as income statements, bank interest statements, receipts, donation receipts, private health insurance statements, and work-from-home evidence/i)).toBeInTheDocument()
    expect(screen.getByText(/more specific suggestions will appear after you answer more journey questions or review extracted items/i)).toBeInTheDocument()
  })

  it('shows obligation-specific suggestions when obligations exist', async () => {
    mockGetDocuments.mockResolvedValue({ data: { data: [] } })
    mockGetEvidenceObligations.mockResolvedValue({
      data: {
        data: {
          obligations: [
            {
              id: 'obl-1',
              workspace_id: 'ws-1',
              financial_year: '2024-25',
              source_type: 'journey',
              source_id: null,
              obligation_key: 'private_health_insurance_statement',
              category: 'health',
              label: 'Private health insurance statement',
              description: null,
              required_level: 'recommended',
              status: 'missing',
              reason: null,
              matches: [],
              metadata_json: {},
              created_at: null,
              updated_at: null,
            },
            {
              id: 'obl-2',
              workspace_id: 'ws-1',
              financial_year: '2024-25',
              source_type: 'journey',
              source_id: null,
              obligation_key: 'work_from_home_records',
              category: 'work_from_home',
              label: 'Work from home records',
              description: null,
              required_level: 'required',
              status: 'missing',
              reason: null,
              matches: [],
              metadata_json: {},
              created_at: null,
              updated_at: null,
            },
          ],
        },
      },
    })
    wrap(<EvidencePage />)
    expect(await screen.findByText(/recommended to upload now/i)).toBeInTheDocument()
    expect(screen.getByText(/private health insurance statement/i)).toBeInTheDocument()
    expect(screen.getByText(/work-from-home log, diary, or timesheet/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /review missing evidence/i })).toHaveAttribute('href', '/readiness/missing')
  })

  it('shows skipped journey warning when session has incomplete answers', async () => {
    mockGetDocuments.mockResolvedValue({ data: { data: [] } })
    mockGetEvidenceObligations.mockResolvedValue({ data: { data: { obligations: [] } } })
    mockGetSession.mockResolvedValue({
      data: {
        data: {
          state: 'awaiting_evidence',
          has_incomplete_questions: true,
          incomplete_questions: [{ question_id: 'wfh', question_label: 'Did you work from home?', editable: true }],
        },
      },
    })
    wrap(<EvidencePage />)
    expect(await screen.findByText(/some skipped journey answers may reveal more evidence requirements later/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /review skipped journey answers/i })).toHaveAttribute('href', '/journey')
  })

  it('renders a DocumentCard for each document returned', async () => {
    mockGetDocuments.mockResolvedValue({
      data: {
        data: [
          {
            document_id: 'doc-1',
            original_filename: 'payslip.pdf',
            file_type: 'pdf',
            file_size_bytes: 12345,
            status: 'ready',
            document_type: 'payg_summary',
            uploaded_at: '2026-05-01T10:00:00+00:00',
            processed_at: '2026-05-01T10:01:00+00:00',
          },
          {
            document_id: 'doc-2',
            original_filename: 'bank.csv',
            file_type: 'csv',
            file_size_bytes: 5000,
            status: 'processing',
            document_type: null,
            uploaded_at: '2026-05-02T09:00:00+00:00',
            processed_at: null,
          },
        ],
      },
    })
    mockGetEvidenceObligations.mockResolvedValue({ data: { data: { obligations: [] } } })
    wrap(<EvidencePage />)
    await waitFor(() => expect(screen.getAllByTestId('document-card')).toHaveLength(2))
    expect(screen.getByText('payslip.pdf')).toBeInTheDocument()
    expect(screen.getByText('bank.csv')).toBeInTheDocument()
  })
})
