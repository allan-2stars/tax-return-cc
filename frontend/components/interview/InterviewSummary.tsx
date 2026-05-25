'use client'
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getInterviewSummary, jumpToQuestion } from '@/lib/api/interview'

interface InterviewSummaryProps {
  onEdit: () => void
}

export default function InterviewSummary({ onEdit }: InterviewSummaryProps) {
  const queryClient = useQueryClient()
  const [jumping, setJumping] = useState<string | null>(null)
  const [editError, setEditError] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['interview', 'summary'],
    queryFn: () => getInterviewSummary().then((r) => r.data.data),
  })

  if (isLoading) {
    return <div className="font-ui text-sm text-text-muted">Loading summary…</div>
  }

  if (isError) {
    return <div className="font-ui text-sm text-risk-high">Failed to load summary.</div>
  }

  if (!data || data.sections.length === 0) {
    return null
  }

  async function handleEdit(questionId: string) {
    if (jumping) return
    setJumping(questionId)
    setEditError(null)
    try {
      await jumpToQuestion(questionId)
      queryClient.invalidateQueries({ queryKey: ['interview', 'session'] })
      onEdit()
    } catch {
      setEditError('Unable to edit that answer. Please try again.')
    } finally {
      setJumping(null)
    }
  }

  return (
    <div>
      <h2 className="font-display text-xl text-text-primary mb-4">Your answers</h2>

      {data.sections.map((section, sectionIndex) => (
        <div key={section.title}>
          {sectionIndex > 0 && <div className="border-t border-border" />}
          <p className="font-ui font-semibold text-sm text-text-muted uppercase tracking-wide mb-2 mt-4">
            {section.title}
          </p>
          <div>
            {section.answers.map((answer, answerIndex) => (
              <div
                key={answer.question_id}
                className={`flex items-center justify-between px-4 py-2 text-sm ${
                  answerIndex % 2 === 0 ? 'bg-canvas' : 'bg-surface-raised'
                }`}
              >
                <span className="font-ui text-text-body">{answer.question_label}</span>
                <span className="font-body text-text-muted">{answer.answer_label}</span>
                {answer.editable && (
                  <button
                    type="button"
                    onClick={() => handleEdit(answer.question_id)}
                    disabled={jumping !== null}
                    className="text-accent font-ui text-sm hover:text-accent-hover transition-colors"
                  >
                    Edit
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
      {editError && (
        <p role="alert" className="text-sm font-ui text-risk-high mt-2">{editError}</p>
      )}
    </div>
  )
}
