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

export type InterviewState = 'not_started' | 'in_progress' | 'paused' | 'awaiting_evidence' | 'complete'

export interface InterviewQuestion {
  id: string
  ask: string
  type: 'single_choice' | 'multi_choice' | 'text' | 'number'
  options: string[] | null
  branches: Record<string, string[]> | null
  required: boolean
  why: string | null
  hint: string | null
}

export interface InterviewProgress {
  completed: number
  total: number
}

export interface InterviewSessionData {
  state: InterviewState
  session_id?: string
  current_question: InterviewQuestion | null
  answers?: Record<string, string>
  activated_skills?: string[]
  progress: InterviewProgress
  resumed?: boolean
}

export interface AnswerResponseData {
  session_id: string
  state: InterviewState
  next_question: InterviewQuestion | null
  activated_skills: string[]
  progress: InterviewProgress
}

export interface SkipResponseData {
  session_id: string
  state: InterviewState
  next_question: InterviewQuestion | null
  progress: InterviewProgress
}

export interface PauseResponseData {
  session_id: string
  state: InterviewState
}

export interface CompleteResponseData {
  session_id: string
  state: InterviewState
}

export interface YoYSuggestion {
  id: string
  workspace_id: string
  source_workspace_id: string | null
  financial_year: string
  category: string
  description: string
  amount_last_year: number | null
  frequency: string | null
  status: string
  actioned_at: string | null
}
