# M10 Phase 4 — Evidence (Document Upload) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Evidence page — document upload with SSE progress tracking, document list, and duplicate detection modal.

**Architecture:** UploadZone uses `useSSE` hook internally; SSE URL is set only after a successful upload response. The Evidence page owns `DuplicateModal` visibility. Backend gains two new endpoints: `GET /documents` (list) and `DELETE /documents/{id}` (soft-archive). No storage-usage indicator — the `/health` endpoint does not return usage metrics.

**Tech Stack:** Next.js 14 App Router, React Query v5, Zustand, axios, EventSource API, Jest + RTL, FastAPI, SQLAlchemy async.

---

## IMPORTANT — spec corrections

The user's spec shows:
```typescript
export const getDocuments = (workspaceId: string) =>
  client.get(`/documents?workspace_id=${workspaceId}`)
```

Two corrections needed:
1. Path must be `/api/v1/documents` — all other API functions use the `/api/v1/` prefix and Next.js only rewrites `/api/:path*` to the backend.
2. `workspaceId` is redundant — the backend already extracts it from the auth cookie. `getDocuments()` takes no parameter.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/repositories/documents.py` | Modify | Add `list_by_workspace`, `archive_by_id` |
| `backend/app/api/routes/documents.py` | Modify | Add `GET /documents`, `DELETE /documents/{id}` |
| `backend/tests/test_evidence.py` | Modify | Add 3 tests for new endpoints |
| `frontend/lib/api/types.ts` | Modify | Add `DocumentStatus`, `DocumentData`, `DocumentSummaryData`, `UploadResponse`, `DuplicateUploadResponse`, `SSEEvent` |
| `frontend/lib/api/documents.ts` | Create | `getDocuments`, `uploadDocument`, `getDocumentSummary`, `getDocumentFile`, `archiveDocument` |
| `frontend/__tests__/documents-api.test.ts` | Create | 5 tests for API functions |
| `frontend/lib/hooks/useSSE.ts` | Replace | Real EventSource wrapper — terminal-status auto-close, 5-min timeout, returns `{data, status, error}` |
| `frontend/__tests__/useSSE.test.ts` | Create | 2 tests: terminal close, timeout close |
| `frontend/components/evidence/UploadZone.tsx` | Create | Drag-drop + file input, 5 states, SSE progress, duplicate callback |
| `frontend/__tests__/UploadZone.test.tsx` | Create | 4 tests |
| `frontend/components/evidence/DocumentCard.tsx` | Create | Filename, date, status badge, View/Remove actions, expand |
| `frontend/__tests__/DocumentCard.test.tsx` | Create | 2 tests |
| `frontend/components/evidence/DuplicateModal.tsx` | Create | Modal showing existing doc summary, single CTA |
| `frontend/__tests__/DuplicateModal.test.tsx` | Create | 1 test |
| `frontend/app/(dashboard)/evidence/page.tsx` | Replace | Full evidence page wiring all pieces |
| `frontend/__tests__/evidence-page.test.tsx` | Create | 2 tests |

---

## Task 1: Backend — list + archive endpoints

**Files:**
- Modify: `backend/app/repositories/documents.py`
- Modify: `backend/app/api/routes/documents.py`
- Modify: `backend/tests/test_evidence.py`

- [ ] **Step 1: Write the failing tests**

Add to the end of `backend/tests/test_evidence.py`:

```python
@pytest.mark.asyncio
async def test_list_documents_returns_empty_for_new_workspace(auth_client):
    """GET /documents returns empty list when no documents exist."""
    response = auth_client.get("/api/v1/documents")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"] == []


@pytest.mark.asyncio
async def test_list_documents_excludes_archived(auth_client, tmp_path):
    """GET /documents excludes archived documents."""
    # Upload a document, then archive it via DELETE, then verify list is empty
    from pathlib import Path
    pdf_bytes = b"%PDF-1.4 minimal"
    response = auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    doc_id = response.json()["document_id"]

    # Archive it
    del_response = auth_client.delete(f"/api/v1/documents/{doc_id}")
    assert del_response.status_code == 200

    # Now list should be empty
    list_response = auth_client.get("/api/v1/documents")
    assert list_response.status_code == 200
    assert list_response.json()["data"] == []


@pytest.mark.asyncio
async def test_archive_document_not_found(auth_client):
    """DELETE /documents/{id} returns 404 for unknown document."""
    response = auth_client.delete("/api/v1/documents/nonexistent-id")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec backend pytest tests/test_evidence.py::test_list_documents_returns_empty_for_new_workspace tests/test_evidence.py::test_list_documents_excludes_archived tests/test_evidence.py::test_archive_document_not_found -v
```

Expected: FAIL with "404 Not Found" or attribute errors.

- [ ] **Step 3: Add repository methods**

In `backend/app/repositories/documents.py`, append:

```python
async def list_by_workspace(db: AsyncSession, workspace_id: str) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == workspace_id, Document.archived == False)
        .order_by(Document.uploaded_at.desc())
    )
    return list(result.scalars().all())


async def archive_by_id(db: AsyncSession, document_id: str) -> None:
    doc = await get_by_id(db, document_id)
    if doc:
        doc.archived = True
        doc.archived_reason = "user_removed"
        await db.commit()
```

- [ ] **Step 4: Add route handlers**

In `backend/app/api/routes/documents.py`, append after the existing routes:

```python
@router.get("/documents")
async def list_documents(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    docs = await doc_repo.list_by_workspace(db, workspace_id)
    return {
        "status": "ok",
        "data": [
            {
                "document_id": d.id,
                "original_filename": d.original_filename,
                "file_type": d.file_type,
                "file_size_bytes": d.file_size_bytes,
                "status": d.status,
                "document_type": d.document_type,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                "processed_at": d.processed_at.isoformat() if d.processed_at else None,
            }
            for d in docs
        ],
    }


@router.delete("/documents/{document_id}")
async def archive_document(
    document_id: str,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    doc = await doc_repo.get_by_id(db, document_id)
    if not doc or doc.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "Document not found.", retryable=False),
        )
    await doc_repo.archive_by_id(db, document_id)
    return {"status": "ok", "data": {"document_id": document_id}}
```

- [ ] **Step 5: Run tests — expect pass**

```bash
docker compose exec backend pytest tests/test_evidence.py::test_list_documents_returns_empty_for_new_workspace tests/test_evidence.py::test_list_documents_excludes_archived tests/test_evidence.py::test_archive_document_not_found -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Run full backend suite — confirm no regressions**

```bash
make test
```

Expected: all previous 125 tests + 3 new = 128 PASSED.

- [ ] **Step 7: Commit**

```bash
git add backend/app/repositories/documents.py backend/app/api/routes/documents.py backend/tests/test_evidence.py
git commit -m "feat: add list and archive endpoints for documents"
```

---

## Task 2: API types + `lib/api/documents.ts`

**Files:**
- Modify: `frontend/lib/api/types.ts`
- Create: `frontend/lib/api/documents.ts`
- Create: `frontend/__tests__/documents-api.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/__tests__/documents-api.test.ts`:

```typescript
jest.mock('@/lib/api/client', () => ({
  default: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
  __esModule: true,
}))

import client from '@/lib/api/client'
import {
  getDocuments,
  uploadDocument,
  getDocumentSummary,
  getDocumentFile,
  archiveDocument,
} from '@/lib/api/documents'

const mockClient = client as {
  get: jest.Mock
  post: jest.Mock
  delete: jest.Mock
}

beforeEach(() => jest.clearAllMocks())

describe('documents API', () => {
  it('getDocuments calls GET /api/v1/documents', async () => {
    mockClient.get.mockResolvedValue({ data: { status: 'ok', data: [] } })
    await getDocuments()
    expect(mockClient.get).toHaveBeenCalledWith('/api/v1/documents')
  })

  it('uploadDocument posts multipart form to /api/v1/documents/upload', async () => {
    mockClient.post.mockResolvedValue({ data: { document_id: 'doc-1', status: 'processing' } })
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    await uploadDocument(file)
    expect(mockClient.post).toHaveBeenCalledWith(
      '/api/v1/documents/upload',
      expect.any(FormData),
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  })

  it('getDocumentSummary calls GET /api/v1/documents/{id}/summary', async () => {
    mockClient.get.mockResolvedValue({ data: { status: 'ok', data: {} } })
    await getDocumentSummary('doc-1')
    expect(mockClient.get).toHaveBeenCalledWith('/api/v1/documents/doc-1/summary')
  })

  it('getDocumentFile calls GET with responseType blob', async () => {
    mockClient.get.mockResolvedValue({ data: new Blob() })
    await getDocumentFile('doc-1')
    expect(mockClient.get).toHaveBeenCalledWith(
      '/api/v1/documents/doc-1/file',
      { responseType: 'blob' }
    )
  })

  it('archiveDocument calls DELETE /api/v1/documents/{id}', async () => {
    mockClient.delete.mockResolvedValue({ data: { status: 'ok', data: { document_id: 'doc-1' } } })
    await archiveDocument('doc-1')
    expect(mockClient.delete).toHaveBeenCalledWith('/api/v1/documents/doc-1')
  })
})
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
make test-fe 2>&1 | grep "documents-api"
```

Expected: FAIL with "Cannot find module '@/lib/api/documents'".

- [ ] **Step 3: Add types to `types.ts`**

Append to the end of `frontend/lib/api/types.ts`:

```typescript
export type DocumentStatus = 'processing' | 'ready' | 'failed' | 'archived'

export interface DocumentData {
  document_id: string
  original_filename: string
  file_type: string | null
  file_size_bytes: number | null
  status: DocumentStatus
  document_type: string | null
  uploaded_at: string
  processed_at: string | null
}

export interface DocumentSummaryData extends DocumentData {
  extraction_method: string | null
  extraction_confidence: number | null
  extracted_fields: Record<string, unknown> | null
}

export interface UploadResponse {
  document_id: string
  status: 'processing'
}

export interface DuplicateUploadResponse {
  status: 'duplicate'
  existing_document_id: string
}

export interface SSEEvent {
  document_id: string
  status: DocumentStatus
  stage?: string
  progress?: number
  events_created?: number
  error_code?: string
}
```

- [ ] **Step 4: Create `frontend/lib/api/documents.ts`**

```typescript
import client from './client'
import type { ApiResponse, DocumentData, DocumentSummaryData, UploadResponse, DuplicateUploadResponse } from './types'

export const getDocuments = () =>
  client.get<ApiResponse<DocumentData[]>>('/api/v1/documents')

export const uploadDocument = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return client.post<UploadResponse | DuplicateUploadResponse>(
    '/api/v1/documents/upload',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
}

export const getDocumentSummary = (id: string) =>
  client.get<ApiResponse<DocumentSummaryData>>(`/api/v1/documents/${id}/summary`)

export const getDocumentFile = (id: string) =>
  client.get<Blob>(`/api/v1/documents/${id}/file`, { responseType: 'blob' })

export const archiveDocument = (id: string) =>
  client.delete<ApiResponse<{ document_id: string }>>(`/api/v1/documents/${id}`)
```

- [ ] **Step 5: Run tests — expect pass**

```bash
make test-fe 2>&1 | grep -E "documents-api|PASS|FAIL"
```

Expected: `PASS __tests__/documents-api.test.ts` with 5 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/api/types.ts frontend/lib/api/documents.ts frontend/__tests__/documents-api.test.ts
git commit -m "feat: add document API types and functions"
```

---

## Task 3: `useSSE` hook — real implementation

**Files:**
- Replace: `frontend/lib/hooks/useSSE.ts`
- Create: `frontend/__tests__/useSSE.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/__tests__/useSSE.test.ts`:

```typescript
import { renderHook, act } from '@testing-library/react'
import { useSSE } from '@/lib/hooks/useSSE'

class MockEventSource {
  static instance: MockEventSource | null = null
  url: string
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  close = jest.fn()

  constructor(url: string) {
    this.url = url
    MockEventSource.instance = this
  }
}

beforeAll(() => {
  Object.defineProperty(global, 'EventSource', {
    value: MockEventSource,
    writable: true,
  })
})

beforeEach(() => {
  MockEventSource.instance = null
  jest.useFakeTimers()
})

afterEach(() => {
  jest.useRealTimers()
})

describe('useSSE', () => {
  it('closes EventSource on terminal status "ready"', () => {
    const { result } = renderHook(() => useSSE('/stream/doc-1'))
    const es = MockEventSource.instance!
    expect(es).not.toBeNull()

    act(() => {
      es.onmessage?.({
        data: JSON.stringify({ document_id: 'doc-1', status: 'ready', events_created: 1 }),
      })
    })

    expect(es.close).toHaveBeenCalled()
    expect(result.current.data?.status).toBe('ready')
  })

  it('closes EventSource after 5-minute timeout', () => {
    const { result } = renderHook(() => useSSE('/stream/doc-1'))
    const es = MockEventSource.instance!
    expect(result.current.status).toBe('connecting')

    act(() => {
      jest.advanceTimersByTime(5 * 60 * 1000 + 1)
    })

    expect(es.close).toHaveBeenCalled()
    expect(result.current.status).toBe('closed')
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
make test-fe 2>&1 | grep -E "useSSE|PASS|FAIL"
```

Expected: FAIL — stub returns `undefined` not `{ data, status, error }`.

- [ ] **Step 3: Replace `frontend/lib/hooks/useSSE.ts`**

```typescript
'use client'
import { useEffect, useState } from 'react'
import type { SSEEvent } from '@/lib/api/types'

const TERMINAL = new Set(['ready', 'failed', 'archived'])
const TIMEOUT_MS = 5 * 60 * 1000

type SSEStatus = 'connecting' | 'open' | 'closed'

export function useSSE(url: string | null): {
  data: SSEEvent | null
  status: SSEStatus
  error: string | null
} {
  const [data, setData] = useState<SSEEvent | null>(null)
  const [status, setStatus] = useState<SSEStatus>('closed')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!url) return
    setStatus('connecting')
    setData(null)
    setError(null)

    const es = new EventSource(url)

    const timer = setTimeout(() => {
      es.close()
      setStatus('closed')
      setError('timeout')
    }, TIMEOUT_MS)

    es.onopen = () => setStatus('open')

    es.onmessage = (e) => {
      try {
        const evt: SSEEvent = JSON.parse(e.data as string)
        setData(evt)
        if (TERMINAL.has(evt.status)) {
          clearTimeout(timer)
          es.close()
          setStatus('closed')
        }
      } catch {
        // ignore malformed events
      }
    }

    es.onerror = () => {
      clearTimeout(timer)
      es.close()
      setStatus('closed')
      setError('connection_error')
    }

    return () => {
      clearTimeout(timer)
      es.close()
    }
  }, [url])

  return { data, status, error }
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
make test-fe 2>&1 | grep -E "useSSE|PASS|FAIL"
```

Expected: `PASS __tests__/useSSE.test.ts` with 2 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/hooks/useSSE.ts frontend/__tests__/useSSE.test.ts
git commit -m "feat: implement useSSE hook — terminal auto-close, 5-min timeout"
```

---

## Task 4: `UploadZone` component

**Files:**
- Create: `frontend/components/evidence/UploadZone.tsx`
- Create: `frontend/__tests__/UploadZone.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/__tests__/UploadZone.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import UploadZone from '@/components/evidence/UploadZone'

jest.mock('@/lib/api/documents', () => ({
  uploadDocument: jest.fn(),
  __esModule: true,
}))

jest.mock('@/lib/hooks/useSSE', () => ({
  useSSE: jest.fn().mockReturnValue({ data: null, status: 'closed', error: null }),
  __esModule: true,
}))

import { uploadDocument } from '@/lib/api/documents'

const mockUpload = uploadDocument as jest.Mock
const onUploadComplete = jest.fn()
const onDuplicate = jest.fn()

function renderZone() {
  return render(
    <UploadZone onUploadComplete={onUploadComplete} onDuplicate={onDuplicate} />
  )
}

beforeEach(() => jest.clearAllMocks())

describe('UploadZone', () => {
  it('renders idle state with drop text and supported formats', () => {
    renderZone()
    expect(screen.getByText(/drop your document here/i)).toBeInTheDocument()
    expect(screen.getByText(/supported/i)).toBeInTheDocument()
    expect(screen.getByText(/maximum 20mb/i)).toBeInTheDocument()
  })

  it('shows error for oversized file (client-side validation)', () => {
    renderZone()
    const input = screen.getByLabelText(/upload document/i)
    const file = new File(['x'], 'big.pdf', { type: 'application/pdf' })
    Object.defineProperty(file, 'size', { value: 21 * 1024 * 1024 })
    fireEvent.change(input, { target: { files: [file] } })
    expect(screen.getByText(/too large/i)).toBeInTheDocument()
  })

  it('shows error for unsupported format (client-side validation)', () => {
    renderZone()
    const input = screen.getByLabelText(/upload document/i)
    const file = new File(['content'], 'doc.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    fireEvent.change(input, { target: { files: [file] } })
    expect(screen.getByText(/not supported/i)).toBeInTheDocument()
  })

  it('transitions to uploading state on valid file selection', async () => {
    mockUpload.mockReturnValue(new Promise(() => {})) // never resolves — stays uploading
    renderZone()
    const input = screen.getByLabelText(/upload document/i)
    const file = new File(['%PDF-content'], 'payslip.pdf', { type: 'application/pdf' })
    fireEvent.change(input, { target: { files: [file] } })
    await waitFor(() => expect(screen.getByText(/payslip\.pdf/i)).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
make test-fe 2>&1 | grep -E "UploadZone|PASS|FAIL"
```

Expected: FAIL with "Cannot find module '@/components/evidence/UploadZone'".

- [ ] **Step 3: Create `frontend/components/evidence/UploadZone.tsx`**

```typescript
'use client'
import { useState, useRef, useCallback, useEffect } from 'react'
import { uploadDocument } from '@/lib/api/documents'
import { useSSE } from '@/lib/hooks/useSSE'

const ALLOWED_TYPES = new Set([
  'application/pdf',
  'image/jpeg',
  'image/png',
  'text/csv',
  'application/vnd.ms-excel',
])
const ALLOWED_EXTS = new Set(['.pdf', '.jpg', '.jpeg', '.png', '.csv'])
const MAX_BYTES = 20 * 1024 * 1024

const ERROR_MESSAGES: Record<string, string> = {
  ocr_failed: 'We had trouble reading this document.',
  file_corrupted: 'This file appears to be damaged.',
  file_too_large: 'This file is too large. Maximum size is 20MB.',
  unsupported_format: "This file format isn't supported.",
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
      }
    },
    [onDuplicate]
  )

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) void processFile(file)
    // reset input so same file can be re-selected after error
    e.target.value = ''
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setKind('idle')
    const file = e.dataTransfer.files?.[0]
    if (file) void processFile(file)
  }

  const handleReset = () => {
    setKind('idle')
    setFilename('')
    setErrorMessage('')
    setSseStage('')
    setDocumentId(null)
  }

  return (
    <div
      role="region"
      aria-label="File upload zone"
      onDragEnter={() => setKind('hover')}
      onDragLeave={() => kind === 'hover' && setKind('idle')}
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
        /* error */
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
```

- [ ] **Step 4: Run tests — expect pass**

```bash
make test-fe 2>&1 | grep -E "UploadZone|PASS|FAIL"
```

Expected: `PASS __tests__/UploadZone.test.tsx` with 4 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/evidence/UploadZone.tsx frontend/__tests__/UploadZone.test.tsx
git commit -m "feat: implement UploadZone — drag-drop, client validation, SSE progress"
```

---

## Task 5: `DocumentCard` component

**Files:**
- Create: `frontend/components/evidence/DocumentCard.tsx`
- Create: `frontend/__tests__/DocumentCard.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/__tests__/DocumentCard.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react'
import DocumentCard from '@/components/evidence/DocumentCard'
import type { DocumentData } from '@/lib/api/types'

const READY_DOC: DocumentData = {
  document_id: 'doc-1',
  original_filename: 'payslip.pdf',
  file_type: 'pdf',
  file_size_bytes: 12345,
  status: 'ready',
  document_type: 'payg_summary',
  uploaded_at: '2026-05-01T10:00:00+00:00',
  processed_at: '2026-05-01T10:01:00+00:00',
}

const PROCESSING_DOC: DocumentData = {
  ...READY_DOC,
  document_id: 'doc-2',
  status: 'processing',
  processed_at: null,
}

describe('DocumentCard', () => {
  it('renders filename, upload date, and status badge', () => {
    render(<DocumentCard document={READY_DOC} onRemove={jest.fn()} />)
    expect(screen.getByText('payslip.pdf')).toBeInTheDocument()
    expect(screen.getByText(/1 May 2026/i)).toBeInTheDocument()
    expect(screen.getByText(/ready/i)).toBeInTheDocument()
  })

  it('shows processing spinner when status is processing', () => {
    render(<DocumentCard document={PROCESSING_DOC} onRemove={jest.fn()} />)
    expect(screen.getByTestId('processing-spinner')).toBeInTheDocument()
    expect(screen.getByText(/processing/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
make test-fe 2>&1 | grep -E "DocumentCard|PASS|FAIL"
```

Expected: FAIL with "Cannot find module '@/components/evidence/DocumentCard'".

- [ ] **Step 3: Create `frontend/components/evidence/DocumentCard.tsx`**

```typescript
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
```

- [ ] **Step 4: Run tests — expect pass**

```bash
make test-fe 2>&1 | grep -E "DocumentCard|PASS|FAIL"
```

Expected: `PASS __tests__/DocumentCard.test.tsx` with 2 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/evidence/DocumentCard.tsx frontend/__tests__/DocumentCard.test.tsx
git commit -m "feat: implement DocumentCard — status badge, view/remove actions, expand"
```

---

## Task 6: `DuplicateModal` component

**Files:**
- Create: `frontend/components/evidence/DuplicateModal.tsx`
- Create: `frontend/__tests__/DuplicateModal.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/__tests__/DuplicateModal.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DuplicateModal from '@/components/evidence/DuplicateModal'

jest.mock('@/lib/api/documents', () => ({
  getDocumentSummary: jest.fn(),
  __esModule: true,
}))

import { getDocumentSummary } from '@/lib/api/documents'

const SUMMARY = {
  document_id: 'doc-1',
  original_filename: 'payslip.pdf',
  file_type: 'pdf',
  file_size_bytes: 12345,
  status: 'ready' as const,
  document_type: 'payg_summary',
  uploaded_at: '2026-05-01T10:00:00+00:00',
  processed_at: '2026-05-01T10:01:00+00:00',
  extraction_method: 'pdfplumber',
  extraction_confidence: 0.95,
  extracted_fields: null,
}

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('DuplicateModal', () => {
  it('renders existing document summary and single CTA only', async () => {
    ;(getDocumentSummary as jest.Mock).mockResolvedValue({ data: { data: SUMMARY } })

    wrap(<DuplicateModal existingDocumentId="doc-1" onClose={jest.fn()} />)

    // Wait for the summary to load
    await screen.findByText('payslip.pdf')
    expect(screen.getByText(/1 May 2026/i)).toBeInTheDocument()

    // Single action only — "View existing document" link
    const cta = screen.getByRole('link', { name: /view existing document/i })
    expect(cta).toBeInTheDocument()

    // No "Replace" or "Keep both" options
    expect(screen.queryByRole('button', { name: /replace/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /keep both/i })).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
make test-fe 2>&1 | grep -E "DuplicateModal|PASS|FAIL"
```

Expected: FAIL with "Cannot find module '@/components/evidence/DuplicateModal'".

- [ ] **Step 3: Create `frontend/components/evidence/DuplicateModal.tsx`**

```typescript
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
    ? new Date(data.uploaded_at).toLocaleDateString('en-AU', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
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
            className="px-4 py-2 rounded-md bg-accent text-white font-ui font-medium text-sm hover:bg-accent-hover transition-colors"
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
```

- [ ] **Step 4: Run test — expect pass**

```bash
make test-fe 2>&1 | grep -E "DuplicateModal|PASS|FAIL"
```

Expected: `PASS __tests__/DuplicateModal.test.tsx` with 1 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/evidence/DuplicateModal.tsx frontend/__tests__/DuplicateModal.test.tsx
git commit -m "feat: implement DuplicateModal — existing doc summary, single CTA"
```

---

## Task 7: Evidence page

**Files:**
- Replace: `frontend/app/(dashboard)/evidence/page.tsx`
- Create: `frontend/__tests__/evidence-page.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/__tests__/evidence-page.test.tsx`:

```typescript
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EvidencePage from '@/app/(dashboard)/evidence/page'
import * as documentsApi from '@/lib/api/documents'

jest.mock('@/lib/api/documents')
jest.mock('@/lib/stores/workspace.store', () => ({
  default: jest.fn().mockReturnValue({
    workspaceId: 'ws-1',
    financialYear: '2024-25',
    isAuthenticated: true,
    isUnlocked: true,
  }),
  __esModule: true,
}))
jest.mock('@/components/evidence/UploadZone', () => ({
  default: () => <div data-testid="upload-zone" />,
  __esModule: true,
}))
jest.mock('@/components/evidence/DocumentCard', () => ({
  default: ({ document }: { document: { original_filename: string } }) => (
    <div data-testid="document-card">{document.original_filename}</div>
  ),
  __esModule: true,
}))

const mockGetDocuments = documentsApi.getDocuments as jest.Mock

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

beforeEach(() => jest.clearAllMocks())

describe('EvidencePage', () => {
  it('shows empty state when no documents exist', async () => {
    mockGetDocuments.mockResolvedValue({ data: { data: [] } })
    wrap(<EvidencePage />)
    await waitFor(() =>
      expect(screen.getByText(/upload your first document to get started/i)).toBeInTheDocument()
    )
  })

  it('renders a DocumentCard for each document returned', async () => {
    mockGetDocuments.mockResolvedValue({
      data: {
        data: [
          {
            document_id: 'doc-1',
            original_filename: 'payslip.pdf',
            file_type: 'pdf',
            file_size_bytes: 12345,
            status: 'ready',
            document_type: 'payg_summary',
            uploaded_at: '2026-05-01T10:00:00+00:00',
            processed_at: '2026-05-01T10:01:00+00:00',
          },
          {
            document_id: 'doc-2',
            original_filename: 'bank.csv',
            file_type: 'csv',
            file_size_bytes: 5000,
            status: 'processing',
            document_type: null,
            uploaded_at: '2026-05-02T09:00:00+00:00',
            processed_at: null,
          },
        ],
      },
    })
    wrap(<EvidencePage />)
    await waitFor(() => expect(screen.getAllByTestId('document-card')).toHaveLength(2))
    expect(screen.getByText('payslip.pdf')).toBeInTheDocument()
    expect(screen.getByText('bank.csv')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
make test-fe 2>&1 | grep -E "evidence-page|PASS|FAIL"
```

Expected: FAIL — stub page renders "coming soon", not actual content.

- [ ] **Step 3: Replace `frontend/app/(dashboard)/evidence/page.tsx`**

```typescript
'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getDocuments, archiveDocument } from '@/lib/api/documents'
import type { DocumentData } from '@/lib/api/types'
import UploadZone from '@/components/evidence/UploadZone'
import DocumentCard from '@/components/evidence/DocumentCard'
import DuplicateModal from '@/components/evidence/DuplicateModal'
import useWorkspaceStore from '@/lib/stores/workspace.store'
import { isFYActive } from '@/lib/utils/fy'

export default function EvidencePage() {
  const queryClient = useQueryClient()
  const { financialYear } = useWorkspaceStore()
  const [duplicateDocId, setDuplicateDocId] = useState<string | null>(null)

  const { data: documents, isLoading, isError } = useQuery<DocumentData[]>({
    queryKey: ['documents'],
    queryFn: () => getDocuments().then((r) => r.data.data),
  })

  const removeMutation = useMutation({
    mutationFn: archiveDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
  })

  const handleUploadComplete = () => {
    queryClient.invalidateQueries({ queryKey: ['documents'] })
  }

  const fyActive = financialYear ? isFYActive(financialYear) : false

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-text-muted">Loading your documents…</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-risk-high">
          Unable to load documents. Please try refreshing.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">
          Supporting Evidence
        </h1>
        <p className="text-sm font-ui text-text-muted mt-1">
          Upload tax documents to build your evidence package.
        </p>
      </div>

      {fyActive && (
        <div className="bg-review-bg rounded-md px-4 py-3">
          <p className="text-sm font-ui text-review">
            Some documents (like PAYG summaries) are only available after 30 June.
            Upload what you have now.
          </p>
        </div>
      )}

      <UploadZone
        onUploadComplete={handleUploadComplete}
        onDuplicate={(existingId) => setDuplicateDocId(existingId)}
      />

      {documents && documents.length === 0 ? (
        <p className="text-sm font-ui text-text-muted text-center py-12">
          Upload your first document to get started
        </p>
      ) : (
        <div className="space-y-3">
          {documents?.map((doc) => (
            <DocumentCard
              key={doc.document_id}
              document={doc}
              onRemove={(id) => removeMutation.mutate(id)}
            />
          ))}
        </div>
      )}

      {duplicateDocId && (
        <DuplicateModal
          existingDocumentId={duplicateDocId}
          onClose={() => setDuplicateDocId(null)}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
make test-fe 2>&1 | grep -E "evidence-page|PASS|FAIL"
```

Expected: `PASS __tests__/evidence-page.test.tsx` with 2 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/(dashboard)/evidence/page.tsx frontend/__tests__/evidence-page.test.tsx
git commit -m "feat: implement Evidence page — upload zone, document list, duplicate modal"
```

---

## Task 8: Full test suite verification

**Files:** None — read-only verification.

- [ ] **Step 1: Run backend tests**

```bash
make test
```

Expected output: `128 passed` (125 from Phase 3 + 3 new from Task 1).

- [ ] **Step 2: Run frontend tests**

```bash
make test-fe
```

Expected: `~135 passed` across `~27 test suites` (121 from Phase 3 + ~14 new tests from Phase 4):
- `documents-api.test.ts` → 5 tests
- `useSSE.test.ts` → 2 tests
- `UploadZone.test.tsx` → 4 tests
- `DocumentCard.test.tsx` → 2 tests
- `DuplicateModal.test.tsx` → 1 test
- `evidence-page.test.tsx` → 2 tests

- [ ] **Step 3: If anything fails, fix before committing**

Common failure modes:
- `useSSE` timeout test: ensure `jest.useFakeTimers()` is called in `beforeEach` and `jest.useRealTimers()` in `afterEach`
- `DuplicateModal` test: ensure the `QueryClientProvider` wrapper is used
- `UploadZone` test: ensure `uploadDocument` mock is set up correctly

- [ ] **Step 4: Commit**

```bash
git commit -m "test: M10 Phase 4 full test suite — 128 backend, ~135 frontend"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| UploadZone — 5 states (idle/hover/uploading/success/error) | Task 4 |
| UploadZone — client validation (type, size) | Task 4 |
| UploadZone — SSE progress tracking | Task 4 (useSSE Task 3) |
| UploadZone — duplicate detection → callback | Task 4 |
| DocumentCard — filename, file type icon, date, status badge | Task 5 |
| DocumentCard — processing spinner | Task 5 |
| DocumentCard — expand to show extracted summary | Task 5 |
| DocumentCard — View original / Remove actions | Task 5 |
| DuplicateModal — existing doc summary | Task 6 |
| DuplicateModal — single CTA only ("View existing →") | Task 6 |
| DuplicateModal — no Replace/Keep both | Task 6 |
| useSSE — terminal auto-close | Task 3 |
| useSSE — 5-minute timeout | Task 3 |
| useSSE — returns `{data, status, error}` | Task 3 |
| Evidence page — upload zone at top | Task 7 |
| Evidence page — document list sorted desc | Task 7 (backend sort in Task 1) |
| Evidence page — empty state | Task 7 |
| Evidence page — FY-aware banner | Task 7 |
| GET /documents backend endpoint | Task 1 |
| DELETE /documents/{id} backend endpoint | Task 1 |
| lib/api/documents.ts — 5 API functions | Task 2 |
| Storage usage indicator | **NOT BUILT** — backend health endpoint does not return storage metrics. Flag to user if needed. |

**Type consistency check:**
- `DocumentData.document_id` (not `id`) — matches backend route response shape → used consistently in DocumentCard, DuplicateModal, evidence page
- `UploadResponse.document_id` → set as `documentId` state in UploadZone
- `DuplicateUploadResponse.existing_document_id` → passed to `onDuplicate` callback
- `SSEEvent.status` is `DocumentStatus` — `TERMINAL` set in useSSE checks `'ready' | 'failed' | 'archived'` all of which are in `DocumentStatus`

**Placeholder scan:** None found — all steps have complete code.

**One gap flagged:** Storage usage indicator is out of scope — not returned by the current backend. Noted in spec coverage table above.
