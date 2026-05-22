import type { ReviewItemQuestion } from '@/lib/api/types'

interface InlineQuestionProps {
  questions: ReviewItemQuestion[]
  onAnswer: (questionId: string, answer: string) => Promise<void>
}

export default function InlineQuestion({ questions, onAnswer }: InlineQuestionProps) {
  if (!questions[0]) return null
  const q = questions[0]
  return (
    <div data-testid="inline-question">
      <p>{q.ask}</p>
      {(q.options ?? []).map((opt) => (
        <button key={opt} type="button" onClick={() => onAnswer(q.id, opt)}>{opt}</button>
      ))}
    </div>
  )
}
