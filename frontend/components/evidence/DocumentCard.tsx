'use client'
import { useState } from 'react'
import type { DocumentData, DocumentStatus } from '@/lib/api/types'

const STATUS_CONFIG: Record<DocumentStatus, { label: string; classes: string; spinner: boolean }> = {
  processing: { label: 'Processing', classes: 'text-review bg-review-bg', spinner: true },
  ready:      { label: 'Ready',      classes: 'text-ready bg-ready-bg',   spinner: false },
  failed:     { label: 'Failed',     classes: 'text-risk-high bg-risk-bg', spinner: false },
  archived:   { label: 'Archived',   classes: 'text-text-muted bg-surface-raised', spinner: false },
}

const FILE_ICONS: Record<string, string> = {
  pdf: '📄',
  jpg: '🖼',
  jpeg: '🖼',
  png: '🖼',
  csv: '📊',
}

interface DocumentCardProps {
  document: DocumentData
  onRemove: (id: string) => void
}

export default function DocumentCard({ document, onRemove }: DocumentCardProps) {
  const [expanded, setExpanded] = useState(false)
  const cfg = STATUS_CONFIG[document.status] ?? STATUS_CONFIG.failed

  const uploadedDate = new Date(document.uploaded_at).toLocaleDateString('en-AU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })

  return (
    <div className="bg-surface border border-border rounded-md p-4">
      <div className="flex items-center gap-3">
        <span className="text-lg" aria-hidden>
          {FILE_ICONS[document.file_type ?? ''] ?? '📄'}
        </span>

        <div className="flex-1 min-w-0">
          <p className="font-ui font-medium text-text-body truncate">{document.original_filename}</p>
          <p className="text-xs font-ui text-text-muted">{uploadedDate}</p>
        </div>

        <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs font-ui font-medium ${cfg.classes}`}>
          {cfg.spinner && (
            <span
              data-testid="processing-spinner"
              className="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"
              aria-label="Loading"
            />
          )}
          {cfg.label}
        </span>
      </div>

      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-border">
        <a
          href={`/api/v1/documents/${document.document_id}/file`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-ui text-accent hover:text-accent-hover transition-colors"
        >
          View original
        </a>
        <button
          type="button"
          onClick={() => onRemove(document.document_id)}
          className="text-sm font-ui text-text-muted hover:text-risk-high transition-colors"
        >
          Remove
        </button>
        {document.status === 'ready' && document.document_type && (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="ml-auto text-sm font-ui text-text-muted hover:text-text-body transition-colors"
          >
            {expanded ? 'Less ↑' : 'Details ↓'}
          </button>
        )}
      </div>

      {expanded && document.document_type && (
        <div className="mt-3 pt-3 border-t border-border">
          <p className="text-xs font-ui text-text-muted">
            Type:{' '}
            <span className="text-text-body capitalize">
              {document.document_type.replace(/_/g, ' ')}
            </span>
          </p>
        </div>
      )}
    </div>
  )
}
