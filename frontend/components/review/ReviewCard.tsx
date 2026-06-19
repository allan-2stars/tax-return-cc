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

function formatHistoryValue(value: unknown): string {
  if (value == null || value === '') return 'none'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function formatHistoryDate(value: string | null): string {
  if (!value) return 'Unknown time'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return 'Unknown time'
  return parsed.toLocaleString('en-AU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatMoney(value: unknown): string | null {
  if (typeof value !== 'number' || Number.isNaN(value)) return null
  return `$${value.toLocaleString('en-AU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatPreviewDate(value: unknown): string | null {
  if (typeof value !== 'string' || !value) return null
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
}

function formatUnits(value: unknown, suffix = 'units'): string | null {
  if (typeof value !== 'number' || Number.isNaN(value)) return null
  return `${value.toLocaleString('en-AU')} ${suffix}`
}

function getSourceBadgeLabel(source: string | null | undefined): string | null {
  if (source === 'document_extracted') return 'Document Extracted'
  if (source === 'manual_entry') return 'Manual Entry'
  return null
}

function getExtractionConfidenceLabel(confidence: number | null): string | null {
  if (confidence == null) return null
  if (confidence >= 0.9) return 'High'
  if (confidence >= 0.7) return 'Medium'
  return 'Low'
}

function getInvestmentPreview(item: ReviewItem): string[] {
  const metadata = item.event_metadata ?? {}
  const lines: string[] = []

  if (item.category === 'shares_acquisition') {
    if (typeof metadata.stock_code === 'string' && metadata.stock_code) lines.push(metadata.stock_code)
    if (typeof metadata.exchange === 'string' && metadata.exchange) lines.push(metadata.exchange)
    const units = formatUnits(metadata.units)
    if (units) lines.push(units)
    const pricePerUnit = formatMoney(metadata.price_per_unit)
    if (pricePerUnit) lines.push(`${pricePerUnit} each`)
    const brokerage = formatMoney(metadata.brokerage_fee)
    if (brokerage) lines.push(`Brokerage ${brokerage}`)
    return lines
  }

  if (
    item.category === 'capital_gain_candidate' ||
    item.category === 'capital_gain' ||
    item.category === 'capital_loss'
  ) {
    if (typeof metadata.stock_code === 'string' && metadata.stock_code) lines.push(metadata.stock_code)
    const units = formatUnits(metadata.units, 'units sold')
    if (units) lines.push(units)
    const pricePerUnit = formatMoney(metadata.price_per_unit)
    if (pricePerUnit) lines.push(`${pricePerUnit} each`)
    const brokerage = formatMoney(metadata.brokerage_fee)
    if (brokerage) lines.push(`Brokerage ${brokerage}`)
    return lines
  }

  if (item.category === 'dividend') {
    const dividendAmount = formatMoney(metadata.dividend_amount)
    if (dividendAmount) lines.push(`Dividend ${dividendAmount}`)
    const franking = formatMoney(metadata.franking_credits)
    if (franking) lines.push(`Franking ${franking}`)
    const paymentDate = formatPreviewDate(metadata.payment_date)
    if (paymentDate) lines.push(`Payment ${paymentDate}`)
    return lines
  }

  if (item.category === 'managed_fund_distribution') {
    const distribution = formatMoney(metadata.distribution_amount)
    if (distribution) lines.push(`Distribution ${distribution}`)
    const capitalGains = formatMoney(metadata.capital_gains_component)
    if (capitalGains) lines.push(`Capital gains component ${capitalGains}`)
    const foreignIncome = formatMoney(metadata.foreign_income_component)
    if (foreignIncome) lines.push(`Foreign income component ${foreignIncome}`)
    return lines
  }

  if (item.category === 'share_annual_summary') {
    const purchases = formatMoney(metadata.total_purchase_value)
    if (purchases) lines.push(`Purchases ${purchases}`)
    const sales = formatMoney(metadata.total_sale_value)
    if (sales) lines.push(`Sales ${sales}`)
    const dividends = formatMoney(metadata.total_dividend_income)
    if (dividends) lines.push(`Dividends ${dividends}`)
    const brokerage = formatMoney(metadata.total_brokerage_fees)
    if (brokerage) lines.push(`Brokerage ${brokerage}`)
    return lines
  }

  return lines
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
  onUndo?: (id: string) => void
  onUndoBulk?: (bulkActionId: string) => void
}

export default function ReviewCard({ item, onAction, onInlineAnswer, onUndo, onUndoBulk }: ReviewCardProps) {
  const [showWhy, setShowWhy] = useState(false)
  const [showExplanation, setShowExplanation] = useState(false)
  const [showAmend, setShowAmend] = useState(false)
  const [showAsk, setShowAsk] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [confirmed, setConfirmed] = useState(item.status === 'confirmed')
  const [newSkillPending, setNewSkillPending] = useState(false)

  const borderClass = getBorderClass(item)
  const lockClass = !item.questions_complete ? 'opacity-50 pointer-events-none' : ''

  const displayAmount = item.amended_amount ?? item.amount
  const displayCategory = item.amended_category ?? item.category
  const decisionHistory = item.decision_history ?? []
  const latestHistory = decisionHistory[0]
  const canUndoLatest = latestHistory?.action === 'confirmed' || latestHistory?.action === 'amended'
  const sourceBadgeLabel = getSourceBadgeLabel(item.source)
  const extractionConfidenceLabel =
    item.source === 'document_extracted' ? getExtractionConfidenceLabel(item.confidence) : null
  const investmentPreview = item.source === 'document_extracted' ? getInvestmentPreview(item) : []

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
    setShowAmend(false)
    onAction(item.id, 'confirmed', {})
  }

  function handleUndo() {
    if (latestHistory?.bulk_action_id && onUndoBulk) {
      onUndoBulk(latestHistory.bulk_action_id)
      return
    }
    onUndo?.(item.id)
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

      {sourceBadgeLabel && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-accent-soft px-2 py-1 text-xs font-ui text-accent">
            {sourceBadgeLabel}
          </span>
          {extractionConfidenceLabel && (
            <span className="text-xs font-ui text-text-muted">
              Extraction confidence: {extractionConfidenceLabel}
            </span>
          )}
        </div>
      )}

      {item.source === 'document_extracted' && item.source_document && (
        <div className="mt-3 rounded bg-surface-raised p-3 text-xs font-ui text-text-muted">
          <p>
            <span className="text-text-body">Source document:</span>{' '}
            {item.source_document.original_filename}
          </p>
          <a
            href={`/api/v1/documents/${item.source_document.document_id}/file`}
            className="mt-1 inline-block text-accent underline"
          >
            View source document
          </a>
        </div>
      )}

      {investmentPreview.length > 0 && (
        <div className="mt-3 rounded bg-surface-raised p-3">
          <div className="flex flex-wrap gap-2">
            {investmentPreview.map((line) => (
              <span
                key={line}
                className="rounded-full bg-surface px-2 py-1 text-xs font-ui text-text-body"
              >
                {line}
              </span>
            ))}
          </div>
        </div>
      )}

      {item.source === 'document_extracted' && (
        <p className="mt-3 text-xs font-ui text-text-muted">
          Review extracted information and correct any fields that appear inaccurate.
        </p>
      )}

      {item.ai_reasoning && (
        <p className="mt-2 text-sm font-ui italic text-text-muted">{item.ai_reasoning}</p>
      )}

      {item.confidence != null && (
        <div className="mt-2">
          <ConfidenceBar confidence={item.confidence} />
        </div>
      )}

      {item.explanation && (
        <div className="mt-3 pt-3 border-t border-border">
          <p className="text-xs font-ui text-text-body">{item.explanation.plain_english_summary}</p>
          <button
            type="button"
            onClick={() => setShowExplanation((v) => !v)}
            className="mt-1 text-xs font-ui text-text-muted hover:text-text-body transition-colors"
          >
            {showExplanation ? 'Hide details ↑' : 'Why this matters ↓'}
          </button>
          {showExplanation && (
            <div data-testid="review-explanation-details" className="mt-2 p-3 bg-surface-raised rounded text-xs font-ui space-y-2 text-text-muted">
              <p><span className="text-text-body">Why this matters: </span>{item.explanation.why_it_matters}</p>
              <p><span className="text-text-body">What to check: </span>{item.explanation.what_user_should_check}</p>
              {item.explanation.evidence_expected.length > 0 && (
                <p>
                  <span className="text-text-body">Expected evidence: </span>
                  {item.explanation.evidence_expected.join(', ')}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {!item.questions_complete && item.inline_questions.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <InlineQuestion questions={item.inline_questions} onAnswer={handleInlineAnswer} />
        </div>
      )}

      <div className="mt-3 pt-3 border-t border-border">
        <button
          type="button"
          onClick={() => setShowHistory((v) => !v)}
          className="text-xs font-ui text-text-muted hover:text-text-body transition-colors"
        >
          {showHistory ? 'Hide review history ↑' : 'Review history ↓'}
        </button>
        {showHistory && (
          <div data-testid="review-history" className="mt-2 rounded bg-surface-raised p-3 text-xs font-ui text-text-muted">
            {decisionHistory.length === 0 ? (
              <p>No review history yet.</p>
            ) : (
              <div className="space-y-3">
                {decisionHistory.map((entry) => (
                  <div key={entry.id} className="border-b border-border pb-3 last:border-b-0 last:pb-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-text-body">{entry.action.replace(/_/g, ' ')}</span>
                      <span>{formatHistoryDate(entry.created_at)}</span>
                      {entry.bulk_action_id && (
                        <span className="rounded-full bg-review-bg px-2 py-0.5 text-review">Bulk action</span>
                      )}
                    </div>
                    {Object.keys(entry.changed_fields || {}).length > 0 && (
                      <div className="mt-2 space-y-1">
                        {Object.entries(entry.changed_fields).map(([field, change]) => (
                          <p key={field} className="text-text-body">
                            {`${field}: ${formatHistoryValue(change.old)} -> ${formatHistoryValue(change.new)}`}
                          </p>
                        ))}
                      </div>
                    )}
                    {entry.note && <p className="mt-2">{entry.note}</p>}
                  </div>
                ))}
                {canUndoLatest && (onUndo || (latestHistory?.bulk_action_id && onUndoBulk)) && (
                  <button
                    type="button"
                    onClick={handleUndo}
                    className="text-xs font-ui text-accent underline"
                  >
                    Undo last decision
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {!confirmed ? (
        <div
          data-testid="action-buttons"
          className={`flex flex-wrap gap-2 mt-3 pt-3 border-t border-border ${lockClass}`}
        >
          <button
            type="button"
            onClick={handleConfirm}
            className="min-h-11 px-3 py-2 rounded text-sm font-ui font-medium bg-ready text-surface hover:opacity-90 transition-opacity"
          >
            Looks right
          </button>
          <button
            type="button"
            onClick={() => setShowAmend((v) => !v)}
            className="min-h-11 px-3 py-2 rounded text-sm font-ui font-medium border border-border text-text-body hover:bg-surface-raised transition-colors"
          >
            Change this
          </button>
          <button
            type="button"
            onClick={() => setShowAsk(true)}
            className="min-h-11 px-3 py-2 rounded text-sm font-ui font-medium border border-border text-text-body hover:bg-surface-raised transition-colors"
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
