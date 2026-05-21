jest.mock('@/lib/api/client', () => ({
  default: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
  __esModule: true,
}))

import client from '@/lib/api/client'
import {
  getDocuments,
  uploadDocument,
  getDocumentSummary,
  getDocumentFile,
  archiveDocument,
} from '@/lib/api/documents'

const mockClient = client as {
  get: jest.Mock
  post: jest.Mock
  delete: jest.Mock
}

beforeEach(() => jest.clearAllMocks())

describe('documents API', () => {
  it('getDocuments calls GET /api/v1/documents', async () => {
    mockClient.get.mockResolvedValue({ data: { status: 'ok', data: [] } })
    await getDocuments()
    expect(mockClient.get).toHaveBeenCalledWith('/api/v1/documents')
  })

  it('uploadDocument posts multipart form to /api/v1/documents/upload', async () => {
    mockClient.post.mockResolvedValue({ data: { document_id: 'doc-1', status: 'processing' } })
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    await uploadDocument(file)
    expect(mockClient.post).toHaveBeenCalledWith(
      '/api/v1/documents/upload',
      expect.any(FormData),
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  })

  it('getDocumentSummary calls GET /api/v1/documents/{id}/summary', async () => {
    mockClient.get.mockResolvedValue({ data: { status: 'ok', data: {} } })
    await getDocumentSummary('doc-1')
    expect(mockClient.get).toHaveBeenCalledWith('/api/v1/documents/doc-1/summary')
  })

  it('getDocumentFile calls GET with responseType blob', async () => {
    mockClient.get.mockResolvedValue({ data: new Blob() })
    await getDocumentFile('doc-1')
    expect(mockClient.get).toHaveBeenCalledWith(
      '/api/v1/documents/doc-1/file',
      { responseType: 'blob' }
    )
  })

  it('archiveDocument calls DELETE /api/v1/documents/{id}', async () => {
    mockClient.delete.mockResolvedValue({ data: { status: 'ok', data: { document_id: 'doc-1' } } })
    await archiveDocument('doc-1')
    expect(mockClient.delete).toHaveBeenCalledWith('/api/v1/documents/doc-1')
  })
})
