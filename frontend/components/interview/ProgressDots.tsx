interface Props {
  completed: number
  total: number
}

export default function ProgressDots({ completed, total }: Props) {
  return (
    <div
      className="flex items-center gap-2"
      aria-label={`${completed} of ${total} questions answered`}
    >
      {Array.from({ length: total }).map((_, i) => {
        const isDone = i < completed
        const isCurrent = i === completed
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
