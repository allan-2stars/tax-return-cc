'use client'

import Link from 'next/link'
import ReadinessRing from '@/components/readiness/ReadinessRing'
import SkillBreakdown from '@/components/readiness/SkillBreakdown'
import Disclaimer from '@/components/shared/Disclaimer'
import { useReadiness } from '@/lib/hooks/useReadiness'
import useWorkspaceStore from '@/lib/stores/workspace.store'
import { getFYEndLabel, isFYActive } from '@/lib/utils/fy'

export default function ReadinessPage() {
  const { data, isLoading, isError } = useReadiness()
  const { financialYear } = useWorkspaceStore()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-text-muted">Loading your tax readiness…</p>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-risk-high">
          Unable to load tax readiness. Please try refreshing the page.
        </p>
      </div>
    )
  }

  const fyLabel = financialYear ? getFYEndLabel(financialYear) : '30 June'
  const fyActive = financialYear ? isFYActive(financialYear) : false

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">
          Tax Readiness
        </h1>
        {data.is_stale && (
          <p className="mt-1 text-xs font-ui text-text-muted flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-review animate-pulse" />
            Updating…
          </p>
        )}
      </div>

      {/* Readiness ring + sub-indicators */}
      <div className="bg-surface rounded-lg shadow-sm p-6 flex flex-col items-center gap-6">
        <ReadinessRing percentage={data.percentage} />

        {/* State messages */}
        {data.percentage === 0 && (
          <p className="text-sm font-ui text-text-muted text-center">
            Upload your first document to get started
          </p>
        )}
        {data.percentage === 100 && (
          <p className="text-sm font-ui text-ready font-medium text-center">
            Your tax review package is ready
          </p>
        )}

        {/* Sub-indicators */}
        <div className="w-full grid grid-cols-1 gap-2">
          {data.review_items_count > 0 && (
            <p className="text-sm font-ui text-review">
              🟡 {data.review_items_count} item{data.review_items_count !== 1 ? 's' : ''} need your review
            </p>
          )}
          {data.agent_items_count > 0 && (
            <p className="text-sm font-ui text-agent">
              🔴 {data.agent_items_count} item{data.agent_items_count !== 1 ? 's' : ''} need a tax agent
            </p>
          )}
          {data.missing_items_count > 0 && (
            <Link href="/readiness/missing" className="text-sm font-ui text-text-muted hover:text-text-body transition-colors">
              ⬜ {data.missing_items_count} piece{data.missing_items_count !== 1 ? 's' : ''} of evidence still missing →
            </Link>
          )}
        </div>

        {/* CTA */}
        <Link
          href="/journey"
          className="inline-block px-6 py-3 rounded-md bg-accent hover:bg-accent-hover text-white font-ui font-medium text-sm transition-colors"
        >
          Continue your tax journey →
        </Link>
      </div>

      {/* Per-skill breakdown */}
      {data.breakdown.length > 0 && (
        <div className="bg-surface rounded-lg shadow-sm p-6">
          <SkillBreakdown breakdown={data.breakdown} />
        </div>
      )}

      {/* FY-aware banner */}
      {fyActive && data.missing_items_count > 0 && (
        <div className="bg-review-bg rounded-md px-4 py-3">
          <p className="text-sm font-ui text-review">
            Some evidence types become available after {fyLabel}. We&apos;ll remind you when the financial year ends.
          </p>
        </div>
      )}

      <Disclaimer />
    </div>
  )
}
