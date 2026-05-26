'use client'
import { useState } from 'react'
import { useReadiness } from '@/lib/hooks/useReadiness'
import useWorkspaceStore from '@/lib/stores/workspace.store'
import { deadlineState, daysUntilFYEnd } from '@/lib/utils/fy'

const SESSION_KEY = 'deadline-banner-dismissed'

export default function DeadlineBanner() {
  const { financialYear, userLodgerType } = useWorkspaceStore()
  const { data: readiness } = useReadiness()
  const [dismissed, setDismissed] = useState(() => {
    if (typeof window === 'undefined') return false
    return sessionStorage.getItem(SESSION_KEY) === '1'
  })

  if (!financialYear || dismissed) return null
  const state = deadlineState(financialYear)
  if (!state) return null

  const days = daysUntilFYEnd(financialYear)
  const isOctWarning =
    userLodgerType === 'self' &&
    readiness !== undefined &&
    readiness.percentage < 80

  const bgClass =
    state === 'terracotta'
      ? 'bg-risk-high text-white'
      : 'bg-review-bg text-review'

  let message: string
  if (isOctWarning) {
    message = `You need to lodge by 31 October. Your readiness is ${readiness!.percentage}% — keep going.`
  } else if (days <= 7) {
    message = `${days} day${days !== 1 ? 's' : ''} until the end of financial year. Finalise your documents now.`
  } else {
    message = `${days} days until the end of financial year.`
  }

  function dismiss() {
    sessionStorage.setItem(SESSION_KEY, '1')
    setDismissed(true)
  }

  return (
    <div role="alert" className={`px-4 py-2 flex items-center justify-between gap-4 ${bgClass}`}>
      <p className="text-sm font-ui">{message}</p>
      <button
        type="button"
        onClick={dismiss}
        className="text-sm font-ui shrink-0 opacity-70 hover:opacity-100"
        aria-label="Dismiss banner"
      >
        ×
      </button>
    </div>
  )
}
