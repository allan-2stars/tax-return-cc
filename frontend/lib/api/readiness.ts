import client from './client'
import type { ApiResponse, ReadinessData, MissingData, RecalculateData } from './types'

export const getReadiness = () =>
  client.get<ApiResponse<ReadinessData>>('/api/v1/readiness')

export const getMissing = () =>
  client.get<ApiResponse<MissingData>>('/api/v1/readiness/missing')

export const triggerRecalculate = () =>
  client.post<ApiResponse<RecalculateData>>('/api/v1/readiness/recalculate')
