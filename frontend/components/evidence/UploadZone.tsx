'use client'
import { useState, useRef, useCallback, useEffect } from 'react'
import { uploadDocument } from '@/lib/api/documents'
import { useSSE } from '@/lib/hooks/useSSE'

const ALLOWED_TYPES = new Set([
  'application/pdf',
  'image/jpeg',
  'image/png',
  'text/csv',
])
const ALLOWED_EXTS = new Set(['.pdf', '.jpg', '.jpeg', '.png', '.csv'])
const MAX_BYTES = 20 * 1024 * 1024

const ERROR_MESSAGES: Record<string, string> = {
  ocr_failed: 'We had trouble reading this document.',
  file_corrupted: 'This file appears to be damaged.',
  file_too_large: 'This file is too large. Maximum size is 20MB.',
  unsupported_format: 'This file format is not supported.',
  default: 'Something went wrong. Please try again.',
}

const STAGE_LABELS: Record<string, string> = {
  ocr: 'Reading document...',
  classify: 'Identifying document type...',
  extract: 'Finding tax items...',
}

type UploadKind = 'idle' | 'hover' | 'uploading' | 'success' | 'error'

interface UploadZoneProps {
  onUploadComplete: (documentId: string) => void
  onDuplicate: (existingDocumentId: string) => void
}

export default function UploadZone({ onUploadComplete, onDuplicate }: UploadZoneProps) {
  const [kind, setKind] = useState<UploadKind>('idle')
  const [filename, setFilename] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [sseStage, setSseStage] = useState('')
  const [documentId, setDocumentId] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const dragCounterRef = useRef(0)
  const uploadingRef = useRef(false)

  const sseUrl = documentId ? `/api/v1/documents/${documentId}/stream` : null
  const { data: sseData } = useSSE(sseUrl)

  useEffect(() => {
    if (!sseData) return
    if (sseData.status === 'ready') {
      setKind('success')
      setDocumentId(null)
      onUploadComplete(sseData.document_id)
    } else if (sseData.status === 'failed') {
      setKind('error')
      setErrorMessage(ERROR_MESSAGES[sseData.error_code ?? ''] ?? ERROR_MESSAGES.default)
      setDocumentId(null)
    } else if (sseData.status === 'processing' && sseData.stage) {
      setSseStage(STAGE_LABELS[sseData.stage] ?? 'Processing...')
    }
  }, [sseData, onUploadComplete])

  const processFile = useCallback(
    async (file: File) => {
      if (uploadingRef.current) return
      const ext = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`
      if (!ALLOWED_TYPES.has(file.type) && !ALLOWED_EXTS.has(ext)) {
        setKind('error')
        setErrorMessage(ERROR_MESSAGES.unsupported_format)
        return
      }
      if (file.size > MAX_BYTES) {
        setKind('error')
        setErrorMessage(ERROR_MESSAGES.file_too_large)
        return
      }
      uploadingRef.current = true
      setFilename(file.name)
      setKind('uploading')
      setSseStage('')
      try {
        const res = await uploadDocument(file)
        const data = res.data
        if (data.status === 'duplicate') {
          setKind('idle')
          onDuplicate(data.existing_document_id)
        } else {
          setDocumentId(data.document_id)
        }
      } catch {
        setKind('error')
        setErrorMessage(ERROR_MESSAGES.default)
      } finally {
        uploadingRef.current = false
      }
    },
    [onDuplicate]
  )

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) void processFile(file)
    e.target.value = ''
  }

  const handleReset = () => {
    setKind('idle')
    setFilename('')
    setErrorMessage('')
    setSseStage('')
    setDocumentId(null)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    dragCounterRef.current = 0
    handleReset()
    const file = e.dataTransfer.files?.[0]
    if (file) void processFile(file)
  }

  return (
    <div
      role="region"
      aria-label="File upload zone"
      onDragEnter={() => { dragCounterRef.current++; setKind('hover') }}
      onDragLeave={() => { dragCounterRef.current--; if (dragCounterRef.current <= 0) { dragCounterRef.current = 0; setKind(prev => prev === 'hover' ? 'idle' : prev) } }}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      className={[
        'rounded-md border-2 border-dashed p-8 text-center transition-all',
        kind === 'hover' ? 'border-accent scale-[1.01]' : 'border-border-strong',
        kind === 'success' ? 'border-ready' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {kind === 'idle' || kind === 'hover' ? (
        <>
          <p className="font-ui text-text-muted">
            Drop your document here, or{' '}
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="text-accent hover:text-accent-hover font-medium"
            >
              browse
            </button>
          </p>
          <p className="text-sm font-ui text-text-faint mt-2">
            Supported: PDF, JPG, PNG, CSV · Maximum 20MB
          </p>
        </>
      ) : kind === 'uploading' ? (
        <div className="space-y-2">
          <p className="font-ui text-text-body truncate">{filename}</p>
          <p className="text-sm font-ui text-text-muted">{sseStage || 'Uploading...'}</p>
          <div className="w-full bg-progress-track rounded-full h-1.5">
            <div className="bg-progress-fill h-1.5 rounded-full animate-pulse w-1/2" />
          </div>
        </div>
      ) : kind === 'success' ? (
        <div className="space-y-2">
          <p className="text-ready font-ui font-medium">✓ {filename}</p>
          <button
            type="button"
            onClick={handleReset}
            className="text-sm font-ui text-text-muted hover:text-text-body transition-colors"
          >
            Remove
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm font-ui text-risk-high">{errorMessage}</p>
          <button
            type="button"
            onClick={handleReset}
            className="text-sm font-ui text-accent hover:text-accent-hover transition-colors"
          >
            Try again
          </button>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.csv"
        className="sr-only"
        aria-label="Upload document"
        onChange={handleChange}
      />
    </div>
  )
}
