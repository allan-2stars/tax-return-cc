interface ReadinessRingProps {
  percentage: number    // 0–100 (values outside range are displayed as-is but clamped for SVG)
  size?: number         // SVG size in px, default 200
  strokeWidth?: number  // ring thickness, default 12
}

export default function ReadinessRing({
  percentage,
  size = 200,
  strokeWidth = 12,
}: ReadinessRingProps) {
  const cx = size / 2
  const cy = size / 2
  const radius = (size - strokeWidth * 2) / 2
  const circumference = 2 * Math.PI * radius
  const clamped = Math.min(100, Math.max(0, percentage))
  const offset = circumference - (clamped / 100) * circumference

  return (
    <svg
      width={size}
      height={size}
      aria-label={`${percentage}% ready`}
      role="img"
    >
      {/* Background track */}
      <circle
        data-testid="ring-track"
        cx={cx}
        cy={cy}
        r={radius}
        fill="none"
        strokeWidth={strokeWidth}
        className="stroke-progress-track"
      />
      {/* Progress arc — rotated so 0° starts at top */}
      <circle
        data-testid="ring-progress"
        cx={cx}
        cy={cy}
        r={radius}
        fill="none"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        className="stroke-ready"
        strokeDasharray={`${circumference} ${circumference}`}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: 'stroke-dashoffset 600ms ease' }}
      />
      {/* Centre: percentage number */}
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="central"
        className="fill-ready font-mono text-3xl font-bold"
      >
        {percentage}%
      </text>
    </svg>
  )
}
