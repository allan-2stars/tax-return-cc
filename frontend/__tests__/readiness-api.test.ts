jest.mock('@/lib/api/client', () => ({
  default: { get: jest.fn(), post: jest.fn() },
  __esModule: true,
}))

import client from '@/lib/api/client'
import * as readinessApi from '@/lib/api/readiness'

const mockGet = client.get as jest.Mock
const mockPost = client.post as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('readiness API', () => {
  it('getReadiness GETs /api/v1/readiness', async () => {
    mockGet.mockResolvedValue({ data: { data: {} } })
    await readinessApi.getReadiness()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/readiness')
  })

  it('getMissing GETs /api/v1/readiness/missing', async () => {
    mockGet.mockResolvedValue({ data: { data: {} } })
    await readinessApi.getMissing()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/readiness/missing')
  })

  it('triggerRecalculate POSTs to /api/v1/readiness/recalculate', async () => {
    mockPost.mockResolvedValue({ data: { data: { status: 'recalculating' } } })
    await readinessApi.triggerRecalculate()
    expect(mockPost).toHaveBeenCalledWith('/api/v1/readiness/recalculate')
  })
})
