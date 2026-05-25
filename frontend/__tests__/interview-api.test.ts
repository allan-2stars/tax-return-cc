jest.mock('@/lib/api/client', () => ({
  default: { get: jest.fn(), post: jest.fn() },
  __esModule: true,
}))

import client from '@/lib/api/client'
import {
  getSession, startInterview, answerQuestion,
  goBack, skipQuestion, getYoySuggestions, actOnSuggestion,
  getInterviewSummary, jumpToQuestion,
} from '@/lib/api/interview'

const mockGet = client.get as jest.Mock
const mockPost = client.post as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('interview API', () => {
  it('getSession calls GET /api/v1/interview/session', async () => {
    mockGet.mockResolvedValue({ data: { data: {} } })
    await getSession()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/interview/session')
  })

  it('startInterview calls POST /api/v1/interview/start', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await startInterview()
    expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/start')
  })

  it('answerQuestion calls POST /api/v1/interview/answer with body', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await answerQuestion('q1', 'yes')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/answer', { question_id: 'q1', answer: 'yes' })
  })

  it('answerQuestion coerces numeric answer to string', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await answerQuestion('dependent_count', 3 as any)
    expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/answer', {
      question_id: 'dependent_count',
      answer: '3',
    })
  })

  it('goBack calls POST /api/v1/interview/back', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await goBack()
    expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/back')
  })

  it('skipQuestion calls POST /api/v1/interview/skip with body', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await skipQuestion('q1', 'user_skipped')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/skip', { question_id: 'q1', reason: 'user_skipped' })
  })

  it('getYoySuggestions calls GET /api/v1/yoy/suggestions', async () => {
    mockGet.mockResolvedValue({ data: { data: [] } })
    await getYoySuggestions()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/yoy/suggestions')
  })

  it('actOnSuggestion calls POST /api/v1/yoy/{id}/action with body', async () => {
    mockPost.mockResolvedValue({ data: { data: {} } })
    await actOnSuggestion('sug-1', 'confirmed')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/yoy/sug-1/action', { action: 'confirmed' })
  })

  it('getInterviewSummary calls GET /api/v1/interview/summary', async () => {
    const mockData = { sections: [] }
    mockGet.mockResolvedValueOnce({ data: { data: mockData } })
    const result = await getInterviewSummary()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/interview/summary')
    expect(result.data.data).toEqual(mockData)
  })

  it('jumpToQuestion calls POST /api/v1/interview/jump with question_id', async () => {
    const mockData = { state: 'in_progress', current_question: null, progress: { completed: 0, total: 0 } }
    mockPost.mockResolvedValueOnce({ data: { data: mockData } })
    const result = await jumpToQuestion('residency')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/jump', { question_id: 'residency' })
    expect(result.data.data).toEqual(mockData)
  })
})
