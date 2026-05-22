import client from './client'
import type { ExportEligibility, ExportRecord, GenerateExportData } from './types'

export const getEligibility = () =>
  client.get<{ data: ExportEligibility }>('/api/v1/export/eligibility')

export const generateExport = (password: string) =>
  client.post<{ data: GenerateExportData }>('/api/v1/export/generate', { password })

export const getExportStatus = (id: string) =>
  client.get<{ data: ExportRecord }>(`/api/v1/export/${id}/status`)

export const downloadExport = async (id: string): Promise<void> => {
  const response = await client.get(`/api/v1/export/${id}/download`, { responseType: 'blob' })
  const disposition = response.headers['content-disposition'] as string | undefined
  const match = disposition?.match(/filename="([^"]+)"/)
  const filename = match?.[1] ?? 'review-package.zip'
  const url = URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export const getExportHistory = () =>
  client.get<{ data: ExportRecord[] }>('/api/v1/export/history')
