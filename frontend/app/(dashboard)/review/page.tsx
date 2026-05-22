'use client'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { bulkAction, getReviewQueue, submitInlineAnswer, takeAction } from '@/lib/api/review'
import type { ReviewItem, ReviewQueue } from '@/lib/api/types'
import ReviewCard from '@/components/review/ReviewCard'
import BulkActionBar from '@/components/review/BulkActionBar'
import ManualEntryForm from '@/components/review/ManualEntryForm'

function findGroups(items: ReviewItem[]): Map<string, { ids: string[]; label: string }> {
  const groups = new Map<string, { ids: string[]; label: string }>()
  items.forEach((item) => {
    const key = item.group_id ?? item.title
    if (!key) return
    const label = item.group_display ?? item.title ?? key
    const existing = groups.get(key) ?? { ids: [], label }
    groups.set(key, { ids: [...existing.ids, item.id], label })
  })
  return new Map([...groups.entries()].filter(([, { ids }]) => ids.length >= 2))
}

export default function ReviewPage() {
  const queryClient = useQueryClient()
  const [showManualEntry, setShowManualEntry] = useState(false)

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
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['review-queue'] }),
  })

  const bulkMutation = useMutation({
    mutationFn: (ids: string[]) => bulkAction(ids, 'confirmed'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['review-queue'] }),
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
      </div>

      {queue.pending === 0 && queue.total === 0 && (
        <div className="py-16 text-center">
          <p className="font-ui text-text-muted">
            No items to review yet. Complete the interview to generate review items.
          </p>
        </div>
      )}

      {queue.agent_required.count > 0 && (
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
              />
            ))}
          </div>
        </section>
      )}

      {queue.high_risk.count > 0 && (
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
              />
            ))}
          </div>
        </section>
      )}

      {queue.needs_review.count > 0 && (
        <section>
          <h2 className="font-display text-base font-semibold text-text-primary mb-3">
            Needs your review ({queue.needs_review.count})
          </h2>
          <div className="space-y-3">
            {[...groups.entries()].map(([key, { ids, label }]) => (
              <BulkActionBar
                key={key}
                itemIds={ids}
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
              />
            ))}
          </div>
        </section>
      )}

      {queue.confirmed.count > 0 && (
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
