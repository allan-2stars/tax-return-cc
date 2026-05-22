'use client'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAiUsage } from '@/lib/api/settings'
import type { AiUsageItem } from '@/lib/api/types'

const SENT_TO_AI = [
  { label: 'Extracted text from documents', sent: true },
  { label: 'Transaction amounts and dates', sent: true },
  { label: 'Merchant names', sent: true },
  { label: 'Original files', sent: false },
  { label: 'Your name or personal details', sent: false },
  { label: 'Bank account numbers', sent: false },
  { label: 'Tax File Number (TFN)', sent: false },
]

export default function AiPrivacyTab() {
  const [offlineMode, setOfflineMode] = useState(false)

  const { data: usageData, isLoading } = useQuery({
    queryKey: ['ai-usage'],
    queryFn: () => getAiUsage().then((r) => r.data.data),
  })

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          AI provider
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-sm font-ui text-text-body">Current provider:</span>
          <span className="text-sm font-mono text-text-primary font-semibold">
            {usageData?.ai_provider ?? '—'}
          </span>
        </div>
        <p className="text-xs font-ui text-text-muted">
          To change provider, update AI_PROVIDER in your .env and restart the service.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          What we send to AI
        </h2>
        <ul className="space-y-2">
          {SENT_TO_AI.map((item) => (
            <li key={item.label} className="flex items-center gap-2 text-sm font-ui">
              <span
                className={item.sent ? 'text-ready' : 'text-risk-high'}
                aria-hidden="true"
              >
                {item.sent ? '✓' : '✗'}
              </span>
              <span className={item.sent ? 'text-text-body' : 'text-text-muted'}>
                {item.label}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          AI usage this month
        </h2>
        {isLoading ? (
          <p className="text-sm font-ui text-text-muted">Loading…</p>
        ) : usageData?.items.length === 0 ? (
          <p className="text-sm font-ui text-text-muted">No AI calls this month.</p>
        ) : (
          <div className="space-y-1">
            {usageData?.items.map((item: AiUsageItem) => (
              <div
                key={item.operation}
                className="flex justify-between text-sm font-ui"
              >
                <span className="text-text-body capitalize">{item.operation}</span>
                <span className="text-text-muted">
                  {item.calls} call{item.calls !== 1 ? 's' : ''} ~${item.cost_usd.toFixed(2)}
                </span>
              </div>
            ))}
            <div className="border-t border-border mt-2 pt-2 flex justify-between text-sm font-ui font-semibold">
              <span className="text-text-body">Total</span>
              <span className="text-text-primary">
                ~${usageData?.total_cost_usd.toFixed(2)}
              </span>
            </div>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Offline mode
        </h2>
        <div className="flex items-center gap-3">
          <button
            type="button"
            role="switch"
            aria-checked={offlineMode}
            onClick={() => setOfflineMode((v) => !v)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              offlineMode ? 'bg-agent' : 'bg-border'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                offlineMode ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
          <span className="text-sm font-ui text-text-body">
            Disable AI — review all items manually
          </span>
        </div>
      </section>
    </div>
  )
}
