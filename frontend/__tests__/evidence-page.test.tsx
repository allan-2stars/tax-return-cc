import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EvidencePage from '@/app/(dashboard)/evidence/page'
import * as documentsApi from '@/lib/api/documents'

jest.mock('@/lib/api/documents')
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

const mockGetDocuments = documentsApi.getDocuments as jest.Mock

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

beforeEach(() => jest.clearAllMocks())

describe('EvidencePage', () => {
  it('shows empty state when no documents exist', async () => {
    mockGetDocuments.mockResolvedValue({ data: { data: [] } })
    wrap(<EvidencePage />)
    await waitFor(() =>
      expect(screen.getByText(/upload your first document to get started/i)).toBeInTheDocument()
    )
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
    wrap(<EvidencePage />)
    await waitFor(() => expect(screen.getAllByTestId('document-card')).toHaveLength(2))
    expect(screen.getByText('payslip.pdf')).toBeInTheDocument()
    expect(screen.getByText('bank.csv')).toBeInTheDocument()
  })
})
