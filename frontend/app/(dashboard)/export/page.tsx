'use client'
import { useState } from 'react'
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

export default function ExportPage() {
  const qc = useQueryClient()
  const [password, setPassword] = useState('')
  const [activeExportId, setActiveExportId] = useState<string | null>(null)
  const [showGenerateForm, setShowGenerateForm] = useState(false)

  const { data: eligibility, isLoading: eligibilityLoading } = useQuery({
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
  const showForm = (canExport || showGenerateForm) && activeExportId === null

  if (eligibilityLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-text-muted">Loading…</p>
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
