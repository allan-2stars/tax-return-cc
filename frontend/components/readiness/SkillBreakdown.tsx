'use client'

import { useState } from 'react'
import type { SkillBreakdownItem } from '@/lib/api/types'

const SKILL_LABELS: Record<string, string> = {
  employee_tax_au: 'Employee Tax',
  wfh_skill:       'Work From Home',
  investment_skill:'Investments',
  crypto_skill:    'Crypto',
}

interface SkillBreakdownProps {
  breakdown: SkillBreakdownItem[]
}

export default function SkillBreakdown({ breakdown }: SkillBreakdownProps) {
  const [expanded, setExpanded] = useState(true)
  const allZero = breakdown.every((item) => item.percentage === 0)

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-2 text-sm font-ui font-medium text-text-body hover:text-text-primary transition-colors"
        aria-expanded={expanded}
      >
        Tax areas checked
        <span className="text-text-faint text-xs">{expanded ? '▴' : '▾'}</span>
      </button>

      {expanded && breakdown.length > 0 && (
        <div className="mt-3 space-y-3">
          <p className="text-xs font-ui text-text-muted">
            Progress for each tax area reflects confirmed evidence and review progress.
          </p>
          {allZero && (
            <p className="text-sm font-ui text-text-muted">
              No tax areas have evidence confirmed yet.
            </p>
          )}
          <ul className="space-y-2">
            {breakdown.map((item) => (
              <li key={item.skill_id} className="flex items-center gap-3">
                <span className="text-sm font-ui text-text-muted flex-1 min-w-0 truncate">
                  {SKILL_LABELS[item.skill_id] ?? item.skill_id}
                </span>
                <div className="flex-1 h-1 bg-progress-track rounded-full overflow-hidden">
                  <div
                    className="h-full bg-progress-fill rounded-full"
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-text-muted shrink-0">
                  {item.percentage}%
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
