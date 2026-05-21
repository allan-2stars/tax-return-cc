import client from './client'
import type { ApiResponse, DocumentData, DocumentSummaryData, UploadResponse, DuplicateUploadResponse } from './types'

export const getDocuments = () =>
  client.get<ApiResponse<DocumentData[]>>('/api/v1/documents')

export const uploadDocument = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return client.post<UploadResponse | DuplicateUploadResponse>(
    '/api/v1/documents/upload',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
}

export const getDocumentSummary = (id: string) =>
  client.get<ApiResponse<DocumentSummaryData>>(`/api/v1/documents/${id}/summary`)

export const getDocumentFile = (id: string) =>
  client.get<Blob>(`/api/v1/documents/${id}/file`, { responseType: 'blob' })

export const archiveDocument = (id: string) =>
  client.delete<ApiResponse<{ document_id: string }>>(`/api/v1/documents/${id}`)
