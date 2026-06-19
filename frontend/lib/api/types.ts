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

export type EvidenceFreshnessState = 'fresh' | 'reconciling' | 'stale' | 'failed'

export interface EvidenceFreshness {
  freshness_state: EvidenceFreshnessState
  last_reconciled_at: string | null
  last_attempted_at: string | null
  last_failure_at: string | null
  trigger_source?: string | null
  freshness_reason: string
  evidence_reconciled_at?: string | null
  evidence_reconcile_status?: string
  evidence_reconcile_meta?: Record<string, unknown> | null
}

export interface EvidenceDiagnosticItem {
  id: string
  obligation_key: string
  label: string
  description?: string | null
  category: string | null
  required_level: string
  status: string
  reason: string | null
  rule_version?: string | null
  explanation?: Partial<Pick<ExplanationSidecar, 'what_user_should_check' | 'plain_english_summary'>> | null
}

export interface ReadinessData {
  percentage: number
  breakdown: SkillBreakdownItem[]
  missing_items_count: number
  review_items_count: number
  agent_items_count: number
  is_stale: boolean
  calculated_at: string | null
  evidence_obligation_summary?: {
    total_obligations: number
    required_missing: number
    required_partially_matched: number
    required_matched: number
    recommended_missing: number
    recommended_partially_matched: number
    recommended_matched: number
    blocking_evidence_obligations: EvidenceDiagnosticItem[]
  }
  evidence_freshness?: EvidenceFreshness
  readiness_2_0?: {
    overall: {
      state: 'blocked' | 'warning' | 'ready'
      score: number
      label: string
    }
    journey: {
      is_complete: boolean
      has_incomplete_questions: boolean
      required_blockers_count: number
      incomplete_questions: Array<{
        question_id: string
        question_label: string
        editable: boolean
      }>
      state: 'blocked' | 'warning' | 'ready'
    }
    review: {
      unconfirmed_total: number
      needs_user_review_count: number
      needs_agent_review_count: number
      confirmed_count: number
      rejected_or_flagged_count: number
      state: 'blocked' | 'warning' | 'ready'
    }
    evidence: {
      required_missing_count: number
      required_partial_count: number
      required_matched_count: number
      recommended_missing_count: number
      candidate_match_count: number
      accepted_match_count: number
      rejected_match_count: number
      blocking_obligations: EvidenceDiagnosticItem[]
      state: 'blocked' | 'warning' | 'ready'
      current_rule_version: string
    }
    blocking_reasons: string[]
    warnings: string[]
    last_calculated_at: string | null
  }
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

export type EvidenceObligationStatus =
  | 'missing'
  | 'partially_matched'
  | 'matched'
  | 'waived'
  | 'not_applicable'

export interface EvidenceMatchDocument {
  id: string
  original_filename: string
  document_type: string | null
  status: string
}

export interface EvidenceMatchTaxEvent {
  id: string
  event_type: string
  category: string
  status: string
}

export interface EvidenceMatchDecisionHistoryItem {
  id: string
  workspace_id: string
  evidence_match_id: string
  evidence_obligation_id: string
  action: string
  actor: string
  previous_status: string | null
  new_status: string | null
  note: string | null
  created_at: string | null
}

export interface EvidenceMatchItem {
  id: string
  match_type: 'document' | 'tax_event' | 'manual'
  status: 'candidate' | 'accepted' | 'rejected'
  confidence: number | null
  reason: string | null
  decision_history: EvidenceMatchDecisionHistoryItem[]
  document: EvidenceMatchDocument | null
  tax_event: EvidenceMatchTaxEvent | null
}

export interface EvidenceObligation {
  id: string
  workspace_id: string
  financial_year: string
  source_type: string
  source_id: string | null
  obligation_key: string
  category: string | null
  label: string
  description: string | null
  required_level: 'required' | 'recommended' | 'optional'
  status: EvidenceObligationStatus
  reason: string | null
  rule_version?: string | null
  explanation?: ExplanationSidecar | null
  matches: EvidenceMatchItem[]
  metadata_json: Record<string, unknown>
  created_at: string | null
  updated_at: string | null
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
  edit_mode?: boolean
  edit_target?: string | null
  edit_flow_completed?: number
  edit_flow_total?: number
  resumed?: boolean
  needs_restart?: boolean
  missing_platform_ids?: string[]
  incomplete_questions?: { question_id: string; question_label: string; editable: boolean }[]
  has_incomplete_questions?: boolean
}

export interface AnswerResponseData {
  session_id: string
  state: InterviewState
  next_question: InterviewQuestion | null
  activated_skills: string[]
  progress: InterviewProgress
  edit_mode?: boolean
  edit_target?: string | null
  edit_flow_completed?: number
  edit_flow_total?: number
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

export interface ReviewDecisionHistory {
  id: string
  workspace_id: string
  review_item_id: string
  tax_event_id: string | null
  action: string
  actor: string
  previous_status: string | null
  new_status: string | null
  changed_fields: Record<string, { old: unknown; new: unknown }>
  note: string | null
  bulk_action_id: string | null
  created_at: string | null
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
  source?: string | null
  event_metadata?: Record<string, unknown> | null
  source_document?: {
    document_id: string
    original_filename: string
  } | null
  decision_history?: ReviewDecisionHistory[]
  explanation?: ExplanationSidecar | null
}

export interface ExplanationSidecar {
  explanation_id: string
  target_type: string
  target_id: string
  category: string
  plain_english_summary: string
  why_it_matters: string
  what_user_should_check: string
  evidence_expected: string[]
  confidence_level: 'low' | 'medium' | 'high'
  rule_version: string | null
  source: 'rule' | 'extraction' | 'user_entry' | 'review' | 'evidence_match' | string
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
  evidence_required_missing_count?: number
  evidence_required_partial_count?: number
  evidence_required_matched_count?: number
  evidence_recommended_missing_count?: number
  blocking_evidence_obligations?: EvidenceDiagnosticItem[]
  eligibility_preview?: {
    evidence_total?: number
    evidence_required_total: number
    evidence_required_blocking_total: number
    evidence_required_missing_total: number
    evidence_required_partial_total: number
    evidence_required_matched_total?: number
    evidence_recommended_missing_total?: number
    evidence_recommended_partial_total?: number
    evidence_recommended_matched_total?: number
    blocking_evidence_obligations: EvidenceDiagnosticItem[]
    would_block_export: boolean
  } | null
  evidence_export_status?: {
    would_block_export: boolean
    blocking_required_count: number
    missing_required_count: number
    partial_required_count: number
    blocking_evidence_obligations: EvidenceDiagnosticItem[]
    mode: 'soft_block'
    message: string
  }
  evidence_freshness?: EvidenceFreshness
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

// ── Recovery types ────────────────────────────────────────────────────────────

export type RecoverySafetyStatusValue = 'healthy' | 'stale' | 'missing' | 'failed'
export type RecoveryEncryptionMode = 'server_derived' | 'recovery_key_derived' | 'future_dual_wrapped'

export interface RecoverySafetyStatusData {
  status: RecoverySafetyStatusValue
  last_backup_at: string | null
  last_verified_at: string | null
  requires_backup_before_dangerous_action: boolean
  policy_window_hours: number
}

export interface RecoveryVerificationResult {
  status: 'pass' | 'fail' | string
  errors: string[]
  warnings: string[]
}

export interface RecoveryBackupData {
  backup_id: string
  status: string
  created_at: string | null
  filename: string | null
  path: string | null
  manifest_summary: Record<string, unknown>
  verification: RecoveryVerificationResult
}

export interface RecoveryVerifyBackupData {
  backup_id: string
  status: string
  manifest_summary: Record<string, unknown>
  verification: RecoveryVerificationResult
}

export interface RecoveryKeyVerificationData {
  status: string
  verified: boolean
  verified_at: string | null
}

export interface RecoveryRestorePreviewData {
  status: string
  preview_id: string | null
  backup_id: string
  workspace_id: string | null
  financial_year: string | null
  created_at: string | null
  encryption_mode: RecoveryEncryptionMode | string | null
  record_counts: Record<string, number>
  included_sections: string[]
  compatibility: Record<string, unknown>
  blockers: string[]
  warnings: string[]
  can_restore: boolean
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

export interface IncompleteInterviewQuestion {
  question_id: string
  question_label: string
  editable: boolean
}

export interface InterviewSummaryData {
  sections: SummarySection[]
  incomplete_questions?: IncompleteInterviewQuestion[]
}
