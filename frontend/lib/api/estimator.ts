import client from './client'
import type { ApiResponse, TaxEstimateSummary } from './types'

export const getEstimatorSummary = () =>
  client.get<ApiResponse<TaxEstimateSummary>>('/api/v1/estimator/summary')
