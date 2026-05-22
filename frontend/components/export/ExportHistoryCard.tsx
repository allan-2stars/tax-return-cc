import type { ExportRecord } from '@/lib/api/types'

interface Props {
  record: ExportRecord
  onDownload: (id: string) => void
  onRegenerate: (id: string) => void
}

function formatBytes(bytes: number | null): string {
  if (bytes === null) return ''
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function ExportHistoryCard({ record, onDownload, onRegenerate }: Props) {
  const createdDate = record.created_at
    ? new Date(record.created_at).toLocaleDateString('en-AU')
    : ''
  const expiresDate = record.expires_at
    ? new Date(record.expires_at).toLocaleDateString('en-AU')
    : ''

  return (
    <div className="rounded-lg border border-border bg-surface p-4 flex items-center justify-between gap-4">
      <div className="space-y-1 min-w-0">
        <p className="text-sm font-ui font-semibold text-text-primary">
          {record.financial_year} review package
        </p>
        <p className="text-xs font-ui text-text-muted">
          Generated {createdDate}
          {record.readiness_pct !== null &&
            ` · ${Math.floor(record.readiness_pct)}% readiness`}
          {record.file_size_bytes ? ` · ${formatBytes(record.file_size_bytes)}` : ''}
        </p>
        {record.status === 'ready' && expiresDate && (
          <p className="text-xs font-ui text-text-muted">Expires {expiresDate}</p>
        )}
      </div>

      <div className="flex-shrink-0">
        {record.status === 'generating' && (
          <div
            data-testid="history-generating-spinner"
            className="animate-spin w-5 h-5 border-2 border-accent border-t-transparent rounded-full"
          />
        )}
        {record.status === 'ready' && (
          <button
            type="button"
            className="text-sm font-ui text-ready font-semibold"
            onClick={() => onDownload(record.id)}
          >
            Download
          </button>
        )}
        {(record.status === 'expired' || record.status === 'failed') && (
          <button
            type="button"
            className="text-sm font-ui text-text-muted"
            onClick={() => onRegenerate(record.id)}
          >
            Re-generate
          </button>
        )}
      </div>
    </div>
  )
}
