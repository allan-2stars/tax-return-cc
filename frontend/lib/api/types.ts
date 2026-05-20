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

export interface SkillBreakdownItem {
  skill_id: string
  percentage: number
  achieved_weight: number
  total_weight: number
}

export interface ReadinessData {
  percentage: number
  breakdown: SkillBreakdownItem[]
  missing_items_count: number
  review_items_count: number
  agent_items_count: number
  is_stale: boolean
  calculated_at: string | null
}

export interface MissingItem {
  requirement_id: string
  display: string
  weight: number
  skill_id: string
  how_to_get?: string
}

export interface MissingData {
  available_now: MissingItem[]
  available_after_fy: MissingItem[]
}

export interface RecalculateData {
  status: 'recalculating'
}
