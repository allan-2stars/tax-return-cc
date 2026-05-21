import { render, screen } from '@testing-library/react'
import DocumentCard from '@/components/evidence/DocumentCard'
import type { DocumentData } from '@/lib/api/types'

const READY_DOC: DocumentData = {
  document_id: 'doc-1',
  original_filename: 'payslip.pdf',
  file_type: 'pdf',
  file_size_bytes: 12345,
  status: 'ready',
  document_type: 'payg_summary',
  uploaded_at: '2026-05-01T10:00:00+00:00',
  processed_at: '2026-05-01T10:01:00+00:00',
}

const PROCESSING_DOC: DocumentData = {
  ...READY_DOC,
  document_id: 'doc-2',
  status: 'processing',
  processed_at: null,
}

describe('DocumentCard', () => {
  it('renders filename, upload date, and status badge', () => {
    render(<DocumentCard document={READY_DOC} onRemove={jest.fn()} />)
    expect(screen.getByText('payslip.pdf')).toBeInTheDocument()
    expect(screen.getByText(/1 May 2026/i)).toBeInTheDocument()
    expect(screen.getByText(/ready/i)).toBeInTheDocument()
  })

  it('shows processing spinner when status is processing', () => {
    render(<DocumentCard document={PROCESSING_DOC} onRemove={jest.fn()} />)
    expect(screen.getByTestId('processing-spinner')).toBeInTheDocument()
    expect(screen.getByText(/processing/i)).toBeInTheDocument()
  })
})
