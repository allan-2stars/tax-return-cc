'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import ReadinessRing from '@/components/readiness/ReadinessRing'
import SkillBreakdown from '@/components/readiness/SkillBreakdown'
import TaxEstimate from '@/components/readiness/TaxEstimate'
import Disclaimer from '@/components/shared/Disclaimer'
import { useReadiness } from '@/lib/hooks/useReadiness'
import { getEstimatorSummary } from '@/lib/api/estimator'
import { getSession } from '@/lib/api/interview'
import useWorkspaceStore from '@/lib/stores/workspace.store'
import { getFYEndLabel, isFYActive } from '@/lib/utils/fy'

function readinessStateClasses(state: 'blocked' | 'warning' | 'ready') {
  if (state === 'blocked') return 'border-risk-high bg-review-bg text-risk-high'
  if (state === 'warning') return 'border-review bg-review-bg text-review'
  return 'border-ready bg-ready-bg text-ready'
}
export default function ReadinessPage() {
  const { data, isLoading, isError, recalcError } = useReadiness()
  const { data: estimate, isLoading: estimateLoading } = useQuery({
    queryKey: ['tax-estimate'],
    queryFn: () => getEstimatorSummary().then((r) => r.data.data),
  })
  const { data: interviewSession } = useQuery({
    queryKey: ['interview', 'session'],
    queryFn: () => getSession().then((r) => r.data.data),
  })
  const { financialYear } = useWorkspaceStore()

  if (isLoading) {
    return (
      <div className="space-y-8 animate-pulse" aria-label="Loading">
        <div className="h-8 w-48 bg-surface rounded" />
        <div className="bg-surface rounded-lg shadow-sm p-6 flex flex-col items-center gap-6">
          <div className="w-40 h-40 rounded-full bg-border" />
          <div className="w-full space-y-2">
            <div className="h-4 bg-border rounded w-3/4" />
            <div className="h-4 bg-border rounded w-1/2" />
          </div>
        </div>
        <div className="bg-surface rounded-lg shadow-sm p-6 space-y-3">
          <div className="h-4 bg-border rounded w-1/3" />
          <div className="h-3 bg-border rounded" />
          <div className="h-3 bg-border rounded w-5/6" />
        </div>
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
          <div className="mt-1 space-y-1">
            <p className="text-xs font-ui text-text-muted flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full bg-review animate-pulse" />
              Updating…
            </p>
            {recalcError && <p className="text-xs font-ui text-risk-high">{recalcError}</p>}
          </div>
        )}
      </div>

      {/* Readiness ring + sub-indicators */}
      <div className="bg-surface rounded-lg shadow-sm p-6 flex flex-col items-center gap-6">
        {interviewSession?.has_incomplete_questions && (
          <div className="w-full rounded-md border border-review bg-review-bg px-4 py-3">
            <p className="text-sm font-ui text-text-body">
              Complete your Tax Journey before final export.
            </p>
          </div>
        )}
        <ReadinessRing percentage={data.percentage} />
        <p className="text-xs font-ui text-text-muted">Overall preparation score</p>

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
          {!data.readiness_2_0 && (
            <Link href="/readiness/checklist" className="text-sm font-ui text-text-muted hover:text-text-body transition-colors">
              View evidence checklist →
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

      {data.readiness_2_0 && (
        <div className="bg-surface rounded-lg shadow-sm p-6 space-y-4">
          <h2 className="font-ui text-sm font-semibold text-text-primary">Readiness dimensions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className={`rounded-md border p-3 space-y-2 ${readinessStateClasses(data.readiness_2_0.journey.state)}`}>
              <p className="text-sm font-ui font-semibold text-text-primary">Journey readiness</p>
              <p className="text-xs font-ui">State: {data.readiness_2_0.journey.state}</p>
              <p className="text-xs font-ui">Required blockers: {data.readiness_2_0.journey.required_blockers_count}</p>
              <p className="text-xs font-ui text-text-muted">Complete required journey questions to proceed cleanly.</p>
              <Link href="/journey" className="text-xs font-ui text-accent hover:underline">Go to Journey</Link>
            </div>
            <div className={`rounded-md border p-3 space-y-2 ${readinessStateClasses(data.readiness_2_0.review.state)}`}>
              <p className="text-sm font-ui font-semibold text-text-primary">Review readiness</p>
              <p className="text-xs font-ui">State: {data.readiness_2_0.review.state}</p>
              <p className="text-xs font-ui">Unconfirmed: {data.readiness_2_0.review.unconfirmed_total}</p>
              <p className="text-xs font-ui">Needs agent review: {data.readiness_2_0.review.needs_agent_review_count}</p>
              <p className="text-xs font-ui text-text-muted">Resolve review items before final export submission.</p>
              <Link href="/review" className="text-xs font-ui text-accent hover:underline">Go to Review</Link>
            </div>
            <div className={`rounded-md border p-3 space-y-2 ${readinessStateClasses(data.readiness_2_0.evidence.state)}`}>
              <p className="text-sm font-ui font-semibold text-text-primary">Evidence readiness</p>
              <p className="text-xs font-ui">State: {data.readiness_2_0.evidence.state}</p>
              <p className="text-xs font-ui">Required missing: {data.readiness_2_0.evidence.required_missing_count}</p>
              <p className="text-xs font-ui">Required partial: {data.readiness_2_0.evidence.required_partial_count}</p>
              <p className="text-xs font-ui">Required matched: {data.readiness_2_0.evidence.required_matched_count}</p>
              <p className="text-xs font-ui text-text-muted">Confirm required evidence matches and resolve missing items.</p>
              <Link href="/readiness/checklist" className="text-xs font-ui text-accent hover:underline">Open checklist</Link>
            </div>
          </div>

          {(data.readiness_2_0.blocking_reasons.length > 0 || data.readiness_2_0.warnings.length > 0) && (
            <div className="space-y-2">
              {data.readiness_2_0.blocking_reasons.length > 0 && (
                <div className="rounded-md border border-risk-high bg-review-bg px-3 py-2">
                  <p className="text-xs font-ui font-semibold text-text-primary">
                    Blockers (must resolve before considered ready)
                  </p>
                  {data.readiness_2_0.blocking_reasons.map((reason) => (
                    <p key={reason} className="text-xs font-ui text-risk-high">{reason}</p>
                  ))}
                </div>
              )}
              {data.readiness_2_0.warnings.length > 0 && (
                <div className="rounded-md border border-review bg-review-bg px-3 py-2">
                  <p className="text-xs font-ui font-semibold text-text-primary">
                    Warnings (should review before export)
                  </p>
                  {data.readiness_2_0.warnings.map((warning) => (
                    <p key={warning} className="text-xs font-ui text-review">{warning}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Per-skill breakdown */}
      {data.breakdown.length > 0 && (
        <div className="bg-surface rounded-lg shadow-sm p-6">
          <SkillBreakdown breakdown={data.breakdown} />
        </div>
      )}

      {!data.readiness_2_0 && data.evidence_obligation_summary && (
        <div className="bg-surface rounded-lg shadow-sm p-6 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-ui text-sm font-semibold text-text-primary">Evidence readiness</h2>
            <Link href="/readiness/checklist" className="text-xs font-ui text-accent hover:underline">
              Open checklist
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm font-ui">
            <p className="text-risk-high">
              Required missing: {data.evidence_obligation_summary.required_missing}
            </p>
            <p className="text-review">
              Required partial: {data.evidence_obligation_summary.required_partially_matched}
            </p>
            <p className="text-ready">
              Required matched: {data.evidence_obligation_summary.required_matched}
            </p>
          </div>
          <p className="text-xs font-ui text-text-muted">
            Evidence readiness is shown separately from your overall tax readiness score.
          </p>
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

      {/* Tax estimate */}
      <TaxEstimate data={estimate} isLoading={estimateLoading} />

      <Disclaimer />
    </div>
  )
}
