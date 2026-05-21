'use client'
import { useQuery } from '@tanstack/react-query'
import { getDocumentSummary } from '@/lib/api/documents'

interface DuplicateModalProps {
  existingDocumentId: string
  onClose: () => void
}

export default function DuplicateModal({ existingDocumentId, onClose }: DuplicateModalProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['document-summary', existingDocumentId],
    queryFn: () => getDocumentSummary(existingDocumentId).then((r) => r.data.data),
  })

  const uploadedDate = data
    ? (() => {
        const d = new Date(data.uploaded_at)
        return isNaN(d.getTime())
          ? '—'
          : d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
      })()
    : null

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      role="dialog"
      aria-modal="true"
      aria-label="Duplicate document"
    >
      <div className="bg-surface rounded-lg shadow-lg p-6 max-w-sm w-full mx-4">
        <h2 className="font-display text-xl text-text-primary mb-1">
          Document already uploaded
        </h2>
        <p className="text-sm font-ui text-text-muted mb-5">
          This file has been uploaded before.
        </p>

        {isLoading ? (
          <p className="text-sm font-ui text-text-muted mb-5">Loading…</p>
        ) : data ? (
          <div className="bg-surface-raised rounded-md p-3 mb-5 space-y-1">
            <p className="font-ui font-medium text-text-body text-sm">{data.original_filename}</p>
            {uploadedDate && (
              <p className="text-xs font-ui text-text-muted">Uploaded {uploadedDate}</p>
            )}
          </div>
        ) : null}

        <div className="flex items-center gap-4">
          <a
            href={`/api/v1/documents/${existingDocumentId}/file`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 rounded-md bg-accent text-surface font-ui font-medium text-sm hover:bg-accent-hover transition-colors"
          >
            View existing document →
          </a>
          <button
            type="button"
            onClick={onClose}
            className="text-sm font-ui text-text-muted hover:text-text-body transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
