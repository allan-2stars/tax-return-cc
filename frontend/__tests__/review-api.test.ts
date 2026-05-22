import * as reviewApi from '@/lib/api/review'
import client from '@/lib/api/client'

jest.mock('@/lib/api/client', () => ({
  get: jest.fn(),
  post: jest.fn(),
}))

const mockGet = client.get as jest.Mock
const mockPost = client.post as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('review API', () => {
  it('getReviewQueue calls GET /api/v1/review/queue', async () => {
    mockGet.mockResolvedValue({ data: { agent_required: { items: [], count: 0 }, high_risk: { items: [], count: 0 }, needs_review: { items: [], count: 0 }, confirmed: { items: [], count: 0 }, total: 0, pending: 0 } })
    await reviewApi.getReviewQueue()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/review/queue')
  })

  it('takeAction calls POST /api/v1/review/:id/action with body', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await reviewApi.takeAction('item-1', 'confirmed', {})
    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/review/item-1/action',
      { action: 'confirmed' }
    )
  })

  it('takeAction passes amount and category for amended', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await reviewApi.takeAction('item-1', 'amended', { amount: 99.5, category: 'work_expense' })
    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/review/item-1/action',
      { action: 'amended', amount: 99.5, category: 'work_expense' }
    )
  })

  it('submitInlineAnswer calls POST /api/v1/review/:id/inline-answer', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await reviewApi.submitInlineAnswer('item-1', 'q1', 'yes', 'evt-1')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/review/item-1/inline-answer', {
      question_id: 'q1',
      answer: 'yes',
      event_id: 'evt-1',
    })
  })

  it('bulkAction calls POST /api/v1/review/bulk-action with item_ids', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await reviewApi.bulkAction(['item-1', 'item-2'], 'confirmed')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/review/bulk-action', {
      item_ids: ['item-1', 'item-2'],
      action: 'confirmed',
    })
  })

  it('askClaude calls POST /api/v1/review/:id/ask', async () => {
    mockPost.mockResolvedValue({ data: { data: { answer: 'hello' } } })
    await reviewApi.askClaude('item-1', 'Is this deductible?')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/review/item-1/ask', {
      question: 'Is this deductible?',
    })
  })
})
