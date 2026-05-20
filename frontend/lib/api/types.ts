// frontend/lib/api/types.ts
export interface ApiResponse<T> {
  data: T
  status: 'ok'
}

export interface ApiError {
  error_code: string
  message: string
  action: string | null
  retryable: boolean
}

export interface HealthResponse {
  status: 'ok'
  db: 'ok' | 'error'
  storage: 'ok' | 'error'
}

export interface SessionData {
  workspace_id: string
  financial_year: string
  is_unlocked: boolean
}

export interface LoginData extends SessionData {
  setup_not_confirmed?: boolean
}

export interface SetupData {
  recovery_key: string
}
