jest.mock('@/lib/api/client', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn() },
}))

import * as exportApi from '@/lib/api/export'
import client from '@/lib/api/client'

const mockGet = client.get as jest.Mock
const mockPost = client.post as jest.Mock
beforeEach(() => jest.clearAllMocks())

describe('export API', () => {
  it('getEligibility calls correct endpoint', async () => {
    mockGet.mockResolvedValue({ data: { data: { can_export: true, blocking_reasons: [], warnings: [] } } })
    const result = await exportApi.getEligibility()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/export/eligibility')
    expect(result.data.data.can_export).toBe(true)
  })
  it('generateExport posts password', async () => {
    mockPost.mockResolvedValue({ data: { data: { export_id: 'e-1', status: 'generating', warnings: [] } } })
    const result = await exportApi.generateExport('secret')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/export/generate', { password: 'secret' })
    expect(result.data.data.export_id).toBe('e-1')
  })
  it('getExportStatus calls correct endpoint', async () => {
    mockGet.mockResolvedValue({ data: { data: { id: 'e-1', status: 'ready' } } })
    const result = await exportApi.getExportStatus('e-1')
    expect(mockGet).toHaveBeenCalledWith('/api/v1/export/e-1/status')
  })
  it('getExportHistory calls correct endpoint', async () => {
    mockGet.mockResolvedValue({ data: { data: [] } })
    await exportApi.getExportHistory()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/export/history')
  })
  it('downloadExport fetches blob and triggers anchor download', async () => {
    const fakeBlob = new Blob(['zip content'])
    mockGet.mockResolvedValue({
      data: fakeBlob,
      headers: { 'content-disposition': 'attachment; filename="review-package-2024-25-abc12345.zip"' },
    })

    const mockUrl = 'blob:http://localhost/fake'
    const createObjectURL = jest.fn().mockReturnValue(mockUrl)
    const revokeObjectURL = jest.fn()
    Object.defineProperty(globalThis, 'URL', {
      value: { createObjectURL, revokeObjectURL },
      writable: true,
    })

    const clickSpy = jest.fn()
    const mockAnchor = { href: '', download: '', click: clickSpy }
    jest.spyOn(document, 'createElement').mockReturnValueOnce(mockAnchor as unknown as HTMLAnchorElement)

    await exportApi.downloadExport('e-1')

    expect(mockGet).toHaveBeenCalledWith('/api/v1/export/e-1/download', { responseType: 'blob' })
    expect(mockAnchor.download).toBe('review-package-2024-25-abc12345.zip')
    expect(clickSpy).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledWith(mockUrl)

    jest.restoreAllMocks()
  })
})
