interface ConfidenceBarProps {
  confidence: number  // 0.0–1.0
}

interface ConfidenceConfig {
  label: string
  fillClass: string
  widthPercent: number
}

function getConfig(confidence: number): ConfidenceConfig {
  if (confidence >= 0.90) return { label: 'High confidence', fillClass: 'bg-ready',      widthPercent: 100 }
  if (confidence >= 0.70) return { label: 'Moderate',        fillClass: 'bg-text-muted', widthPercent: 70  }
  if (confidence >= 0.50) return { label: 'Uncertain',       fillClass: 'bg-review',     widthPercent: 50  }
  return                         { label: 'Needs review',    fillClass: 'bg-agent',      widthPercent: 25  }
}

export default function ConfidenceBar({ confidence }: ConfidenceBarProps) {
  const { label, fillClass, widthPercent } = getConfig(confidence)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-progress-track rounded-full overflow-hidden">
        <div
          data-testid="confidence-fill"
          className={`h-full rounded-full ${fillClass}`}
          style={{ width: `${widthPercent}%` }}
        />
      </div>
      <span className="text-xs font-ui text-text-muted whitespace-nowrap">{label}</span>
    </div>
  )
}
