'use client'
import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  bulkAction,
  getReviewQueue,
  submitInlineAnswer,
  takeAction,
  undoBulkReviewDecision,
  undoReviewDecision,
} from '@/lib/api/review'
import type { ReviewItem, ReviewQueue } from '@/lib/api/types'
import ReviewCard from '@/components/review/ReviewCard'
import BulkActionBar from '@/components/review/BulkActionBar'
import ManualEntryForm from '@/components/review/ManualEntryForm'
import { normalizeApiError } from '@/lib/api/errors'

const INCOME_CATEGORIES = new Set([
  'payg_income', 'allowance', 'lump_sum', 'bank_interest', 'investment_income_basic',
])
const DEDUCTION_CATEGORIES = new Set([
  'work_expense', 'work_subscription', 'work_equipment', 'vehicle', 'travel',
  'uniform', 'self_education', 'other_deduction', 'donation', 'private_health_rebate',
  'wfh_deduction',
])
const INVESTMENT_CATEGORIES = new Set([
  'shares_acquisition', 'crypto_acquisition',
  'crypto', 'crypto_income', 'crypto_gain', 'crypto_loss',
  'capital_gain', 'capital_loss', 'dividend',
  'foreign_income', 'managed_fund_distribution',
])

const FILTER_TABS = ['All', 'Income', 'Deductions', 'Investments', 'Confirmed']

function applyFilter(items: ReviewItem[], filter: string): ReviewItem[] {
  if (filter === 'income') return items.filter((i) => INCOME_CATEGORIES.has(i.category ?? ''))
  if (filter === 'deductions') return items.filter((i) => DEDUCTION_CATEGORIES.has(i.category ?? ''))
  if (filter === 'investments') return items.filter((i) => INVESTMENT_CATEGORIES.has(i.category ?? ''))
  if (filter === 'confirmed') return items.filter((i) => i.status === 'confirmed')
  return items
}

function findGroups(items: ReviewItem[]): Map<string, { items: ReviewItem[]; label: string }> {
  const groups = new Map<string, { items: ReviewItem[]; label: string }>()
  items.forEach((item) => {
    const key = item.group_id ?? item.title
    if (!key) return
    const label = item.group_display ?? item.title ?? key
    const existing = groups.get(key) ?? { items: [], label }
    groups.set(key, { items: [...existing.items, item], label })
  })
  return new Map([...groups.entries()].filter(([, { items }]) => items.length >= 2))
}

function ReviewContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()
  const [showManualEntry, setShowManualEntry] = useState(false)
  const [activeFilter, setActiveFilter] = useState(() => searchParams.get('filter') ?? 'all')
  const [mutationError, setMutationError] = useState<string | null>(null)
  const [mutationSuccess, setMutationSuccess] = useState<string | null>(null)

  function handleFilterChange(filter: string) {
    setActiveFilter(filter)
    if (filter === 'all') {
      router.push('/review', { scroll: false })
    } else {
      router.push(`/review?filter=${filter}`, { scroll: false })
    }
  }

  const { data: queue, isLoading, isError } = useQuery<ReviewQueue>({
    queryKey: ['review-queue'],
    queryFn: () => getReviewQueue().then((r) => r.data.data),
  })

  const actionMutation = useMutation({
    mutationFn: ({
      id,
      action,
      payload,
    }: {
      id: string
      action: 'confirmed' | 'amended' | 'flagged' | 'skipped'
      payload: { amount?: number; category?: string; note?: string }
    }) => takeAction(id, action, payload),
    onSuccess: () => {
      setMutationError(null)
      setMutationSuccess(null)
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
    },
    onError: (err: unknown) => {
      setMutationError(normalizeApiError(err, 'Unable to save review action. Try again.').message)
    },
  })

  const bulkMutation = useMutation({
    mutationFn: (ids: string[]) => bulkAction(ids, 'confirmed'),
    onSuccess: () => {
      setMutationError(null)
      setMutationSuccess(null)
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
    },
    onError: (err: unknown) => {
      setMutationError(normalizeApiError(err, 'Unable to save review action. Try again.').message)
    },
  })

  const undoMutation = useMutation({
    mutationFn: (id: string) => undoReviewDecision(id),
    onSuccess: () => {
      setMutationError(null)
      setMutationSuccess('Review decision undone.')
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
    },
    onError: (err: unknown) => {
      setMutationSuccess(null)
      setMutationError(normalizeApiError(err, 'Unable to undo review decision. Try again.').message)
    },
  })

  const undoBulkMutation = useMutation({
    mutationFn: (bulkActionId: string) => undoBulkReviewDecision(bulkActionId),
    onSuccess: () => {
      setMutationError(null)
      setMutationSuccess('Review decision undone.')
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
    },
    onError: (err: unknown) => {
      setMutationSuccess(null)
      setMutationError(normalizeApiError(err, 'Unable to undo review decision. Try again.').message)
    },
  })

  async function handleInlineAnswer(
    itemId: string,
    questionId: string,
    answer: string,
    eventId: string
  ) {
    const res = await submitInlineAnswer(itemId, questionId, answer, eventId)
    queryClient.invalidateQueries({ queryKey: ['review-queue'] })
    return { new_skill_pending: res.data.data.new_skill_pending }
  }

  if (isLoading) {
    return (
      <div className="space-y-8 animate-pulse" aria-label="Loading">
        <div className="h-8 w-32 bg-surface rounded" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-surface rounded-lg p-4 h-20" />
        ))}
      </div>
    )
  }

  if (isError || !queue) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-risk-high">Unable to load review queue. Please refresh.</p>
      </div>
    )
  }

  const allNeedsReview = queue.needs_review.items
  const groups = findGroups(allNeedsReview)

  const allItems: ReviewItem[] = [
    ...queue.agent_required.items,
    ...queue.high_risk.items,
    ...queue.needs_review.items,
    ...queue.confirmed.items,
  ]
  const filteredItems = applyFilter(allItems, activeFilter)

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">Review</h1>
        {queue.pending > 0 ? (
          <p className="text-sm font-ui text-text-muted mt-1">
            {queue.pending} item{queue.pending !== 1 ? 's' : ''} to review
          </p>
        ) : (
          <p className="text-sm font-ui text-ready mt-1">All caught up</p>
        )}
        <button
          type="button"
          className="mt-3 text-sm font-ui text-accent underline"
          onClick={() => setShowManualEntry(true)}
        >
          + Add item manually
        </button>
        <p className="text-xs font-ui text-text-muted mt-3">
          Supporting Evidence = uploaded source documents.
        </p>
        <p className="text-xs font-ui text-text-muted mt-1">
          Review = tax items extracted or manually added for confirmation before export.
        </p>
        {mutationError && (
          <p role="alert" className="text-sm font-ui text-risk-high mt-3">
            {mutationError}
          </p>
        )}
        {mutationSuccess && (
          <p className="text-sm font-ui text-ready mt-3">
            {mutationSuccess}
          </p>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 flex-wrap border-b border-border" role="tablist" aria-label="Filter review items">
        {FILTER_TABS.map((tab) => {
          const key = tab.toLowerCase()
          const active = activeFilter === key
          return (
            <button
              key={key}
              role="tab"
              aria-selected={active}
              type="button"
              onClick={() => handleFilterChange(key)}
              style={{
                borderBottom: active ? '2px solid var(--color-accent)' : '2px solid transparent',
                color: active ? 'var(--color-accent)' : 'var(--color-text-muted)',
                fontFamily: 'var(--font-ui)',
                fontWeight: 500,
                padding: 'var(--space-2) var(--space-4)',
              }}
            >
              {tab}
            </button>
          )
        })}
      </div>

      {activeFilter !== 'all' && (
        <div className="space-y-3">
          {filteredItems.length === 0 ? (
            <p className="font-ui text-text-muted py-8 text-center">No items match this filter.</p>
          ) : (
            filteredItems.map((item) => (
              <ReviewCard
                key={item.id}
                item={item}
                onAction={(id, action, payload) => actionMutation.mutate({ id, action, payload })}
                onInlineAnswer={handleInlineAnswer}
                onUndo={(id) => undoMutation.mutate(id)}
                onUndoBulk={(bulkActionId) => undoBulkMutation.mutate(bulkActionId)}
              />
            ))
          )}
        </div>
      )}

      {activeFilter === 'all' && queue.pending === 0 && queue.total === 0 && (
        <div className="py-16 text-center">
          <p className="font-ui text-text-muted">
            No items to review yet. Complete the interview to generate review items.
          </p>
          <p className="mt-2 text-sm font-ui text-text-muted">
            Upload supporting evidence or add a manual item to create review items.
          </p>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-4">
            <Link href="/evidence" className="text-sm font-ui text-accent underline">
              Upload supporting evidence
            </Link>
            <button
              type="button"
              className="text-sm font-ui text-accent underline"
              onClick={() => setShowManualEntry(true)}
            >
              Add a manual item
            </button>
          </div>
        </div>
      )}

      {activeFilter === 'all' && queue.agent_required.count > 0 && (
        <section>
          <h2 className="font-display text-base font-semibold text-agent mb-3">
            Agent review required ({queue.agent_required.count})
          </h2>
          <div className="space-y-3">
            {queue.agent_required.items.map((item) => (
              <ReviewCard
                key={item.id}
                item={item}
                onAction={(id, action, payload) => actionMutation.mutate({ id, action, payload })}
                onInlineAnswer={handleInlineAnswer}
                onUndo={(id) => undoMutation.mutate(id)}
                onUndoBulk={(bulkActionId) => undoBulkMutation.mutate(bulkActionId)}
              />
            ))}
          </div>
        </section>
      )}

      {activeFilter === 'all' && queue.high_risk.count > 0 && (
        <section>
          <h2 className="font-display text-base font-semibold text-risk-high mb-3">
            Flagged for review ({queue.high_risk.count})
          </h2>
          <div className="space-y-3">
            {queue.high_risk.items.map((item) => (
              <ReviewCard
                key={item.id}
                item={item}
                onAction={(id, action, payload) => actionMutation.mutate({ id, action, payload })}
                onInlineAnswer={handleInlineAnswer}
                onUndo={(id) => undoMutation.mutate(id)}
                onUndoBulk={(bulkActionId) => undoBulkMutation.mutate(bulkActionId)}
              />
            ))}
          </div>
        </section>
      )}

      {activeFilter === 'all' && queue.needs_review.count > 0 && (
        <section>
          <h2 className="font-display text-base font-semibold text-text-primary mb-3">
            Needs your review ({queue.needs_review.count})
          </h2>
          <div className="space-y-3">
            {[...groups.entries()].map(([key, { items, label }]) => (
              <BulkActionBar
                key={key}
                items={items.map((item) => ({
                  id: item.id,
                  title: item.title ?? item.category ?? item.id,
                  amount: item.amount,
                  date: item.date,
                }))}
                groupLabel={label}
                onBulkConfirm={(ids) => bulkMutation.mutate(ids)}
              />
            ))}
            {allNeedsReview.map((item) => (
              <ReviewCard
                key={item.id}
                item={item}
                onAction={(id, action, payload) => actionMutation.mutate({ id, action, payload })}
                onInlineAnswer={handleInlineAnswer}
                onUndo={(id) => undoMutation.mutate(id)}
                onUndoBulk={(bulkActionId) => undoBulkMutation.mutate(bulkActionId)}
              />
            ))}
          </div>
        </section>
      )}

      {activeFilter === 'all' && queue.confirmed.count > 0 && (
        <section>
          <h2 className="font-display text-base font-semibold text-ready mb-3">
            Confirmed ({queue.confirmed.count})
          </h2>
          <div className="space-y-3">
            {queue.confirmed.items.map((item) => (
              <ReviewCard
                key={item.id}
                item={item}
                onAction={(id, action, payload) => actionMutation.mutate({ id, action, payload })}
                onInlineAnswer={handleInlineAnswer}
                onUndo={(id) => undoMutation.mutate(id)}
                onUndoBulk={(bulkActionId) => undoBulkMutation.mutate(bulkActionId)}
              />
            ))}
          </div>
        </section>
      )}
      {showManualEntry && (
        <div className="fixed inset-0 z-50 bg-canvas overflow-y-auto">
          <div className="max-w-lg mx-auto px-4 py-8">
            <ManualEntryForm
              onSuccess={() => {
                setShowManualEntry(false)
                queryClient.invalidateQueries({ queryKey: ['review-queue'] })
              }}
              onCancel={() => setShowManualEntry(false)}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default function ReviewPage() {
  return (
    <Suspense fallback={
      <div style={{ padding: 'var(--space-8)', color: 'var(--color-text-muted)' }}>
        Loading...
      </div>
    }>
      <ReviewContent />
    </Suspense>
  )
}
