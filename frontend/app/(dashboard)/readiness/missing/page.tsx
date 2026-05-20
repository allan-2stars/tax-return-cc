'use client'

import Link from 'next/link'
import MissingEvidenceList from '@/components/readiness/MissingEvidenceList'
import { useMissing } from '@/lib/hooks/useReadiness'
import useWorkspaceStore from '@/lib/stores/workspace.store'

function getFYEndLabel(fy: string): string {
  const endYear = parseInt(fy.split('-')[1]) + 2000
  return `30 June ${endYear}`
}

export default function MissingPage() {
  const { data, isLoading } = useMissing()
  const { financialYear } = useWorkspaceStore()

  if (isLoading || !data) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-text-muted">Loading missing items…</p>
      </div>
    )
  }

  const fyLabel = financialYear ? getFYEndLabel(financialYear) : '30 June'
  const totalMissing = data.available_now.length + data.available_after_fy.length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-semibold text-text-primary">
          Missing Evidence
        </h1>
        <Link href="/readiness" className="text-sm font-ui text-text-muted hover:text-text-body transition-colors">
          ← Back to readiness
        </Link>
      </div>

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
    </div>
  )
}
