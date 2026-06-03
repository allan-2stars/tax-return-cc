export type ApiErrorKind = 'session' | 'unlock' | 'network' | 'validation' | 'unknown'

export interface NormalizedApiError {
  kind: ApiErrorKind
  code: string | null
  message: string
}

export function normalizeApiError(error: unknown, fallback = 'Something went wrong. Please try again.'): NormalizedApiError {
  const response = (
    error as {
      response?: {
        status?: number
        data?: {
          detail?: { error_code?: string; message?: string }
          error_code?: string
          message?: string
        }
      }
      message?: string
    }
  )?.response

  const detail = response?.data?.detail
  const code = detail?.error_code ?? response?.data?.error_code ?? null
  const serverMessage = detail?.message ?? response?.data?.message

  if (response?.status === 401 || code === 'session_expired' || code === 'invalid_session' || code === 'not_authenticated') {
    return {
      kind: 'session',
      code,
      message: 'Your session has expired. Sign in again, then try again.',
    }
  }

  if (code === 'unlock_expired' || code === 'not_unlocked' || code === 'unlock_invalid') {
    return {
      kind: 'unlock',
      code,
      message: 'Your workspace lock has expired. Unlock your workspace, then try again.',
    }
  }

  if (!response) {
    return {
      kind: 'network',
      code: null,
      message: fallback,
    }
  }

  if (response.status === 422 || response.status === 400) {
    return {
      kind: 'validation',
      code,
      message: serverMessage ?? fallback,
    }
  }

  return {
    kind: 'unknown',
    code,
    message: serverMessage ?? fallback,
  }
}
