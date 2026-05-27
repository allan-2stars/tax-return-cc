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
  user_lodger_type?: string | null
  setup_confirmed?: boolean
  setup_required?: boolean
  authenticated?: boolean
}

export interface LoginData extends SessionData {
  setup_not_confirmed?: boolean
}

export interface SetupData {
  recovery_key: string
  workspace_id: string
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
  currency?: boolean
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

export type DocumentStatus = 'processing' | 'ready' | 'failed' | 'archived'

export interface DocumentData {
  document_id: string
  original_filename: string
  file_type: string | null
  file_size_bytes: number | null
  status: DocumentStatus
  document_type: string | null
  uploaded_at: string
  processed_at: string | null
}

export interface DocumentSummaryData extends DocumentData {
  extraction_method: string | null
  extraction_confidence: number | null
  extracted_fields: Record<string, unknown> | null
}

export interface UploadResponse {
  document_id: string
  status: 'processing'
}

export interface DuplicateUploadResponse {
  status: 'duplicate'
  existing_document_id: string
}

export interface SSEEvent {
  document_id: string
  status: DocumentStatus
  stage?: string
  progress?: number
  events_created?: number
  error_code?: string
}

export interface ReviewItemQuestion {
  id: string
  ask: string
  type: 'single_choice' | 'multi_choice' | 'text' | 'number'
  options: string[] | null
}

export interface ReviewItem {
  id: string
  workspace_id: string
  tax_event_id: string | null
  title: string | null
  category: string | null
  amount: number | null
  date: string | null
  skill_id: string | null
  risk_level: string
  ai_reasoning: string | null
  confidence: number | null
  inline_questions: ReviewItemQuestion[]
  questions_complete: boolean
  status: string
  user_action: string | null
  user_note: string | null
  amended_amount: number | null
  amended_category: string | null
  skipped_until: string | null
  created_at: string
  reviewed_at: string | null
  review_duration_seconds: number | null
  group_id: string | null
  group_display: string | null
}

export interface ReviewQueueSection {
  items: ReviewItem[]
  count: number
}

export interface ReviewQueue {
  agent_required: ReviewQueueSection
  high_risk: ReviewQueueSection
  needs_review: ReviewQueueSection
  confirmed: ReviewQueueSection
  total: number
  pending: number
}

export interface ReviewActionResponse extends ReviewItem {}

export interface InlineAnswerResponse extends ReviewItem {
  new_skill_pending: boolean
}

export interface BulkActionResponseData {
  items: ReviewItem[]
  count: number
}

export interface AskClaudeResponseData {
  answer: string
}

// ── Export types ─────────────────────────────────────────────────────────────

export interface ExportEligibility {
  can_export: boolean
  blocking_reasons: string[]
  warnings: string[]
}

export type ExportStatus = 'generating' | 'ready' | 'expired' | 'failed'

export interface ExportRecord {
  id: string
  workspace_id: string
  financial_year: string
  readiness_pct: number | null
  confirmed_count: number
  review_count: number
  agent_count: number
  missing_count: number
  status: ExportStatus
  error_message?: string | null
  file_size_bytes: number | null
  expires_at: string | null
  created_at: string | null
}

export interface GenerateExportData {
  export_id: string
  status: ExportStatus
  warnings: string[]
}

// ── Manual entry types ────────────────────────────────────────────────────────

export interface ManualEventPeriod {
  months: number
  amount_per_month: number
}

export type ManualEventFrequency = 'one_off' | 'annual' | 'monthly'
export type ManualEventType = 'income' | 'deduction' | 'investment' | 'wfh' | 'other'
export type InvestmentSubType = 'shares' | 'crypto' | 'bank_interest' | 'managed_fund' | 'foreign_income' | 'other'

export interface ManualEventPayload {
  event_type: ManualEventType
  category: string
  description: string
  amount: number
  date: string
  frequency: ManualEventFrequency
  note: string | null
  periods: ManualEventPeriod[] | null
  metadata?: Record<string, unknown>
  review_status?: string
  possible_duplicate?: boolean
}

export interface ManualEventItem {
  id: string
  title: string | null
  category: string | null
  amount: number | null
}

export interface CreateManualEventData {
  items: ManualEventItem[]
  count: number
}

export interface AttachReceiptData {
  document_id: string
}

// ── Settings types ────────────────────────────────────────────────────────────

export interface WorkspaceInfo {
  id: string
  name: string
  financial_year: string
  status: string
  readiness_pct: number
}

export interface WorkspaceListData {
  items: WorkspaceInfo[]
}

export interface DeleteWorkspaceResult {
  redirect_to: string
}

export interface CreateWorkspaceResult extends WorkspaceInfo {
  yoy_count: number
}

export interface AiUsageItem {
  operation: string
  calls: number
  cost_usd: number
}

export interface AiUsageData {
  ai_provider: string
  items: AiUsageItem[]
  total_cost_usd: number
}

export interface StorageUsageData {
  documents_bytes: number
  exports_bytes: number
  db_bytes: number
}

export interface SkillInfo {
  skill_id: string
  version: string
  display_name: string
}

export interface AboutData {
  active_skills: SkillInfo[]
  disclaimer: string
}

export interface RecoveryKeyData {
  recovery_key: string
}

// ── Estimator types ───────────────────────────────────────────────────────────

export interface TaxEstimateSummary {
  gross_income: string
  total_deductions: string
  taxable_income: string
  payg_withheld: string
  confirmed_only: boolean
  pending_count: number
  ato_calculator_url: string
  disclaimer: string
}

// ── Interview summary types ───────────────────────────────────────────────────

export interface SummaryAnswer {
  question_id: string
  question_label: string
  answer_value: string
  answer_label: string
  editable: boolean
}

export interface SummarySection {
  title: string
  answers: SummaryAnswer[]
}

export interface InterviewSummaryData {
  sections: SummarySection[]
}
