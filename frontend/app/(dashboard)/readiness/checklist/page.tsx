'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import EvidenceChecklist from '@/components/readiness/EvidenceChecklist'
import EvidenceFreshnessBadge from '@/components/shared/EvidenceFreshnessBadge'
import { getEvidenceObligations, reconcileEvidence, updateEvidenceMatch } from '@/lib/api/evidence'
import { normalizeApiError } from '@/lib/api/errors'

export default function EvidenceChecklistPage() {
  const queryClient = useQueryClient()
  const [decisionError, setDecisionError] = useState<string | null>(null)
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null)
  const { data, isLoading, isError, dataUpdatedAt } = useQuery({
    queryKey: ['evidence', 'obligations'],
    queryFn: () => getEvidenceObligations().then((r) => r.data.data),
  })

  const reconcile = useMutation({
    mutationFn: reconcileEvidence,
    onMutate: () => {
      setRefreshMessage(null)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['evidence', 'obligations'] })
      setRefreshMessage('Checklist refreshed.')
    },
    onError: () => {
      setRefreshMessage('Unable to refresh evidence checklist. Try again.')
    },
  })
  const decideMatch = useMutation({
    mutationFn: ({ matchId, status }: { matchId: string; status: 'accepted' | 'rejected' }) =>
      updateEvidenceMatch(matchId, status),
    onSuccess: async () => {
      setDecisionError(null)
      await queryClient.invalidateQueries({ queryKey: ['evidence', 'obligations'] })
    },
    onError: (err: unknown) => {
      setDecisionError(normalizeApiError(err, 'Unable to update evidence match. Try again.').message)
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold text-text-primary">Evidence Checklist</h1>
          <p className="text-sm font-ui text-text-muted mt-1">
            Supporting Evidence = uploaded source documents. Review = extracted or manually added tax items.
          </p>
          {dataUpdatedAt > 0 && (
            <p className="text-xs font-ui text-text-muted mt-1">
              Last refreshed: {new Date(dataUpdatedAt).toLocaleString()}
            </p>
          )}
          <div className="mt-2">
            <EvidenceFreshnessBadge freshness={data?.freshness} />
          </div>
          {refreshMessage && (
            <p className={`text-xs font-ui mt-2 ${reconcile.isError ? 'text-risk-high' : 'text-ready'}`}>
              {refreshMessage}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => reconcile.mutate()}
          disabled={reconcile.isPending}
          className="px-3 py-2 rounded-md border border-border text-sm font-ui text-text-body hover:bg-surface"
        >
          {reconcile.isPending ? 'Reconciling...' : 'Refresh checklist'}
        </button>
      </div>

      <Link href="/evidence" className="text-sm font-ui text-accent hover:underline">
        Go to Supporting Evidence
      </Link>

      {decisionError && (
        <div role="alert" className="rounded-md border border-risk-high bg-risk-bg p-3 space-y-2">
          <p className="text-sm font-ui text-risk-high">{decisionError}</p>
          {decideMatch.variables && (
            <button
              type="button"
              onClick={() => decideMatch.mutate(decideMatch.variables!)}
              className="text-sm font-ui text-accent underline"
            >
              Try again
            </button>
          )}
        </div>
      )}

      {isLoading && <p className="text-sm font-ui text-text-muted">Loading checklist…</p>}
      {isError && <p className="text-sm font-ui text-risk-high">Unable to load checklist.</p>}
      {!isLoading && !isError && (
        <EvidenceChecklist
          obligations={data?.obligations ?? []}
          decidingMatchId={decideMatch.variables?.matchId ?? null}
          onDecideMatch={(matchId, status) => decideMatch.mutate({ matchId, status })}
        />
      )}
    </div>
  )
}
