'use client'
import { useState } from 'react'
import type { ReviewItem } from '@/lib/api/types'
import ConfidenceBar from '@/components/shared/ConfidenceBar'
import StatusBadge from '@/components/shared/StatusBadge'
import type { BadgeStatus } from '@/components/shared/StatusBadge'
import InlineQuestion from './InlineQuestion'
import AmendForm from './AmendForm'
import AskClaudeDrawer from './AskClaudeDrawer'

function getBorderClass(item: ReviewItem): string {
  if (item.risk_level === 'high') return 'border-risk-high'
  if (item.status === 'confirmed') return 'border-ready'
  if (item.status === 'needs_agent_review') return 'border-agent'
  return 'border-review'
}

function getStatusBadge(item: ReviewItem): BadgeStatus {
  if (item.risk_level === 'high') return 'high_risk'
  if (item.status === 'confirmed') return 'confirmed'
  if (item.status === 'needs_agent_review') return 'needs_agent_review'
  return 'needs_user_review'
}

interface ReviewCardProps {
  item: ReviewItem
  onAction: (
    id: string,
    action: 'confirmed' | 'amended' | 'flagged' | 'skipped',
    payload: { amount?: number; category?: string; note?: string }
  ) => void
  onInlineAnswer: (
    itemId: string,
    questionId: string,
    answer: string,
    eventId: string
  ) => Promise<{ new_skill_pending: boolean }>
}

export default function ReviewCard({ item, onAction, onInlineAnswer }: ReviewCardProps) {
  const [showWhy, setShowWhy] = useState(false)
  const [showAmend, setShowAmend] = useState(false)
  const [showAsk, setShowAsk] = useState(false)
  const [confirmed, setConfirmed] = useState(item.status === 'confirmed')
  const [newSkillPending, setNewSkillPending] = useState(false)

  const borderClass = getBorderClass(item)
  const actionsLocked = !item.questions_complete
  const lockClass = actionsLocked ? 'opacity-50 pointer-events-none' : ''

  const displayAmount = item.amended_amount ?? item.amount
  const displayCategory = item.amended_category ?? item.category

  const d = item.date ? new Date(item.date) : null
  const displayDate =
    d && !isNaN(d.getTime())
      ? d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
      : '—'

  async function handleInlineAnswer(questionId: string, answer: string) {
    const res = await onInlineAnswer(item.id, questionId, answer, item.tax_event_id ?? item.id)
    if (res.new_skill_pending) setNewSkillPending(true)
  }

  function handleConfirm() {
    setConfirmed(true)
    onAction(item.id, 'confirmed', {})
  }

  return (
    <div className={`bg-surface border border-border border-l-4 ${borderClass} rounded-md p-4`}>
      {newSkillPending && (
        <div className="mb-3 rounded bg-agent-bg px-3 py-2 text-xs font-ui text-agent">
          New tax area unlocked — check Tax Journey for new questions.
        </div>
      )}

      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-ui font-medium text-text-body">{item.title ?? displayCategory}</p>
          <div className="flex items-center gap-3 mt-1">
            {displayAmount != null && (
              <span className="font-mono text-sm text-text-body">
                ${displayAmount.toLocaleString('en-AU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            )}
            <span className="text-xs font-ui text-text-muted">{displayDate}</span>
          </div>
        </div>
        <StatusBadge status={getStatusBadge(item)} />
      </div>

      {item.ai_reasoning && (
        <p className="mt-2 text-sm font-ui italic text-text-muted">{item.ai_reasoning}</p>
      )}

      {item.confidence != null && (
        <div className="mt-2">
          <ConfidenceBar confidence={item.confidence} />
        </div>
      )}

      {!item.questions_complete && item.inline_questions.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <InlineQuestion questions={item.inline_questions} onAnswer={handleInlineAnswer} />
        </div>
      )}

      {!confirmed ? (
        <div
          data-testid="action-buttons"
          className={`flex flex-wrap gap-2 mt-3 pt-3 border-t border-border ${lockClass}`}
        >
          <button
            type="button"
            onClick={handleConfirm}
            className="min-h-[44px] px-3 py-2 rounded text-sm font-ui font-medium bg-ready text-surface hover:opacity-90 transition-opacity"
          >
            Looks right
          </button>
          <button
            type="button"
            onClick={() => setShowAmend((v) => !v)}
            className="min-h-[44px] px-3 py-2 rounded text-sm font-ui font-medium border border-border text-text-body hover:bg-surface-raised transition-colors"
          >
            Change this
          </button>
          <button
            type="button"
            onClick={() => setShowAsk(true)}
            className="min-h-[44px] px-3 py-2 rounded text-sm font-ui font-medium border border-border text-text-body hover:bg-surface-raised transition-colors"
          >
            Ask Claude
          </button>
        </div>
      ) : (
        <p className="mt-3 pt-3 border-t border-border text-sm font-ui text-ready">
          Thanks for reviewing. We&apos;ve noted your input.
        </p>
      )}

      {showAmend && (
        <div className="mt-3 pt-3 border-t border-border">
          <AmendForm
            item={item}
            onSave={(amount, category, note) => {
              setShowAmend(false)
              setConfirmed(true)
              onAction(item.id, 'amended', { amount, category, note })
            }}
            onCancel={() => setShowAmend(false)}
          />
        </div>
      )}

      {item.ai_reasoning && (
        <div className="mt-2">
          <button
            type="button"
            onClick={() => setShowWhy((v) => !v)}
            className="text-xs font-ui text-text-muted hover:text-text-body transition-colors"
          >
            {showWhy ? 'Hide explanation ↑' : 'Why did Claude suggest this? ↓'}
          </button>
          {showWhy && (
            <div data-testid="why-section" className="mt-2 p-3 bg-surface-raised rounded text-xs font-ui text-text-muted">
              {item.ai_reasoning}
            </div>
          )}
        </div>
      )}

      {showAsk && (
        <AskClaudeDrawer
          itemId={item.id}
          itemTitle={item.title ?? displayCategory ?? 'this item'}
          onClose={() => setShowAsk(false)}
        />
      )}
    </div>
  )
}
