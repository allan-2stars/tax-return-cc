import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DuplicateModal from '@/components/evidence/DuplicateModal'

jest.mock('@/lib/api/documents', () => ({
  getDocumentSummary: jest.fn(),
  __esModule: true,
}))

import { getDocumentSummary } from '@/lib/api/documents'

const SUMMARY = {
  document_id: 'doc-1',
  original_filename: 'payslip.pdf',
  file_type: 'pdf',
  file_size_bytes: 12345,
  status: 'ready' as const,
  document_type: 'payg_summary',
  uploaded_at: '2026-05-01T10:00:00+00:00',
  processed_at: '2026-05-01T10:01:00+00:00',
  extraction_method: 'pdfplumber',
  extraction_confidence: 0.95,
  extracted_fields: null,
}

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('DuplicateModal', () => {
  it('renders existing document summary and single CTA only', async () => {
    ;(getDocumentSummary as jest.Mock).mockResolvedValue({ data: { data: SUMMARY } })

    wrap(<DuplicateModal existingDocumentId="doc-1" onClose={jest.fn()} />)

    // Wait for the summary to load
    await screen.findByText('payslip.pdf')
    expect(screen.getByText(/1 May 2026/i)).toBeInTheDocument()

    // Single action only — "View existing document" link
    const cta = screen.getByRole('link', { name: /view existing document/i })
    expect(cta).toBeInTheDocument()

    // No "Replace" or "Keep both" options
    expect(screen.queryByRole('button', { name: /replace/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /keep both/i })).not.toBeInTheDocument()
  })
})
