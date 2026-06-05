'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import MissingEvidenceList from '@/components/readiness/MissingEvidenceList'
import Disclaimer from '@/components/shared/Disclaimer'
import { getSession } from '@/lib/api/interview'
import { useMissing } from '@/lib/hooks/useReadiness'
import useWorkspaceStore from '@/lib/stores/workspace.store'
import { getFYEndLabel } from '@/lib/utils/fy'

export default function MissingPage() {
  const { data, isLoading, isError } = useMissing()
  const { data: interviewSession } = useQuery({
    queryKey: ['interview', 'session'],
    queryFn: () => getSession().then((r) => r.data.data),
  })
  const { financialYear } = useWorkspaceStore()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-text-muted">Loading missing items…</p>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-risk-high">
          Unable to load missing items. Please try refreshing the page.
        </p>
      </div>
    )
  }

  const fyLabel = financialYear ? getFYEndLabel(financialYear) : '30 June'
  const totalMissing = data.available_now.length + data.available_after_fy.length

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="space-y-2">
          <h1 className="font-display text-2xl font-semibold text-text-primary">
            Missing Evidence
          </h1>
          <p className="max-w-2xl text-sm font-ui text-text-muted">
            This list is based on your current tax journey answers and reviewed tax events.
          </p>
          <p className="max-w-2xl text-sm font-ui text-text-muted">
            If you skipped questions, more evidence may be required after you answer them.
          </p>
        </div>
        <div className="flex flex-col gap-3 md:items-end">
          <Link
            href="/evidence"
            className="inline-block rounded-md bg-accent px-5 py-3 text-sm font-ui font-medium text-white transition-colors hover:bg-accent-hover"
          >
            Upload evidence
          </Link>
          <Link href="/readiness" className="text-sm font-ui text-text-muted hover:text-text-body transition-colors">
            ← Back to readiness
          </Link>
        </div>
      </div>

      {interviewSession?.has_incomplete_questions && (
        <div className="rounded-md border border-review bg-review-bg px-4 py-3">
          <p className="text-sm font-ui text-text-body">
            Some journey answers are still skipped or incomplete, so more evidence requirements may appear later.
          </p>
          <Link href="/journey" className="mt-2 inline-block text-sm font-ui text-accent hover:underline">
            Review skipped journey answers
          </Link>
        </div>
      )}

      {totalMissing === 0 ? (
        <div className="bg-ready-bg rounded-lg p-8 text-center">
          <p className="text-sm font-ui text-ready font-medium">
            Nothing missing — you&apos;ve provided all available evidence.
          </p>
        </div>
      ) : (
        <MissingEvidenceList
          availableNow={data.available_now}
          availableAfterFY={data.available_after_fy}
          fyEndLabel={fyLabel}
        />
      )}

      <Disclaimer />
    </div>
  )
}
