'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  downloadExport,
  generateExport,
  getEligibility,
  getExportHistory,
  getExportStatus,
} from '@/lib/api/export'
import type { ExportRecord } from '@/lib/api/types'
import EligibilityCard from '@/components/export/EligibilityCard'
import ExportHistoryCard from '@/components/export/ExportHistoryCard'
import Disclaimer from '@/components/shared/Disclaimer'
import EvidenceFreshnessBadge from '@/components/shared/EvidenceFreshnessBadge'
import type { EvidenceDiagnosticItem } from '@/lib/api/types'

function EvidenceDiagnosticsList({ items }: { items: EvidenceDiagnosticItem[] }) {
  if (items.length === 0) return null
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.id} className="rounded-md border border-border bg-surface-raised px-3 py-2 space-y-1">
          <p className="text-sm font-ui font-medium text-text-primary">{item.label}</p>
          {item.reason && <p className="text-sm font-ui text-text-muted">{item.reason}</p>}
          {item.explanation?.what_user_should_check && (
            <p className="text-sm font-ui text-text-body">
              <span className="text-text-muted">What to check: </span>
              {item.explanation.what_user_should_check}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

export default function ExportPage() {
  const qc = useQueryClient()
  const [password, setPassword] = useState('')
  const [activeExportId, setActiveExportId] = useState<string | null>(null)
  const [showGenerateForm, setShowGenerateForm] = useState(false)

  const { data: eligibility, isLoading: eligibilityLoading, isError: eligibilityError } = useQuery({
    queryKey: ['export-eligibility'],
    queryFn: () => getEligibility().then((r) => r.data.data),
  })

  const { data: exportStatus } = useQuery<ExportRecord>({
    queryKey: ['export-status', activeExportId],
    queryFn: () => getExportStatus(activeExportId!).then((r) => r.data.data),
    enabled: activeExportId !== null,
    refetchInterval: (query) =>
      query.state.data?.status === 'generating' ? 2000 : false,
  })

  const { data: history } = useQuery<ExportRecord[]>({
    queryKey: ['export-history'],
    queryFn: () => getExportHistory().then((r) => r.data.data),
  })

  const generateMutation = useMutation({
    mutationFn: (pw: string) => generateExport(pw),
    onSuccess: (response) => {
      setActiveExportId(response.data.data.export_id)
      setShowGenerateForm(false)
      qc.invalidateQueries({ queryKey: ['export-history'] })
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const pw = password
    setPassword('') // clear immediately — never linger in state
    if (!pw.trim()) return
    generateMutation.mutate(pw)
  }

  function handleRegenerate() {
    setActiveExportId(null)
    setShowGenerateForm(true)
  }

  const canExport = eligibility?.can_export ?? false
  const isGenerating = exportStatus?.status === 'generating'
  const isReady = exportStatus?.status === 'ready'
  const isFailed = exportStatus?.status === 'failed'
  const showForm = (canExport || showGenerateForm) && activeExportId === null
  const evidenceFreshnessWarning =
    eligibility?.evidence_freshness?.freshness_state === 'stale' ||
    eligibility?.evidence_freshness?.freshness_state === 'failed'

  if (eligibilityLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-text-muted">Loading…</p>
      </div>
    )
  }

  if (eligibilityError) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-risk-high">Unable to load export eligibility. Please refresh the page.</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">
          Export Review Pack
        </h1>
        <p className="text-sm font-ui text-text-muted mt-1">
          Generate an encrypted review package for your tax agent.
        </p>
      </div>

      {eligibility && (
        <EligibilityCard
          eligibility={eligibility}
          onGenerateAnyway={() => setShowGenerateForm(true)}
        />
      )}

      {eligibility && !eligibility.can_export && (
        <div className="rounded-lg border border-review bg-review-bg p-4 space-y-2">
          <p className="text-sm font-ui font-semibold text-text-primary">
            Export works best after the earlier steps are in place.
          </p>
          <p className="text-sm font-ui text-text-body">
            Finish your journey, review your items, and check evidence readiness before exporting.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link href="/journey" className="text-sm font-ui text-accent underline">
              Go to Journey
            </Link>
            <Link href="/review" className="text-sm font-ui text-accent underline">
              Go to Review
            </Link>
            <Link href="/readiness" className="text-sm font-ui text-accent underline">
              Review readiness
            </Link>
          </div>
        </div>
      )}

      {eligibility?.evidence_export_status && (
        <section
          className={`rounded-lg p-4 space-y-2 ${
            eligibility.evidence_export_status.would_block_export
              ? 'border border-review bg-review-bg'
              : 'border border-ready bg-ready-bg'
          }`}
        >
          <p className="text-sm font-ui font-semibold text-text-primary">Evidence Preview</p>
          <EvidenceFreshnessBadge freshness={eligibility.evidence_freshness} compact />
          {evidenceFreshnessWarning && (
            <p className="text-sm font-ui text-risk-high">
              Export preview may be using stale evidence status.
            </p>
          )}
          {eligibility.evidence_export_status.would_block_export && (
            <p className="text-sm font-ui text-text-body">
              Export is allowed, but evidence may be incomplete.
            </p>
          )}
          <p className="text-sm font-ui text-text-muted">
            {eligibility.evidence_export_status.message}
          </p>
          <p className="text-sm font-ui text-text-body">
            Required missing: {eligibility.evidence_required_missing_count ?? eligibility.evidence_export_status.missing_required_count}
            {' · '}
            Required partially matched: {eligibility.evidence_required_partial_count ?? eligibility.evidence_export_status.partial_required_count}
            {' · '}
            Required matched: {eligibility.evidence_required_matched_count ?? 0}
            {' · '}
            Recommended missing: {eligibility.evidence_recommended_missing_count ?? 0}
          </p>
          <EvidenceDiagnosticsList items={eligibility.evidence_export_status.blocking_evidence_obligations} />
          <a href="/readiness/checklist" className="text-sm font-ui text-accent underline">
            Review evidence checklist
          </a>
        </section>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="space-y-4 max-w-sm">
          <p className="text-sm font-ui text-text-muted">
            Your password is not stored — save it somewhere safe.
          </p>
          <div>
            <label
              htmlFor="export-password"
              className="text-sm font-ui text-text-body block mb-1"
            >
              Set a password for your review pack
            </label>
            <input
              id="export-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
              placeholder="Enter password"
              aria-label="Export password"
            />
          </div>
          <button
            type="submit"
            className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
            disabled={generateMutation.isPending}
          >
            Generate review pack
          </button>
        </form>
      )}

      {isGenerating && (
        <div
          className="flex items-center gap-3 py-4"
          data-testid="generating-spinner"
        >
          <div className="animate-spin w-5 h-5 border-2 border-accent border-t-transparent rounded-full" />
          <p className="text-sm font-ui text-text-muted">Generating your review pack…</p>
        </div>
      )}

      {isReady && exportStatus && (
        <div className="rounded-lg border border-ready bg-ready-bg p-4 space-y-2">
          <p className="text-sm font-ui font-semibold text-ready">
            Your review pack is ready
          </p>
          <button
            type="button"
            className="text-sm font-ui text-ready underline"
            onClick={() => downloadExport(exportStatus.id)}
          >
            Download now
          </button>
        </div>
      )}

      {isFailed && exportStatus && (
        <div className="rounded-lg border border-review bg-review-bg p-4 space-y-2">
          <p className="text-sm font-ui font-semibold text-text-primary">
            Export failed
          </p>
          <p className="text-sm font-ui text-text-muted">
            {exportStatus.error_message ?? 'Export failed. Please generate again.'}
          </p>
          <button
            type="button"
            className="text-sm font-ui text-accent underline"
            onClick={handleRegenerate}
          >
            Generate again
          </button>
        </div>
      )}

      {history && history.length > 0 && (
        <section>
          <h2 className="font-display text-base font-semibold text-text-primary mb-3">
            Export history
          </h2>
          <div className="space-y-3">
            {history.map((record) => (
              <ExportHistoryCard
                key={record.id}
                record={record}
                onDownload={downloadExport}
                onRegenerate={handleRegenerate}
              />
            ))}
          </div>
        </section>
      )}

      <Disclaimer />
    </div>
  )
}
