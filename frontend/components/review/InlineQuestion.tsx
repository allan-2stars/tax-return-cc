'use client'
import { useState } from 'react'
import type { ReviewItemQuestion } from '@/lib/api/types'

interface InlineQuestionProps {
  questions: ReviewItemQuestion[]
  onAnswer: (questionId: string, answer: string) => Promise<void>
}

export default function InlineQuestion({ questions, onAnswer }: InlineQuestionProps) {
  const [answeredIds, setAnsweredIds] = useState<Set<string>>(new Set())
  const [textValue, setTextValue] = useState('')
  const [pending, setPending] = useState(false)

  const nextQuestion = questions.find((q) => !answeredIds.has(q.id))

  if (!nextQuestion) return null

  async function submit(answer: string) {
    if (!answer.trim() || pending) return
    setPending(true)
    await onAnswer(nextQuestion!.id, answer)
    setAnsweredIds((prev) => new Set([...prev, nextQuestion!.id]))
    setTextValue('')
    setPending(false)
  }

  return (
    <div>
      <p className="text-sm font-ui font-medium text-text-body mb-2">{nextQuestion.ask}</p>

      {nextQuestion.type === 'text' || nextQuestion.type === 'number' ? (
        <div className="flex gap-2">
          <input
            type={nextQuestion.type === 'number' ? 'number' : 'text'}
            value={textValue}
            onChange={(e) => setTextValue(e.target.value)}
            disabled={pending}
            className="flex-1 border border-border rounded px-3 py-2 text-sm font-ui bg-surface text-text-body focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <button
            type="button"
            disabled={pending || !textValue.trim()}
            onClick={() => submit(textValue)}
            className="min-h-11 px-4 rounded text-sm font-ui font-medium bg-accent text-surface hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            Submit
          </button>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {(nextQuestion.options ?? []).map((opt) => (
            <button
              key={opt}
              type="button"
              disabled={pending}
              onClick={() => submit(opt)}
              className="min-h-14 px-4 py-2 rounded border border-border text-sm font-ui text-text-body hover:bg-surface-raised transition-colors disabled:opacity-50"
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
