import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import UploadZone from '@/components/evidence/UploadZone'

jest.mock('@/lib/api/documents', () => ({
  uploadDocument: jest.fn(),
  __esModule: true,
}))

jest.mock('@/lib/hooks/useSSE', () => ({
  useSSE: jest.fn().mockReturnValue({ data: null, status: 'closed', error: null }),
  __esModule: true,
}))

import { uploadDocument } from '@/lib/api/documents'

const mockUpload = uploadDocument as jest.Mock
const onUploadComplete = jest.fn()
const onDuplicate = jest.fn()

function renderZone() {
  return render(
    <UploadZone onUploadComplete={onUploadComplete} onDuplicate={onDuplicate} />
  )
}

beforeEach(() => jest.clearAllMocks())

describe('UploadZone', () => {
  it('renders idle state with drop text and supported formats', () => {
    renderZone()
    expect(screen.getByText(/drop your document here/i)).toBeInTheDocument()
    expect(screen.getByText(/supported/i)).toBeInTheDocument()
    expect(screen.getByText(/maximum 20mb/i)).toBeInTheDocument()
  })

  it('shows error for oversized file (client-side validation)', () => {
    renderZone()
    const input = screen.getByLabelText(/upload document/i)
    const file = new File(['x'], 'big.pdf', { type: 'application/pdf' })
    Object.defineProperty(file, 'size', { value: 21 * 1024 * 1024 })
    fireEvent.change(input, { target: { files: [file] } })
    expect(screen.getByText(/too large/i)).toBeInTheDocument()
  })

  it('shows error for unsupported format (client-side validation)', () => {
    renderZone()
    const input = screen.getByLabelText(/upload document/i)
    const file = new File(['content'], 'doc.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    fireEvent.change(input, { target: { files: [file] } })
    expect(screen.getByText(/not supported/i)).toBeInTheDocument()
  })

  it('transitions to uploading state on valid file selection', async () => {
    mockUpload.mockReturnValue(new Promise(() => {})) // never resolves — stays uploading
    renderZone()
    const input = screen.getByLabelText(/upload document/i)
    const file = new File(['%PDF-content'], 'payslip.pdf', { type: 'application/pdf' })
    fireEvent.change(input, { target: { files: [file] } })
    await waitFor(() => expect(screen.getByText(/payslip\.pdf/i)).toBeInTheDocument())
  })
})
