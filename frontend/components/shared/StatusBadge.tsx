type BadgeStatus =
  | 'confirmed'
  | 'needs_user_review'
  | 'needs_agent_review'
  | 'high_risk'
  | 'out_of_scope'
  | 'missing'
  | 'duplicate'

const STATUS_CONFIG: Record<BadgeStatus, { label: string; classes: string }> = {
  confirmed:          { label: 'Ready',              classes: 'text-ready bg-ready-bg' },
  needs_user_review:  { label: 'Needs your look',    classes: 'text-review bg-review-bg' },
  needs_agent_review: { label: 'Agent review',       classes: 'text-agent bg-agent-bg' },
  high_risk:          { label: 'Flag to review',     classes: 'text-risk-high bg-risk-bg' },
  out_of_scope:       { label: 'Specialist area',    classes: 'text-agent bg-agent-bg' },
  missing:            { label: 'Still needed',       classes: 'text-text-muted bg-surface-raised' },
  duplicate:          { label: 'Possible duplicate', classes: 'text-review bg-review-bg' },
}

export type { BadgeStatus }

interface StatusBadgeProps {
  status: BadgeStatus
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.missing
  return (
    <span className={`inline-block rounded-full px-2 py-1 text-xs font-ui font-medium ${config.classes}`}>
      {config.label}
    </span>
  )
}
