'use client'

import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import EvidenceChecklist from '@/components/readiness/EvidenceChecklist'
import { getEvidenceObligations, reconcileEvidence, updateEvidenceMatch } from '@/lib/api/evidence'

export default function EvidenceChecklistPage() {
  const queryClient = useQueryClient()
  const { data, isLoading, isError, dataUpdatedAt } = useQuery({
    queryKey: ['evidence', 'obligations'],
    queryFn: () => getEvidenceObligations().then((r) => r.data.data.obligations),
  })

  const reconcile = useMutation({
    mutationFn: reconcileEvidence,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['evidence', 'obligations'] })
    },
  })
  const decideMatch = useMutation({
    mutationFn: ({ matchId, status }: { matchId: string; status: 'accepted' | 'rejected' }) =>
      updateEvidenceMatch(matchId, status),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['evidence', 'obligations'] })
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
        </div>
        <button
          type="button"
          onClick={() => reconcile.mutate()}
          className="px-3 py-2 rounded-md border border-border text-sm font-ui text-text-body hover:bg-surface"
        >
          {reconcile.isPending ? 'Refreshing…' : 'Refresh checklist'}
        </button>
      </div>

      <Link href="/evidence" className="text-sm font-ui text-accent hover:underline">
        Go to Supporting Evidence
      </Link>

      {isLoading && <p className="text-sm font-ui text-text-muted">Loading checklist…</p>}
      {isError && <p className="text-sm font-ui text-risk-high">Unable to load checklist.</p>}
      {!isLoading && !isError && (
        <EvidenceChecklist
          obligations={data ?? []}
          decidingMatchId={decideMatch.variables?.matchId ?? null}
          onDecideMatch={(matchId, status) => decideMatch.mutate({ matchId, status })}
        />
      )}
    </div>
  )
}
