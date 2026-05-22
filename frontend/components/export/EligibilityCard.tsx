import type { ExportEligibility } from '@/lib/api/types'

interface Props {
  eligibility: ExportEligibility
  onGenerateAnyway: () => void
}

export default function EligibilityCard({ eligibility, onGenerateAnyway }: Props) {
  const isBlocked = eligibility.blocking_reasons.length > 0
  const hasWarnings = eligibility.warnings.length > 0

  return (
    <div className="rounded-lg border border-border bg-surface p-4 space-y-4">
      {isBlocked && (
        <div className="space-y-2">
          <p className="text-sm font-ui font-semibold text-risk-high">Cannot export yet</p>
          <ul className="space-y-1">
            {eligibility.blocking_reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-2 text-sm font-ui text-text-body">
                <span className="text-risk-high mt-0.5">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {hasWarnings && (
        <div className="space-y-2">
          <p className="text-sm font-ui font-semibold text-review">
            {isBlocked ? 'Warnings' : 'Before you export'}
          </p>
          <ul className="space-y-1">
            {eligibility.warnings.map((w, i) => (
              <li key={i} className="flex items-start gap-2 text-sm font-ui text-text-body">
                <span className="text-review mt-0.5">•</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
          {!isBlocked && (
            <button
              className="text-sm font-ui text-accent underline mt-2"
              onClick={onGenerateAnyway}
            >
              Generate anyway
            </button>
          )}
        </div>
      )}
      {!isBlocked && !hasWarnings && (
        <p className="text-sm font-ui text-ready">Ready to export.</p>
      )}
    </div>
  )
}
