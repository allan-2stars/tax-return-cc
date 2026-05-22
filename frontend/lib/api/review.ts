import client from './client'
import type {
  ReviewQueue,
  ReviewActionResponse,
  InlineAnswerResponse,
  BulkActionResponseData,
  AskClaudeResponseData,
  ApiResponse,
} from './types'

export const getReviewQueue = () =>
  client.get<{ data: ReviewQueue }>('/api/v1/review/queue')

export const takeAction = (
  itemId: string,
  action: 'confirmed' | 'amended' | 'flagged' | 'skipped',
  payload: { amount?: number; category?: string; note?: string }
) =>
  client.post<ApiResponse<ReviewActionResponse>>(`/api/v1/review/${itemId}/action`, {
    action,
    ...payload,
  })

export const submitInlineAnswer = (
  itemId: string,
  questionId: string,
  answer: string,
  eventId: string
) =>
  client.post<ApiResponse<InlineAnswerResponse>>(`/api/v1/review/${itemId}/inline-answer`, {
    question_id: questionId,
    answer,
    event_id: eventId,
  })

export const bulkAction = (itemIds: string[], action: 'confirmed') =>
  client.post<ApiResponse<BulkActionResponseData>>('/api/v1/review/bulk-action', {
    item_ids: itemIds,
    action,
  })

export const askClaude = (itemId: string, question: string) =>
  client.post<ApiResponse<AskClaudeResponseData>>(`/api/v1/review/${itemId}/ask`, { question })
