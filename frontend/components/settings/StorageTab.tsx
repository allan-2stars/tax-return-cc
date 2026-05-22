'use client'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getStorageUsage } from '@/lib/api/settings'

type Cleanup = '24h' | '7d' | 'never'

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function StorageTab() {
  const [cleanup, setCleanup] = useState<Cleanup>('24h')

  const { data, isLoading } = useQuery({
    queryKey: ['storage-usage'],
    queryFn: () => getStorageUsage().then((r) => r.data.data),
  })

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Usage breakdown
        </h2>
        {isLoading ? (
          <p className="text-sm font-ui text-text-muted">Loading…</p>
        ) : (
          <div className="space-y-2">
            <div className="flex justify-between text-sm font-ui">
              <span className="text-text-body">Documents</span>
              <span className="text-text-muted font-mono">
                {formatBytes(data?.documents_bytes ?? 0)}
              </span>
            </div>
            <div className="flex justify-between text-sm font-ui">
              <span className="text-text-body">Exports</span>
              <span className="text-text-muted font-mono">
                {formatBytes(data?.exports_bytes ?? 0)}
              </span>
            </div>
            <div className="flex justify-between text-sm font-ui">
              <span className="text-text-body">Database</span>
              <span className="text-text-muted font-mono">
                {formatBytes(data?.db_bytes ?? 0)}
              </span>
            </div>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Auto-cleanup exports
        </h2>
        <div className="flex gap-2 flex-wrap">
          {(['24h', '7d', 'never'] as Cleanup[]).map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => setCleanup(opt)}
              className={`px-3 py-1 rounded-full text-sm font-ui border transition-colors ${
                cleanup === opt
                  ? 'border-accent text-accent bg-accent-soft'
                  : 'border-border text-text-muted'
              }`}
            >
              {opt === '24h' ? '24 hours' : opt === '7d' ? '7 days' : 'Never'}
            </button>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Backup
        </h2>
        <p className="text-sm font-ui text-text-muted">
          Back up your{' '}
          <code className="font-mono text-text-primary">/data</code>{' '}
          volume regularly.
        </p>
        <p className="text-sm font-ui text-text-muted">
          Last backup: not detected.
        </p>
      </section>
    </div>
  )
}
