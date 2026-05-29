interface Props {
  completed: number
  total: number
}

export default function ProgressDots({ completed, total }: Props) {
  const safeTotal = Math.max(1, total)
  const clampedCompleted = Math.max(0, Math.min(completed, safeTotal))
  const renderTotal = Math.min(safeTotal, 12)
  const renderCompleted = Math.min(clampedCompleted, renderTotal)

  return (
    <div
      className="flex items-center gap-2"
      aria-label={`${clampedCompleted} of ${safeTotal} questions answered`}
    >
      {Array.from({ length: renderTotal }).map((_, i) => {
        const isDone = i < renderCompleted
        const isCurrent = i === renderCompleted
        return (
          <div
            key={i}
            data-testid="dot"
            className={[
              'rounded-full transition-all',
              isDone    ? 'w-2 h-2 bg-ready'  : '',
              isCurrent ? 'w-3 h-3 bg-accent' : '',
              !isDone && !isCurrent ? 'w-2 h-2 bg-border' : '',
            ].filter(Boolean).join(' ')}
          />
        )
      })}
    </div>
  )
}
