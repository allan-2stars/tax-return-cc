import client from './client'
import type {
  ApiResponse,
  InterviewSessionData,
  AnswerResponseData,
  SkipResponseData,
  PauseResponseData,
  CompleteResponseData,
  YoYSuggestion,
} from './types'

export const getSession = () =>
  client.get<ApiResponse<InterviewSessionData>>('/api/v1/interview/session')

export const startInterview = () =>
  client.post<ApiResponse<InterviewSessionData>>('/api/v1/interview/start')

export const answerQuestion = (question_id: string, answer: string) =>
  client.post<ApiResponse<AnswerResponseData>>('/api/v1/interview/answer', { question_id, answer })

export const goBack = () =>
  client.post<ApiResponse<InterviewSessionData>>('/api/v1/interview/back')

export const skipQuestion = (question_id: string, reason: string) =>
  client.post<ApiResponse<SkipResponseData>>('/api/v1/interview/skip', { question_id, reason })

export const pauseInterview = () =>
  client.post<ApiResponse<PauseResponseData>>('/api/v1/interview/pause')

export const completeInterview = () =>
  client.post<ApiResponse<CompleteResponseData>>('/api/v1/interview/complete')

export const getYoySuggestions = () =>
  client.get<ApiResponse<YoYSuggestion[]>>('/api/v1/yoy/suggestions')

export const actOnSuggestion = (id: string, action: string) =>
  client.post<ApiResponse<YoYSuggestion>>(`/api/v1/yoy/${id}/action`, { action })
