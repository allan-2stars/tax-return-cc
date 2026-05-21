jest.mock('@/lib/api/client', () => ({
  default: { get: jest.fn(), post: jest.fn() },
  __esModule: true,
}))

import client from '@/lib/api/client'
import {
  getSession, startInterview, answerQuestion,
  goBack, skipQuestion, getYoySuggestions, actOnSuggestion,
} from '@/lib/api/interview'

const mockGet = client.get as jest.Mock
const mockPost = client.post as jest.Mock

beforeEach(() => jest.clearAllMocks())

test('getSession calls GET /api/v1/interview/session', () => {
  mockGet.mockResolvedValue({ data: { data: {} } })
  getSession()
  expect(mockGet).toHaveBeenCalledWith('/api/v1/interview/session')
})

test('startInterview calls POST /api/v1/interview/start', () => {
  mockPost.mockResolvedValue({ data: { data: {} } })
  startInterview()
  expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/start')
})

test('answerQuestion calls POST /api/v1/interview/answer with body', () => {
  mockPost.mockResolvedValue({ data: { data: {} } })
  answerQuestion('q1', 'yes')
  expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/answer', { question_id: 'q1', answer: 'yes' })
})

test('goBack calls POST /api/v1/interview/back', () => {
  mockPost.mockResolvedValue({ data: { data: {} } })
  goBack()
  expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/back')
})

test('skipQuestion calls POST /api/v1/interview/skip with body', () => {
  mockPost.mockResolvedValue({ data: { data: {} } })
  skipQuestion('q1', 'user_skipped')
  expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/skip', { question_id: 'q1', reason: 'user_skipped' })
})

test('getYoySuggestions calls GET /api/v1/yoy/suggestions', () => {
  mockGet.mockResolvedValue({ data: { data: [] } })
  getYoySuggestions()
  expect(mockGet).toHaveBeenCalledWith('/api/v1/yoy/suggestions')
})

test('actOnSuggestion calls POST /api/v1/yoy/{id}/action with body', () => {
  mockPost.mockResolvedValue({ data: { data: {} } })
  actOnSuggestion('sug-1', 'confirmed')
  expect(mockPost).toHaveBeenCalledWith('/api/v1/yoy/sug-1/action', { action: 'confirmed' })
})
