'use client'
import { useState } from 'react'
import type { InterviewQuestion } from '@/lib/api/types'

interface Props {
  question: InterviewQuestion
  onAnswer: (questionId: string, answer: string) => void
  onBack: () => void
  onSkip: (questionId: string) => void
  isSubmitting?: boolean
}

export default function QuestionCard({
  question, onAnswer, onBack, onSkip, isSubmitting = false,
}: Props) {
  const [whyOpen, setWhyOpen] = useState(false)

  return (
    <div className="space-y-6">
      <button
        type="button"
        onClick={onBack}
        disabled={isSubmitting}
        aria-label="Back"
        className="text-sm font-ui text-text-muted hover:text-text-body transition-colors disabled:opacity-50"
      >
        ← Back
      </button>

      <div className="space-y-2">
        <h2 className="font-display text-xl text-text-primary">{question.ask}</h2>
        {question.hint && (
          <p className="text-sm font-body text-text-muted">{question.hint}</p>
        )}
      </div>

      {question.options && (
        <ul className="space-y-3">
          {question.options.map((opt) => (
            <li key={opt}>
              <button
                type="button"
                onClick={() => onAnswer(question.id, opt)}
                disabled={isSubmitting}
                className="w-full py-4 px-4 text-left rounded-md bg-surface border border-border hover:border-accent text-text-body font-ui transition-colors disabled:opacity-50"
              >
                {opt}
              </button>
            </li>
          ))}
        </ul>
      )}

      {(question.type === 'text' || question.type === 'number') && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            const val = (new FormData(e.currentTarget).get('answer') as string) ?? ''
            if (val.trim()) onAnswer(question.id, val.trim())
          }}
          className="space-y-3"
        >
          <input
            name="answer"
            type={question.type === 'number' ? 'number' : 'text'}
            required
            disabled={isSubmitting}
            className="w-full py-3 px-4 rounded-md bg-surface border border-border focus:border-accent focus:outline-none text-text-body font-ui"
          />
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-3 rounded-md bg-accent text-surface font-ui font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            Continue
          </button>
        </form>
      )}

      <div className="flex items-start justify-between gap-4">
        <div>
          {question.why && (
            <div className="space-y-1">
              <button
                type="button"
                onClick={() => setWhyOpen((v) => !v)}
                aria-label="Why do we ask?"
                className="text-xs font-ui text-text-faint hover:text-text-muted transition-colors"
              >
                Why do we ask?
              </button>
              {whyOpen && (
                <p className="text-sm font-body text-text-muted">{question.why}</p>
              )}
            </div>
          )}
        </div>
        {!question.required && (
          <button
            type="button"
            onClick={() => onSkip(question.id)}
            disabled={isSubmitting}
            aria-label="Skip for now"
            className="text-sm font-ui text-text-faint hover:text-text-muted transition-colors whitespace-nowrap disabled:opacity-50"
          >
            Skip for now →
          </button>
        )}
      </div>
    </div>
  )
}
