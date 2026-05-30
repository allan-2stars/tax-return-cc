import client from './client'
import type { ApiResponse, EvidenceObligation } from './types'

export interface ReconcileEvidenceData {
  status: string
  obligations_count: number
  telemetry?: {
    financial_year?: string
    reconcile_duration_ms?: number
    obligations_created?: number
    matches_created?: number
    reconcile_failures?: number
    current_rule_version?: string
    obligations_by_rule_version?: Record<string, number>
  }
  freshness?: {
    evidence_reconciled_at: string | null
    evidence_reconcile_status: string
  }
}

export const getEvidenceObligations = () =>
  client.get<
    ApiResponse<{
      obligations: EvidenceObligation[]
      freshness?: {
        evidence_reconciled_at: string | null
        evidence_reconcile_status: string
      }
    }>
  >('/api/v1/evidence/obligations')

export const reconcileEvidence = () =>
  client.post<ApiResponse<ReconcileEvidenceData>>('/api/v1/evidence/reconcile')

export const updateEvidenceMatch = (matchId: string, status: 'accepted' | 'rejected') =>
  client.patch<ApiResponse<{ match: { id: string; status: string }; obligation: { id: string; status: string } }>>(
    `/api/v1/evidence/matches/${matchId}`,
    { status }
  )
