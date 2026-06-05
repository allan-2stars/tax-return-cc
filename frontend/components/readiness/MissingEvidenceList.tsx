'use client'

import { useState } from 'react'
import type { MissingItem } from '@/lib/api/types'

interface MissingEvidenceListProps {
  availableNow: MissingItem[]
  availableAfterFY: MissingItem[]
  fyEndLabel: string  // e.g., "30 June 2025"
}

function WeightPill({ weight }: { weight: number }) {
  const label = weight >= 2 ? 'Usually required' : 'Recommended'
  const classes = weight >= 2 ? 'text-review bg-review-bg' : 'text-text-muted bg-surface-raised'
  return (
    <span className={`inline-block rounded-full px-2 py-1 text-xs font-ui ${classes}`}>
      {label}
    </span>
  )
}

function MissingItemRow({
  item,
  onSkip,
}: {
  item: MissingItem
  onSkip: (id: string) => void
}) {
  return (
    <li className="flex items-start justify-between gap-4 py-3 border-b border-border last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-ui text-text-body">{item.display}</span>
          <WeightPill weight={item.weight} />
        </div>
        {item.how_to_get && (
          <p className="mt-1 text-xs font-ui text-text-muted">{item.how_to_get}</p>
        )}
      </div>
      <button
        type="button"
        onClick={() => onSkip(item.requirement_id)}
        className="shrink-0 text-xs font-ui text-text-faint hover:text-text-muted transition-colors"
      >
        I&apos;ll provide this later
      </button>
    </li>
  )
}

export default function MissingEvidenceList({
  availableNow,
  availableAfterFY,
  fyEndLabel,
}: MissingEvidenceListProps) {
  const [skipped, setSkipped] = useState<Set<string>>(new Set())

  const skip = (id: string) =>
    setSkipped((prev) => new Set([...prev, id]))

  const visibleNow = availableNow.filter((i) => !skipped.has(i.requirement_id))
  const visibleAfterFY = availableAfterFY.filter((i) => !skipped.has(i.requirement_id))
  const hasUsuallyRequiredItems = [...visibleNow, ...visibleAfterFY].some((item) => item.weight >= 2)

  return (
    <div className="space-y-6">
      {hasUsuallyRequiredItems && (
        <div className="rounded-md border border-review bg-review-bg px-4 py-3">
          <p className="text-sm font-ui text-text-body">
            Required evidence left for later may keep readiness blocked and appear in export warnings.
          </p>
        </div>
      )}

      {visibleNow.length > 0 && (
        <section>
          <h3 className="text-sm font-ui font-medium text-text-muted uppercase tracking-wide mb-2">
            Available now
          </h3>
          <ul>
            {visibleNow.map((item) => (
              <MissingItemRow key={item.requirement_id} item={item} onSkip={skip} />
            ))}
          </ul>
        </section>
      )}

      {visibleAfterFY.length > 0 && (
        <section>
          <h3 className="text-sm font-ui font-medium text-text-muted uppercase tracking-wide mb-2">
            Available after {fyEndLabel}
          </h3>
          <ul>
            {visibleAfterFY.map((item) => (
              <MissingItemRow key={item.requirement_id} item={item} onSkip={skip} />
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
