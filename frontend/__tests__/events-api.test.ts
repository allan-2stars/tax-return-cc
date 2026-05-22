jest.mock('@/lib/api/client', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn() },
}))

import * as eventsApi from '@/lib/api/events'
import client from '@/lib/api/client'

const mockPost = client.post as jest.Mock
beforeEach(() => jest.clearAllMocks())

describe('events API', () => {
  it('createManualEvent posts to /events/manual', async () => {
    mockPost.mockResolvedValue({ data: { data: { items: [], count: 0 } } })
    const payload = { event_type: 'deduction' as const, category: 'work_expense', description: 'Laptop', amount: 1200, date: '2025-08-01', frequency: 'one_off' as const, note: null, periods: null }
    await eventsApi.createManualEvent(payload)
    expect(mockPost).toHaveBeenCalledWith('/api/v1/events/manual', payload)
  })
  it('attachReceipt posts file as multipart', async () => {
    mockPost.mockResolvedValue({ data: { data: { document_id: 'doc-1' } } })
    const file = new File(['content'], 'receipt.pdf', { type: 'application/pdf' })
    await eventsApi.attachReceipt('evt-1', file)
    expect(mockPost).toHaveBeenCalledWith('/api/v1/events/evt-1/attach-receipt', expect.any(FormData), { headers: { 'Content-Type': 'multipart/form-data' } })
  })
})
