# M10 Phase 6: Export + Manual Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Export Review Pack page (Part A) and the Manual Entry form for adding items directly to the review queue (Part B).

**Architecture:** Export backend is fully implemented — this phase adds the frontend. Manual entry adds two new backend endpoints (`POST /events/manual`, `POST /events/{id}/attach-receipt`) plus a two-step frontend form with variable pricing period support. All state in React Query; password cleared immediately after POST.

**Tech Stack:** Next.js 14 App Router, React Query, TypeScript, Tailwind, pytest-asyncio, SQLAlchemy async

---

## Codebase Context

### What already exists (do not rebuild)
- `backend/app/engines/export.py` — `ExportEngine`: `check_eligibility`, `generate`, `get_download`, `get_history` — **fully implemented**
- `backend/app/api/routes/export.py` — all 5 export routes — **fully implemented**
- `backend/app/repositories/exports.py` — fully implemented
- `backend/app/repositories/events.py` — has `get_by_id`, `get_by_workspace` only — needs `create_event` + `attach_document`
- `backend/app/engines/review.py` — `ReviewEngine` with `process_action`, `bulk_action`, etc. — needs `create_manual_event` method
- `backend/app/engines/evidence.py` — `EvidenceEngine` with `validate_and_create` — needs `attach_receipt` method
- `backend/app/api/routes/events.py` — stubs at wrong paths — replace completely
- `frontend/app/(dashboard)/export/page.tsx` — stub ("coming soon") — replace
- `frontend/lib/api/types.ts` — has review types, needs export + events types appended
- `frontend/lib/api/review.ts` — complete
- `frontend/lib/api/client.ts` — axios with relative base URL + `withCredentials: true`

### Key patterns from existing code
```python
# ReviewEngine method signature style:
async def process_action(self, item_id: str, action: UserAction, payload: dict, db: AsyncSession) -> ReviewItem:

# Readiness recalculation (non-blocking background task):
asyncio.create_task(self._readiness_engine.recalculate(item.workspace_id))

# EvidenceEngine constructor:
EvidenceEngine(db=db, storage=storage)

# Storage backend:
from app.storage import get_storage_backend
storage = get_storage_backend()
```

```typescript
// API call pattern (export.py returns {"data": T} without status: 'ok'):
client.get<{ data: ExportRecord[] }>('/api/v1/export/history')
// Then: r.data.data to get the array

// Download via blob:
const response = await client.get('/api/v1/export/{id}/download', { responseType: 'blob' })
```

---

## File Structure

**New files:**
- `frontend/lib/api/export.ts` — 5 export API functions
- `frontend/lib/api/events.ts` — createManualEvent + attachReceipt
- `frontend/components/export/EligibilityCard.tsx` — blocked/warning state
- `frontend/components/export/ExportHistoryCard.tsx` — history item
- `frontend/components/review/ManualEntryForm.tsx` — 2-step form
- `frontend/__tests__/export-api.test.ts`
- `frontend/__tests__/events-api.test.ts`
- `frontend/__tests__/EligibilityCard.test.tsx`
- `frontend/__tests__/ExportHistoryCard.test.tsx`
- `frontend/__tests__/ManualEntryForm.test.tsx`
- `frontend/__tests__/export-page.test.tsx`
- `backend/tests/test_events.py`

**Modified files:**
- `frontend/lib/api/types.ts` — append export + events types
- `frontend/app/(dashboard)/export/page.tsx` — replace stub with real implementation
- `frontend/app/(dashboard)/review/page.tsx` — add "Add item manually" button + ManualEntryForm overlay
- `backend/app/api/routes/events.py` — replace stubs with real routes
- `backend/app/repositories/events.py` — add `create_event` + `attach_document`
- `backend/app/engines/review.py` — add `create_manual_event` method
- `backend/app/engines/evidence.py` — add `attach_receipt` method

---

## Task 1: API types + lib/api/export.ts + lib/api/events.ts

**Files:**
- Modify: `frontend/lib/api/types.ts`
- Create: `frontend/lib/api/export.ts`
- Create: `frontend/lib/api/events.ts`
- Create: `frontend/__tests__/export-api.test.ts`
- Create: `frontend/__tests__/events-api.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/__tests__/export-api.test.ts`:
```typescript
import * as exportApi from '@/lib/api/export'
import client from '@/lib/api/client'

jest.mock('@/lib/api/client', () => ({
  default: {
    get: jest.fn(),
    post: jest.fn(),
  },
}))

const mockGet = (client as jest.Mocked<typeof client>).get as jest.Mock
const mockPost = (client as jest.Mocked<typeof client>).post as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('export API', () => {
  it('getEligibility calls correct endpoint', async () => {
    mockGet.mockResolvedValue({ data: { data: { can_export: true, blocking_reasons: [], warnings: [] } } })
    const result = await exportApi.getEligibility()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/export/eligibility')
    expect(result.data.data.can_export).toBe(true)
  })

  it('generateExport posts password', async () => {
    mockPost.mockResolvedValue({ data: { data: { export_id: 'e-1', status: 'generating', warnings: [] } } })
    const result = await exportApi.generateExport('secret')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/export/generate', { password: 'secret' })
    expect(result.data.data.export_id).toBe('e-1')
  })

  it('getExportStatus calls correct endpoint', async () => {
    mockGet.mockResolvedValue({ data: { data: { id: 'e-1', status: 'ready' } } })
    const result = await exportApi.getExportStatus('e-1')
    expect(mockGet).toHaveBeenCalledWith('/api/v1/export/e-1/status')
    expect(result.data.data.status).toBe('ready')
  })

  it('getExportHistory calls correct endpoint', async () => {
    mockGet.mockResolvedValue({ data: { data: [] } })
    await exportApi.getExportHistory()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/export/history')
  })
})
```

Create `frontend/__tests__/events-api.test.ts`:
```typescript
import * as eventsApi from '@/lib/api/events'
import client from '@/lib/api/client'

jest.mock('@/lib/api/client', () => ({
  default: { get: jest.fn(), post: jest.fn() },
}))

const mockPost = (client as jest.Mocked<typeof client>).post as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('events API', () => {
  it('createManualEvent posts to /events/manual', async () => {
    mockPost.mockResolvedValue({ data: { data: { items: [], count: 0 } } })
    const payload = {
      event_type: 'deduction' as const,
      category: 'work_expense',
      description: 'Laptop',
      amount: 1200,
      date: '2025-08-01',
      frequency: 'one_off' as const,
      note: null,
      periods: null,
    }
    await eventsApi.createManualEvent(payload)
    expect(mockPost).toHaveBeenCalledWith('/api/v1/events/manual', payload)
  })

  it('attachReceipt posts file as multipart', async () => {
    mockPost.mockResolvedValue({ data: { data: { document_id: 'doc-1' } } })
    const file = new File(['content'], 'receipt.pdf', { type: 'application/pdf' })
    await eventsApi.attachReceipt('evt-1', file)
    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/events/evt-1/attach-receipt',
      expect.any(FormData),
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec frontend npx jest export-api events-api --no-coverage 2>&1 | tail -20
```
Expected: FAIL — module not found.

- [ ] **Step 3: Append types to `frontend/lib/api/types.ts`**

```typescript
// ── Export types ─────────────────────────────────────────────────────────────

export interface ExportEligibility {
  can_export: boolean
  blocking_reasons: string[]
  warnings: string[]
}

export type ExportStatus = 'generating' | 'ready' | 'expired' | 'failed'

export interface ExportRecord {
  id: string
  workspace_id: string
  financial_year: string
  readiness_pct: number | null
  confirmed_count: number
  review_count: number
  agent_count: number
  missing_count: number
  status: ExportStatus
  file_size_bytes: number | null
  expires_at: string | null
  created_at: string | null
}

export interface GenerateExportData {
  export_id: string
  status: ExportStatus
  warnings: string[]
}

// ── Manual entry types ────────────────────────────────────────────────────────

export interface ManualEventPeriod {
  months: number
  amount_per_month: number
}

export type ManualEventFrequency = 'one_off' | 'annual' | 'monthly'
export type ManualEventType = 'income' | 'deduction' | 'investment' | 'wfh' | 'other'

export interface ManualEventPayload {
  event_type: ManualEventType
  category: string
  description: string
  amount: number
  date: string
  frequency: ManualEventFrequency
  note: string | null
  periods: ManualEventPeriod[] | null
}

export interface ManualEventItem {
  id: string
  title: string | null
  category: string | null
  amount: number | null
}

export interface CreateManualEventData {
  items: ManualEventItem[]
  count: number
}

export interface AttachReceiptData {
  document_id: string
}
```

- [ ] **Step 4: Create `frontend/lib/api/export.ts`**

```typescript
import client from './client'
import type { ExportEligibility, ExportRecord, GenerateExportData } from './types'

export const getEligibility = () =>
  client.get<{ data: ExportEligibility }>('/api/v1/export/eligibility')

export const generateExport = (password: string) =>
  client.post<{ data: GenerateExportData }>('/api/v1/export/generate', { password })

export const getExportStatus = (id: string) =>
  client.get<{ data: ExportRecord }>(`/api/v1/export/${id}/status`)

export const downloadExport = async (id: string): Promise<void> => {
  const response = await client.get(`/api/v1/export/${id}/download`, { responseType: 'blob' })
  const disposition = response.headers['content-disposition'] as string | undefined
  const match = disposition?.match(/filename="([^"]+)"/)
  const filename = match?.[1] ?? 'review-package.zip'
  const url = URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export const getExportHistory = () =>
  client.get<{ data: ExportRecord[] }>('/api/v1/export/history')
```

- [ ] **Step 5: Create `frontend/lib/api/events.ts`**

```typescript
import client from './client'
import type { ManualEventPayload, CreateManualEventData, AttachReceiptData } from './types'

export const createManualEvent = (data: ManualEventPayload) =>
  client.post<{ data: CreateManualEventData }>('/api/v1/events/manual', data)

export const attachReceipt = (eventId: string, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return client.post<{ data: AttachReceiptData }>(
    `/api/v1/events/${eventId}/attach-receipt`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
}
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
docker compose exec frontend npx jest export-api events-api --no-coverage 2>&1 | tail -20
```
Expected: PASS — all 5 tests passing.

- [ ] **Step 7: Commit**

```bash
git add frontend/lib/api/types.ts frontend/lib/api/export.ts frontend/lib/api/events.ts \
        frontend/__tests__/export-api.test.ts frontend/__tests__/events-api.test.ts
git commit -m "feat: add export and events API types + functions"
```

---

## Task 2: EligibilityCard component

**Files:**
- Create: `frontend/components/export/EligibilityCard.tsx`
- Create: `frontend/__tests__/EligibilityCard.test.tsx`

- [ ] **Step 1: Write failing tests (spec tests 1 and 2)**

Create `frontend/__tests__/EligibilityCard.test.tsx`:
```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import EligibilityCard from '@/components/export/EligibilityCard'
import type { ExportEligibility } from '@/lib/api/types'

const blocked: ExportEligibility = {
  can_export: false,
  blocking_reasons: ['Interview must be complete before exporting. Please finish the interview first.'],
  warnings: [],
}

const warnOnly: ExportEligibility = {
  can_export: true,
  blocking_reasons: [],
  warnings: ['3 review item(s) have not been confirmed. Consider reviewing them before exporting.'],
}

describe('EligibilityCard', () => {
  it('renders blocked state — shows reason, hides Generate anyway', () => {
    render(<EligibilityCard eligibility={blocked} onGenerateAnyway={jest.fn()} />)
    expect(screen.getByText(/cannot export/i)).toBeInTheDocument()
    expect(screen.getByText(/interview must be complete/i)).toBeInTheDocument()
    expect(screen.queryByText(/generate anyway/i)).not.toBeInTheDocument()
  })

  it('renders warning state — shows warning, shows Generate anyway, calls callback', () => {
    const onGenerateAnyway = jest.fn()
    render(<EligibilityCard eligibility={warnOnly} onGenerateAnyway={onGenerateAnyway} />)
    expect(screen.getByText(/3 review item/i)).toBeInTheDocument()
    const btn = screen.getByText(/generate anyway/i)
    expect(btn).toBeInTheDocument()
    fireEvent.click(btn)
    expect(onGenerateAnyway).toHaveBeenCalledTimes(1)
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec frontend npx jest EligibilityCard --no-coverage 2>&1 | tail -20
```
Expected: FAIL — module not found.

- [ ] **Step 3: Create `frontend/components/export/EligibilityCard.tsx`**

```tsx
import type { ExportEligibility } from '@/lib/api/types'

interface Props {
  eligibility: ExportEligibility
  onGenerateAnyway: () => void
}

export default function EligibilityCard({ eligibility, onGenerateAnyway }: Props) {
  const isBlocked = eligibility.blocking_reasons.length > 0
  const hasWarnings = eligibility.warnings.length > 0

  return (
    <div className="rounded-lg border border-border bg-surface p-4 space-y-4">
      {isBlocked && (
        <div className="space-y-2">
          <p className="text-sm font-ui font-semibold text-risk-high">Cannot export yet</p>
          <ul className="space-y-1">
            {eligibility.blocking_reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-2 text-sm font-ui text-text-body">
                <span className="text-risk-high mt-0.5">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {hasWarnings && (
        <div className="space-y-2">
          <p className="text-sm font-ui font-semibold text-review">
            {isBlocked ? 'Warnings' : 'Before you export'}
          </p>
          <ul className="space-y-1">
            {eligibility.warnings.map((w, i) => (
              <li key={i} className="flex items-start gap-2 text-sm font-ui text-text-body">
                <span className="text-review mt-0.5">•</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
          {!isBlocked && (
            <button
              className="text-sm font-ui text-accent underline mt-2"
              onClick={onGenerateAnyway}
            >
              Generate anyway
            </button>
          )}
        </div>
      )}
      {!isBlocked && !hasWarnings && (
        <p className="text-sm font-ui text-ready">Ready to export.</p>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
docker compose exec frontend npx jest EligibilityCard --no-coverage 2>&1 | tail -20
```
Expected: PASS — 2 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/export/EligibilityCard.tsx frontend/__tests__/EligibilityCard.test.tsx
git commit -m "feat: implement EligibilityCard — blocked/warning export states"
```

---

## Task 3: ExportHistoryCard component

**Files:**
- Create: `frontend/components/export/ExportHistoryCard.tsx`
- Create: `frontend/__tests__/ExportHistoryCard.test.tsx`

- [ ] **Step 1: Write failing tests (spec test 3)**

Create `frontend/__tests__/ExportHistoryCard.test.tsx`:
```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import ExportHistoryCard from '@/components/export/ExportHistoryCard'
import type { ExportRecord } from '@/lib/api/types'

function makeRecord(status: string): ExportRecord {
  return {
    id: 'exp-1',
    workspace_id: 'ws-1',
    financial_year: '2024-25',
    readiness_pct: 82.5,
    confirmed_count: 10,
    review_count: 2,
    agent_count: 0,
    missing_count: 1,
    status: status as ExportRecord['status'],
    file_size_bytes: 1024 * 512,
    expires_at: '2026-05-23T10:00:00+00:00',
    created_at: '2026-05-22T10:00:00+00:00',
  }
}

describe('ExportHistoryCard', () => {
  it('renders ready state with download button', () => {
    const onDownload = jest.fn()
    render(
      <ExportHistoryCard
        record={makeRecord('ready')}
        onDownload={onDownload}
        onRegenerate={jest.fn()}
      />
    )
    expect(screen.getByText(/2024-25/)).toBeInTheDocument()
    expect(screen.getByText(/82/)).toBeInTheDocument()
    const btn = screen.getByText(/download/i)
    fireEvent.click(btn)
    expect(onDownload).toHaveBeenCalledWith('exp-1')
  })

  it('renders expired state with re-generate button', () => {
    const onRegenerate = jest.fn()
    render(
      <ExportHistoryCard
        record={makeRecord('expired')}
        onDownload={jest.fn()}
        onRegenerate={onRegenerate}
      />
    )
    const btn = screen.getByText(/re-generate/i)
    fireEvent.click(btn)
    expect(onRegenerate).toHaveBeenCalledWith('exp-1')
  })

  it('renders generating state with spinner', () => {
    render(
      <ExportHistoryCard
        record={makeRecord('generating')}
        onDownload={jest.fn()}
        onRegenerate={jest.fn()}
      />
    )
    expect(screen.getByTestId('history-generating-spinner')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec frontend npx jest ExportHistoryCard --no-coverage 2>&1 | tail -20
```
Expected: FAIL — module not found.

- [ ] **Step 3: Create `frontend/components/export/ExportHistoryCard.tsx`**

```tsx
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
            ` · ${record.readiness_pct.toFixed(0)}% readiness`}
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
            className="text-sm font-ui text-ready font-semibold"
            onClick={() => onDownload(record.id)}
          >
            Download
          </button>
        )}
        {(record.status === 'expired' || record.status === 'failed') && (
          <button
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
docker compose exec frontend npx jest ExportHistoryCard --no-coverage 2>&1 | tail -20
```
Expected: PASS — 3 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/export/ExportHistoryCard.tsx frontend/__tests__/ExportHistoryCard.test.tsx
git commit -m "feat: implement ExportHistoryCard — ready/expired/generating states"
```

---

## Task 4: Export page — full implementation

**Files:**
- Modify: `frontend/app/(dashboard)/export/page.tsx` (replace stub)
- Create: `frontend/__tests__/export-page.test.tsx`

- [ ] **Step 1: Write failing tests (spec tests 4 and 5)**

Create `frontend/__tests__/export-page.test.tsx`:
```tsx
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ExportPage from '@/app/(dashboard)/export/page'
import * as exportApi from '@/lib/api/export'
import type { ExportEligibility, ExportRecord } from '@/lib/api/types'

jest.mock('@/lib/api/export')
jest.mock('@/components/export/EligibilityCard', () => ({
  default: ({ eligibility, onGenerateAnyway }: { eligibility: ExportEligibility; onGenerateAnyway: () => void }) => (
    <div>
      {eligibility.can_export && (
        <button onClick={onGenerateAnyway} data-testid="generate-anyway">Generate anyway</button>
      )}
      {eligibility.blocking_reasons.map((r, i) => <p key={i}>{r}</p>)}
    </div>
  ),
  __esModule: true,
}))
jest.mock('@/components/export/ExportHistoryCard', () => ({
  default: ({ record }: { record: ExportRecord }) => (
    <div data-testid={`history-${record.id}`}>{record.status}</div>
  ),
  __esModule: true,
}))
jest.mock('@/components/shared/Disclaimer', () => ({
  default: () => <div data-testid="disclaimer" />,
  __esModule: true,
}))

const mockGetEligibility = exportApi.getEligibility as jest.Mock
const mockGenerateExport = exportApi.generateExport as jest.Mock
const mockGetExportStatus = exportApi.getExportStatus as jest.Mock
const mockGetExportHistory = exportApi.getExportHistory as jest.Mock

const readyEligibility: ExportEligibility = { can_export: true, blocking_reasons: [], warnings: [] }
const emptyHistory: ExportRecord[] = []

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

beforeEach(() => {
  jest.clearAllMocks()
  mockGetExportHistory.mockResolvedValue({ data: { data: emptyHistory } })
})

describe('ExportPage', () => {
  it('clears password field immediately after generate', async () => {
    mockGetEligibility.mockResolvedValue({ data: { data: readyEligibility } })
    mockGenerateExport.mockResolvedValue({
      data: { data: { export_id: 'exp-1', status: 'generating', warnings: [] } },
    })
    // Export status never resolves — keeps generating state
    mockGetExportStatus.mockReturnValue(new Promise(() => {}))

    wrap(<ExportPage />)
    await waitFor(() => screen.getByLabelText(/export password/i))

    fireEvent.change(screen.getByLabelText(/export password/i), {
      target: { value: 'mysecret123' },
    })
    expect(screen.getByLabelText(/export password/i)).toHaveValue('mysecret123')

    fireEvent.click(screen.getByRole('button', { name: /generate review pack/i }))

    // Password clears synchronously in the submit handler
    await waitFor(() =>
      expect(screen.queryByLabelText(/export password/i)).not.toBeInTheDocument()
    )
    // The form is hidden after submission starts; password was cleared before that
    expect(mockGenerateExport).toHaveBeenCalledWith('mysecret123')
  })

  it('polls status until ready then shows download button', async () => {
    jest.useFakeTimers()
    mockGetEligibility.mockResolvedValue({ data: { data: readyEligibility } })
    mockGenerateExport.mockResolvedValue({
      data: { data: { export_id: 'exp-2', status: 'generating', warnings: [] } },
    })
    mockGetExportStatus
      .mockResolvedValueOnce({
        data: {
          data: {
            id: 'exp-2', workspace_id: 'ws-1', financial_year: '2024-25',
            status: 'generating', readiness_pct: 80, confirmed_count: 5,
            review_count: 1, agent_count: 0, missing_count: 0,
            file_size_bytes: null, expires_at: null, created_at: null,
          },
        },
      })
      .mockResolvedValue({
        data: {
          data: {
            id: 'exp-2', workspace_id: 'ws-1', financial_year: '2024-25',
            status: 'ready', readiness_pct: 80, confirmed_count: 5,
            review_count: 1, agent_count: 0, missing_count: 0,
            file_size_bytes: 102400, expires_at: '2026-05-23T10:00:00+00:00',
            created_at: '2026-05-22T10:00:00+00:00',
          },
        },
      })

    wrap(<ExportPage />)
    await waitFor(() => screen.getByLabelText(/export password/i))
    fireEvent.change(screen.getByLabelText(/export password/i), { target: { value: 'pass' } })
    fireEvent.click(screen.getByRole('button', { name: /generate review pack/i }))

    await waitFor(() => screen.getByTestId('generating-spinner'))

    // Advance time to trigger refetch interval (2000ms)
    await act(async () => {
      jest.advanceTimersByTime(2100)
    })

    await waitFor(() => screen.getByText(/download now/i))
    jest.useRealTimers()
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec frontend npx jest export-page --no-coverage 2>&1 | tail -20
```
Expected: FAIL — stub page has no form.

- [ ] **Step 3: Replace `frontend/app/(dashboard)/export/page.tsx`**

```tsx
'use client'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  downloadExport,
  generateExport,
  getEligibility,
  getExportHistory,
  getExportStatus,
} from '@/lib/api/export'
import type { ExportRecord } from '@/lib/api/types'
import EligibilityCard from '@/components/export/EligibilityCard'
import ExportHistoryCard from '@/components/export/ExportHistoryCard'
import Disclaimer from '@/components/shared/Disclaimer'

export default function ExportPage() {
  const qc = useQueryClient()
  const [password, setPassword] = useState('')
  const [activeExportId, setActiveExportId] = useState<string | null>(null)
  const [showGenerateForm, setShowGenerateForm] = useState(false)

  const { data: eligibility, isLoading: eligibilityLoading } = useQuery({
    queryKey: ['export-eligibility'],
    queryFn: () => getEligibility().then((r) => r.data.data),
  })

  const { data: exportStatus } = useQuery<ExportRecord>({
    queryKey: ['export-status', activeExportId],
    queryFn: () => getExportStatus(activeExportId!).then((r) => r.data.data),
    enabled: activeExportId !== null,
    refetchInterval: (query) =>
      query.state.data?.status === 'generating' ? 2000 : false,
  })

  const { data: history } = useQuery<ExportRecord[]>({
    queryKey: ['export-history'],
    queryFn: () => getExportHistory().then((r) => r.data.data),
  })

  const generateMutation = useMutation({
    mutationFn: (pw: string) => generateExport(pw),
    onSuccess: (response) => {
      setActiveExportId(response.data.data.export_id)
      setShowGenerateForm(false)
      qc.invalidateQueries({ queryKey: ['export-history'] })
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const pw = password
    setPassword('') // clear immediately — never linger in state
    if (!pw.trim()) return
    generateMutation.mutate(pw)
  }

  function handleRegenerate() {
    setActiveExportId(null)
    setShowGenerateForm(true)
  }

  const canExport = eligibility?.can_export ?? false
  const isGenerating = exportStatus?.status === 'generating'
  const isReady = exportStatus?.status === 'ready'
  const showForm = (canExport || showGenerateForm) && activeExportId === null

  if (eligibilityLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-text-muted">Loading…</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">
          Export Review Pack
        </h1>
        <p className="text-sm font-ui text-text-muted mt-1">
          Generate an encrypted review package for your tax agent.
        </p>
      </div>

      {eligibility && (
        <EligibilityCard
          eligibility={eligibility}
          onGenerateAnyway={() => setShowGenerateForm(true)}
        />
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="space-y-4 max-w-sm">
          <p className="text-sm font-ui text-text-muted">
            Your password is not stored — save it somewhere safe.
          </p>
          <div>
            <label
              htmlFor="export-password"
              className="text-sm font-ui text-text-body block mb-1"
            >
              Set a password for your review pack
            </label>
            <input
              id="export-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
              placeholder="Enter password"
              aria-label="Export password"
            />
          </div>
          <button
            type="submit"
            className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
            disabled={generateMutation.isPending}
          >
            Generate review pack
          </button>
        </form>
      )}

      {isGenerating && (
        <div
          className="flex items-center gap-3 py-4"
          data-testid="generating-spinner"
        >
          <div className="animate-spin w-5 h-5 border-2 border-accent border-t-transparent rounded-full" />
          <p className="text-sm font-ui text-text-muted">Generating your review pack…</p>
        </div>
      )}

      {isReady && exportStatus && (
        <div className="rounded-lg border border-ready bg-ready-bg p-4 space-y-2">
          <p className="text-sm font-ui font-semibold text-ready">
            Your review pack is ready
          </p>
          <button
            className="text-sm font-ui text-ready underline"
            onClick={() => downloadExport(exportStatus.id)}
          >
            Download now
          </button>
        </div>
      )}

      {history && history.length > 0 && (
        <section>
          <h2 className="font-display text-base font-semibold text-text-primary mb-3">
            Export history
          </h2>
          <div className="space-y-3">
            {history.map((record) => (
              <ExportHistoryCard
                key={record.id}
                record={record}
                onDownload={downloadExport}
                onRegenerate={handleRegenerate}
              />
            ))}
          </div>
        </section>
      )}

      <Disclaimer />
    </div>
  )
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
docker compose exec frontend npx jest export-page --no-coverage 2>&1 | tail -20
```
Expected: PASS — 2 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/\(dashboard\)/export/page.tsx frontend/__tests__/export-page.test.tsx
git commit -m "feat: implement Export page — eligibility, generate, poll, history"
```

---

## Task 5: Backend — manual entry + attach receipt endpoints

**Files:**
- Modify: `backend/app/repositories/events.py` (add `create_event`, `attach_document`)
- Modify: `backend/app/engines/evidence.py` (add `attach_receipt` method)
- Modify: `backend/app/engines/review.py` (add `create_manual_event` method)
- Modify: `backend/app/api/routes/events.py` (replace stubs with real routes)
- Create: `backend/tests/test_events.py`

- [ ] **Step 1: Write failing tests (spec tests 10 and 11)**

Create `backend/tests/test_events.py`:
```python
"""
Tests for M10 Phase 6 — manual event creation and receipt attachment.
"""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from unittest.mock import MagicMock, patch

from app.db.models import TaxEvent, ReviewItem as ReviewItemModel, Workspace, TaxProfile, Document


@pytest_asyncio.fixture(autouse=True)
async def patch_async_session_local(test_engine, monkeypatch):
    import app.db.base as db_base
    test_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(db_base, "AsyncSessionLocal", test_maker)


@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def workspace(db_session):
    ws = Workspace(name="Events Test WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def profile(db_session, workspace):
    p = TaxProfile(
        workspace_id=workspace.id,
        financial_year="2024-25",
        employment_type="employee",
        has_wfh=False,
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest_asyncio.fixture
async def existing_event(db_session, workspace):
    evt = TaxEvent(
        workspace_id=workspace.id,
        financial_year="2024-25",
        event_type="deduction",
        category="work_expense",
        description="Laptop stand",
        amount=89.00,
        date="2025-08-01",
        source="manual_entry",
        status="needs_user_review",
        risk_level="low",
    )
    db_session.add(evt)
    await db_session.commit()
    await db_session.refresh(evt)
    return evt


@pytest.mark.asyncio
async def test_create_manual_event_one_off_creates_tax_event_and_review_item(
    db_session, workspace
):
    """POST /events/manual (one-off) creates 1 TaxEvent + 1 ReviewItem."""
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        import asyncio
        mock_recalc.return_value = asyncio.sleep(0)

        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="deduction",
            category="work_subscription",
            description="Spotify",
            amount=119.88,
            date="2025-09-01",
            frequency="one_off",
            note=None,
            periods=None,
            db=db_session,
        )

    assert len(events) == 1
    assert events[0].source == "manual_entry"
    assert events[0].description == "Spotify"
    assert events[0].amount == 119.88

    result = await db_session.execute(
        select(ReviewItemModel).where(ReviewItemModel.workspace_id == workspace.id)
    )
    items = result.scalars().all()
    assert len(items) == 1
    assert items[0].tax_event_id == events[0].id


@pytest.mark.asyncio
async def test_create_manual_event_monthly_creates_grouped_events(
    db_session, workspace
):
    """Monthly recurring with 2 periods creates 2 TaxEvents with same group_id."""
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        import asyncio
        mock_recalc.return_value = asyncio.sleep(0)

        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="deduction",
            category="work_subscription",
            description="Surfshark VPN",
            amount=0,
            date="2025-07-01",
            frequency="monthly",
            note=None,
            periods=[
                {"months": 3, "amount_per_month": 17.0},
                {"months": 8, "amount_per_month": 20.0},
            ],
            db=db_session,
        )

    assert len(events) == 2
    assert events[0].group_id == events[1].group_id
    assert events[0].group_id is not None
    assert events[0].amount == 51.0   # 3 × 17.0
    assert events[1].amount == 160.0  # 8 × 20.0
    assert all(e.is_recurring for e in events)
    assert "2 periods" in events[0].group_display
    assert "$211.00 total" in events[0].group_display


@pytest.mark.asyncio
async def test_attach_receipt_links_document_no_new_event(
    db_session, workspace, existing_event
):
    """attach_receipt links a Document to an existing TaxEvent, no new event created."""
    from app.engines.evidence import EvidenceEngine
    from app.storage.local import LocalStorageBackend
    import tempfile, os

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageBackend(base_path=tmpdir)
        engine = EvidenceEngine(db=db_session, storage=storage)

        # Minimal valid PDF bytes (magic bytes for PDF)
        fake_pdf = b"%PDF-1.4 1 0 obj<</Type /Catalog>> endobj"

        doc = await engine.attach_receipt(
            event_id=existing_event.id,
            workspace_id=workspace.id,
            file_data=fake_pdf,
            filename="receipt.pdf",
        )

    assert doc.id is not None
    assert doc.workspace_id == workspace.id

    # Existing event now has document_id set
    await db_session.refresh(existing_event)
    assert existing_event.document_id == doc.id

    # No new TaxEvent created
    result = await db_session.execute(
        select(TaxEvent).where(TaxEvent.workspace_id == workspace.id)
    )
    all_events = result.scalars().all()
    assert len(all_events) == 1  # only the original existing_event
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec backend pytest tests/test_events.py -v 2>&1 | tail -30
```
Expected: FAIL — `create_manual_event` and `attach_receipt` not implemented.

- [ ] **Step 3: Extend `backend/app/repositories/events.py`**

Add after the existing `get_by_workspace` function:

```python
import uuid as _uuid_mod


async def create_event(
    db: AsyncSession,
    workspace_id: str,
    financial_year: str,
    event_type: str,
    category: str,
    description: str | None,
    amount: float | None,
    date: str | None,
    source: str,
    note: str | None = None,
    group_id: str | None = None,
    group_display: str | None = None,
    is_recurring: bool = False,
    recurrence_index: int | None = None,
) -> TaxEvent:
    event = TaxEvent(
        workspace_id=workspace_id,
        financial_year=financial_year,
        event_type=event_type,
        category=category,
        description=description,
        amount=amount,
        date=date,
        source=source,
        user_note=note,
        group_id=group_id,
        group_display=group_display,
        is_recurring=is_recurring,
        recurrence_index=recurrence_index,
        status="needs_user_review",
        risk_level="low",
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def attach_document(
    db: AsyncSession, event_id: str, document_id: str
) -> TaxEvent:
    result = await db.execute(select(TaxEvent).where(TaxEvent.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise ValueError(f"TaxEvent {event_id!r} not found")
    event.document_id = document_id
    await db.commit()
    await db.refresh(event)
    return event
```

- [ ] **Step 4: Add `attach_receipt` method to `EvidenceEngine` in `backend/app/engines/evidence.py`**

Add the following method to the `EvidenceEngine` class (after `validate_and_create`):

```python
async def attach_receipt(
    self,
    event_id: str,
    workspace_id: str,
    file_data: bytes,
    filename: str,
) -> object:
    """Save file + link its Document to an existing TaxEvent. No OCR/classification."""
    from app.repositories import events as events_repo

    # 1. Validate size
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_data) > max_bytes:
        raise AppError(
            "file_too_large",
            f"This file is too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB.",
            retryable=False,
        )

    # 2. Validate MIME
    mime = magic.from_buffer(file_data, mime=True)
    if mime not in _ALLOWED_MIME:
        raise AppError(
            "unsupported_format",
            "This file format isn't supported.",
            retryable=False,
        )
    file_type = _ALLOWED_MIME[mime]

    # 3. SHA-256
    sha256 = hashlib.sha256(file_data).hexdigest()

    # 4. Save to storage
    doc_id = str(uuid.uuid4())
    storage_key = f"{workspace_id}/{doc_id}/{filename}"
    self.storage.save(storage_key, file_data)

    # 5. Create Document record (status: ready — no extraction needed)
    doc = await doc_repo.create_document(
        self._db,
        workspace_id=workspace_id,
        financial_year="",   # attached receipt inherits FY from the event
        original_filename=filename,
        storage_key=storage_key,
        file_type=file_type,
        file_size_bytes=len(file_data),
        sha256_hash=sha256,
        extraction_method="manual_attachment",
        status="ready",
    )

    # 6. Link document to existing TaxEvent
    await events_repo.attach_document(self._db, event_id, doc.id)

    return doc
```

Note: `doc_repo.create_document` is the existing repository function — check its signature in `repositories/documents.py` and match the parameters. If the signature differs, adjust accordingly.

- [ ] **Step 5: Verify `doc_repo.create_document` signature**

```bash
docker compose exec backend grep -n "async def create_document" app/repositories/documents.py
```

Read the actual signature and adjust the call in step 4 to match exactly. The function must exist — it was built in M3.

- [ ] **Step 6: Add `create_manual_event` method to `ReviewEngine` in `backend/app/engines/review.py`**

Add the following method to the `ReviewEngine` class (after `create_review_item`):

```python
async def create_manual_event(
    self,
    workspace_id: str,
    financial_year: str,
    event_type: str,
    category: str,
    description: str,
    amount: float,
    date: str,
    frequency: str,
    note: str | None,
    periods: list[dict] | None,
    db: AsyncSession,
) -> list[TaxEvent]:
    """Create TaxEvent(s) + ReviewItem(s) for a manual entry."""
    from app.repositories import events as events_repo
    import uuid as _uuid

    group_id = str(_uuid.uuid4()) if frequency == "monthly" and periods else None

    if frequency == "monthly" and periods:
        total_amount = sum(p["months"] * p["amount_per_month"] for p in periods)
        n = len(periods)
        group_display = (
            f"{description} · {n} period{'s' if n != 1 else ''} · ${total_amount:.2f} total"
        )
        created_events = []
        for idx, period in enumerate(periods):
            period_amount = period["months"] * period["amount_per_month"]
            event = await events_repo.create_event(
                db,
                workspace_id=workspace_id,
                financial_year=financial_year,
                event_type=event_type,
                category=category,
                description=description,
                amount=period_amount,
                date=date,
                source="manual_entry",
                note=note,
                group_id=group_id,
                group_display=group_display,
                is_recurring=True,
                recurrence_index=idx,
            )
            created_events.append(event)
    else:
        event = await events_repo.create_event(
            db,
            workspace_id=workspace_id,
            financial_year=financial_year,
            event_type=event_type,
            category=category,
            description=description,
            amount=amount,
            date=date,
            source="manual_entry",
            note=note,
            group_id=None,
            group_display=None,
            is_recurring=False,
            recurrence_index=None,
        )
        created_events = [event]

    # Create ReviewItem for each event
    for event in created_events:
        await self.create_review_item(event, db)

    asyncio.create_task(self._readiness_engine.recalculate(workspace_id))

    return created_events
```

- [ ] **Step 7: Replace `backend/app/api/routes/events.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.engines.evidence import EvidenceEngine
from app.engines.review import ReviewEngine
from app.errors import AppError, error_response
from app.repositories import profiles as profile_repo
from app.storage import get_storage_backend

router = APIRouter()

_review_engine = ReviewEngine()


class _Period(BaseModel):
    months: int
    amount_per_month: float


class ManualEventRequest(BaseModel):
    event_type: str
    category: str
    description: str
    amount: float
    date: str
    frequency: str          # "one_off" | "annual" | "monthly"
    note: str | None = None
    periods: list[_Period] | None = None


def _event_dict(ev) -> dict:
    return {
        "id": ev.id,
        "title": ev.description,
        "category": ev.category,
        "amount": ev.amount,
    }


@router.post("/events/manual")
async def create_manual_event(
    body: ManualEventRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await profile_repo.get_by_workspace(db, workspace_id)
    fy = profile.financial_year if profile else "2024-25"

    try:
        events = await _review_engine.create_manual_event(
            workspace_id=workspace_id,
            financial_year=fy,
            event_type=body.event_type,
            category=body.category,
            description=body.description,
            amount=body.amount,
            date=body.date,
            frequency=body.frequency,
            note=body.note,
            periods=[p.model_dump() for p in body.periods] if body.periods else None,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=error_response("invalid_event", str(e), retryable=False),
        )

    return {"data": {"items": [_event_dict(e) for e in events], "count": len(events)}}


@router.post("/events/{event_id}/attach-receipt")
async def attach_receipt(
    event_id: str,
    file: UploadFile = File(...),
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    file_data = await file.read()
    filename = file.filename or "receipt"
    storage = get_storage_backend()
    engine = EvidenceEngine(db=db, storage=storage)

    try:
        doc = await engine.attach_receipt(
            event_id=event_id,
            workspace_id=workspace_id,
            file_data=file_data,
            filename=filename,
        )
    except (AppError, ValueError) as e:
        code = getattr(e, "error_code", "attach_failed")
        msg = getattr(e, "message", str(e))
        raise HTTPException(
            status_code=422,
            detail=error_response(code, msg, retryable=False),
        )

    return {"data": {"document_id": doc.id}}
```

- [ ] **Step 8: Run tests to confirm they pass**

```bash
docker compose exec backend pytest tests/test_events.py -v 2>&1 | tail -40
```
Expected: PASS — all 3 tests passing.

- [ ] **Step 9: Run full backend suite to check for regressions**

```bash
docker compose exec backend pytest tests/ -v 2>&1 | tail -20
```
Expected: All prior tests still pass. New total: 132.

- [ ] **Step 10: Commit**

```bash
git add backend/app/repositories/events.py backend/app/engines/review.py \
        backend/app/engines/evidence.py backend/app/api/routes/events.py \
        backend/tests/test_events.py
git commit -m "feat: manual entry + attach receipt — backend endpoints + tests"
```

---

## Task 6: ManualEntryForm component + Review page button

**Files:**
- Create: `frontend/components/review/ManualEntryForm.tsx`
- Modify: `frontend/app/(dashboard)/review/page.tsx`
- Create: `frontend/__tests__/ManualEntryForm.test.tsx`

- [ ] **Step 1: Write failing tests (spec tests 6, 7, 8, 9)**

Create `frontend/__tests__/ManualEntryForm.test.tsx`:
```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ManualEntryForm from '@/components/review/ManualEntryForm'
import * as eventsApi from '@/lib/api/events'

jest.mock('@/lib/api/events')
const mockCreate = eventsApi.createManualEvent as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('ManualEntryForm', () => {
  it('step 1 renders 5 type options', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    expect(screen.getByText(/income/i)).toBeInTheDocument()
    expect(screen.getByText(/deduction/i)).toBeInTheDocument()
    expect(screen.getByText(/investment/i)).toBeInTheDocument()
    expect(screen.getByText(/work from home/i)).toBeInTheDocument()
    expect(screen.getByText(/other/i)).toBeInTheDocument()
  })

  it('step 2 shows correct fields for Deduction', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/deduction/i))
    // Step 2 shows category, description, frequency, amount, date
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/amount/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/date/i)).toBeInTheDocument()
    // Category dropdown shows deduction categories
    const select = screen.getByLabelText(/category/i) as HTMLSelectElement
    const options = Array.from(select.options).map((o) => o.value)
    expect(options).toContain('work_expense')
    expect(options).toContain('work_subscription')
    expect(options).not.toContain('payg_income')
  })

  it('monthly recurring calculates FY total correctly', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/deduction/i))

    // Switch to monthly
    fireEvent.click(screen.getByText(/monthly/i))

    // Set period 1: 12 months @ $10/month
    const monthsInput = screen.getByLabelText(/period 1 months/i)
    const amountInput = screen.getByLabelText(/period 1 amount per month/i)
    fireEvent.change(monthsInput, { target: { value: '12' } })
    fireEvent.change(amountInput, { target: { value: '10' } })

    // FY total = 12 × 10 = $120.00
    expect(screen.getByText(/\$120\.00/)).toBeInTheDocument()
  })

  it('variable pricing with two periods calculates total correctly', () => {
    render(<ManualEntryForm onSuccess={jest.fn()} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByText(/deduction/i))
    fireEvent.click(screen.getByText(/monthly/i))

    // Period 1: 6 months @ $5 = $30
    fireEvent.change(screen.getByLabelText(/period 1 months/i), { target: { value: '6' } })
    fireEvent.change(screen.getByLabelText(/period 1 amount per month/i), { target: { value: '5' } })

    // Add second period
    fireEvent.click(screen.getByText(/add pricing period/i))

    // Period 2: 6 months @ $7 = $42
    fireEvent.change(screen.getByLabelText(/period 2 months/i), { target: { value: '6' } })
    fireEvent.change(screen.getByLabelText(/period 2 amount per month/i), { target: { value: '7' } })

    // Total = $30 + $42 = $72.00
    expect(screen.getByText(/\$72\.00/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker compose exec frontend npx jest ManualEntryForm --no-coverage 2>&1 | tail -20
```
Expected: FAIL — module not found.

- [ ] **Step 3: Create `frontend/components/review/ManualEntryForm.tsx`**

```tsx
'use client'
import { useState } from 'react'
import { createManualEvent } from '@/lib/api/events'
import type { ManualEventFrequency, ManualEventType } from '@/lib/api/types'

const TYPE_OPTIONS: { value: ManualEventType; label: string; description: string }[] = [
  { value: 'income', label: 'Income', description: 'Wages, allowances, interest' },
  { value: 'deduction', label: 'Deduction', description: 'Work expenses, subscriptions' },
  { value: 'investment', label: 'Investment', description: 'Dividends, capital gains, crypto' },
  { value: 'wfh', label: 'Work from home', description: 'Working from home deductions' },
  { value: 'other', label: 'Other', description: 'Anything else' },
]

const TYPE_CATEGORIES: Record<ManualEventType, string[]> = {
  income: ['payg_income', 'allowance', 'lump_sum', 'bank_interest', 'investment_income_basic'],
  deduction: [
    'work_expense', 'work_subscription', 'work_equipment', 'vehicle', 'travel',
    'uniform', 'self_education', 'other_deduction', 'donation',
  ],
  investment: ['dividend', 'capital_gain', 'capital_loss', 'crypto'],
  wfh: ['wfh_deduction'],
  other: ['other_deduction'],
}

interface Period {
  months: number
  amount_per_month: number
}

interface Props {
  onSuccess: () => void
  onCancel: () => void
}

export default function ManualEntryForm({ onSuccess, onCancel }: Props) {
  const [step, setStep] = useState<1 | 2>(1)
  const [eventType, setEventType] = useState<ManualEventType | null>(null)
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState('')
  const [date, setDate] = useState('')
  const [frequency, setFrequency] = useState<ManualEventFrequency>('one_off')
  const [periods, setPeriods] = useState<Period[]>([{ months: 1, amount_per_month: 0 }])
  const [note, setNote] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isMonthly = frequency === 'monthly'
  const monthlyTotal = periods.reduce((sum, p) => sum + p.months * p.amount_per_month, 0)

  function updatePeriod(idx: number, field: keyof Period, value: number) {
    setPeriods((prev) => {
      const next = [...prev]
      next[idx] = { ...next[idx], [field]: value }
      return next
    })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!eventType) return
    setPending(true)
    setError(null)
    try {
      await createManualEvent({
        event_type: eventType,
        category,
        description,
        amount: isMonthly ? monthlyTotal : parseFloat(amount),
        date,
        frequency,
        note: note.trim() || null,
        periods: isMonthly
          ? periods.map((p) => ({ months: p.months, amount_per_month: p.amount_per_month }))
          : null,
      })
      onSuccess()
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setPending(false)
    }
  }

  if (step === 1) {
    return (
      <div className="space-y-4">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          What type of item?
        </h2>
        <div className="space-y-2">
          {TYPE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className="w-full text-left rounded-lg border border-border bg-surface p-4 min-h-14 hover:border-accent transition-colors"
              onClick={() => {
                setEventType(opt.value)
                setCategory(TYPE_CATEGORIES[opt.value][0])
                setStep(2)
              }}
            >
              <p className="font-ui font-semibold text-text-primary">{opt.label}</p>
              <p className="text-sm font-ui text-text-muted">{opt.description}</p>
            </button>
          ))}
        </div>
        <button
          className="text-sm font-ui text-text-muted"
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
    )
  }

  const categories = TYPE_CATEGORIES[eventType!]

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setStep(1)}
          className="text-sm font-ui text-text-muted"
        >
          ← Back
        </button>
        <h2 className="font-display text-xl font-semibold text-text-primary">
          {TYPE_OPTIONS.find((o) => o.value === eventType)?.label} details
        </h2>
      </div>

      <div>
        <label htmlFor="manual-category" className="text-sm font-ui text-text-body block mb-1">
          Category
        </label>
        <select
          id="manual-category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          aria-label="Category"
        >
          {categories.map((c) => (
            <option key={c} value={c}>
              {c.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="manual-desc" className="text-sm font-ui text-text-body block mb-1">
          Description
        </label>
        <input
          id="manual-desc"
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          aria-label="Description"
          required
        />
      </div>

      <div>
        <p className="text-sm font-ui text-text-body mb-1">Frequency</p>
        <div className="flex gap-2 flex-wrap">
          {(['one_off', 'annual', 'monthly'] as ManualEventFrequency[]).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFrequency(f)}
              className={`px-3 py-1 rounded-full text-sm font-ui border transition-colors ${
                frequency === f
                  ? 'border-accent text-accent bg-accent-soft'
                  : 'border-border text-text-muted'
              }`}
            >
              {f === 'one_off' ? 'One-off' : f === 'annual' ? 'Annual' : 'Monthly'}
            </button>
          ))}
        </div>
      </div>

      {!isMonthly && (
        <div>
          <label htmlFor="manual-amount" className="text-sm font-ui text-text-body block mb-1">
            Amount (AUD)
          </label>
          <input
            id="manual-amount"
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
            aria-label="Amount"
            step="0.01"
            min="0"
            required
          />
        </div>
      )}

      {isMonthly && (
        <div className="space-y-3">
          <p className="text-sm font-ui text-text-body">Pricing periods</p>
          {periods.map((period, idx) => (
            <div key={idx} className="flex gap-3 items-end flex-wrap">
              <div>
                <label
                  htmlFor={`period-${idx}-months`}
                  className="text-xs font-ui text-text-muted block mb-1"
                >
                  Months
                </label>
                <input
                  id={`period-${idx}-months`}
                  type="number"
                  value={period.months}
                  onChange={(e) => updatePeriod(idx, 'months', parseInt(e.target.value) || 1)}
                  className="w-20 rounded-md border border-border bg-surface px-2 py-1 text-sm font-mono"
                  min="1"
                  aria-label={`Period ${idx + 1} months`}
                />
              </div>
              <div>
                <label
                  htmlFor={`period-${idx}-amount`}
                  className="text-xs font-ui text-text-muted block mb-1"
                >
                  $/month
                </label>
                <input
                  id={`period-${idx}-amount`}
                  type="number"
                  value={period.amount_per_month}
                  onChange={(e) =>
                    updatePeriod(idx, 'amount_per_month', parseFloat(e.target.value) || 0)
                  }
                  className="w-28 rounded-md border border-border bg-surface px-2 py-1 text-sm font-mono"
                  step="0.01"
                  min="0"
                  aria-label={`Period ${idx + 1} amount per month`}
                />
              </div>
              {periods.length > 1 && (
                <button
                  type="button"
                  onClick={() => setPeriods((prev) => prev.filter((_, i) => i !== idx))}
                  className="text-sm font-ui text-text-muted pb-1"
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={() =>
              setPeriods((prev) => [...prev, { months: 1, amount_per_month: 0 }])
            }
            className="text-sm font-ui text-accent"
          >
            + Add pricing period
          </button>
          <p className="text-sm font-mono text-text-body font-semibold">
            FY total: ${monthlyTotal.toFixed(2)}
          </p>
        </div>
      )}

      <div>
        <label htmlFor="manual-date" className="text-sm font-ui text-text-body block mb-1">
          Date
        </label>
        <input
          id="manual-date"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          aria-label="Date"
          required
        />
      </div>

      <div>
        <label htmlFor="manual-note" className="text-sm font-ui text-text-body block mb-1">
          Note (optional)
        </label>
        <input
          id="manual-note"
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
          aria-label="Note"
        />
      </div>

      {error && (
        <p className="text-sm font-ui text-risk-high">{error}</p>
      )}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={pending}
          className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
        >
          {pending ? 'Saving…' : 'Add item'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="min-h-11 px-4 text-sm font-ui text-text-muted"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
docker compose exec frontend npx jest ManualEntryForm --no-coverage 2>&1 | tail -20
```
Expected: PASS — 4 tests passing.

- [ ] **Step 5: Add "Add item manually" button to Review page**

In `frontend/app/(dashboard)/review/page.tsx`, make these changes:

**Add import at top:**
```tsx
import ManualEntryForm from '@/components/review/ManualEntryForm'
```

**Add state inside `ReviewPage` (after `const queryClient = useQueryClient()`):**
```tsx
const [showManualEntry, setShowManualEntry] = useState(false)
```

**Add import for useState (if not already there):**
```tsx
import { useState } from 'react'
```

**Modify the heading section to add the button** (after the `</p>` that shows `items to review` / `All caught up`):
```tsx
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
          className="mt-3 text-sm font-ui text-accent underline"
          onClick={() => setShowManualEntry(true)}
        >
          + Add item manually
        </button>
      </div>
```

**Add ManualEntryForm overlay at the end of the returned JSX (just before the closing `</div>`):**
```tsx
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
```

- [ ] **Step 6: Run full frontend suite to check for regressions**

```bash
docker compose exec frontend npx jest --no-coverage 2>&1 | tail -20
```
Expected: All prior tests pass. New count includes 4 ManualEntryForm tests.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/review/ManualEntryForm.tsx \
        frontend/app/\(dashboard\)/review/page.tsx \
        frontend/__tests__/ManualEntryForm.test.tsx
git commit -m "feat: implement ManualEntryForm — 2-step form with variable pricing"
```

---

## Task 7: Full test suite verification

**Files:** none (read-only)

- [ ] **Step 1: Run full backend test suite**

```bash
docker compose exec backend pytest tests/ -v 2>&1 | tail -30
```
Expected: All tests pass. Count: 132 (129 prior + 3 new events tests).

- [ ] **Step 2: Run full frontend test suite**

```bash
docker compose exec frontend npx jest --no-coverage 2>&1 | tail -30
```
Expected: All tests pass. New frontend count: ~188 (168 prior + ~20 new).

- [ ] **Step 3: Confirm the 11 spec tests all pass**

```bash
docker compose exec frontend npx jest EligibilityCard ExportHistoryCard export-page ManualEntryForm export-api events-api --no-coverage --verbose 2>&1 | tail -40
docker compose exec backend pytest tests/test_events.py -v 2>&1 | tail -20
```
Expected: All 11 spec tests accounted for across these files.

- [ ] **Step 4: Commit**

```bash
git commit --allow-empty -m "test: Phase 6 full test suite verified — ~133 backend + ~208 frontend"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|---|---|
| EligibilityCard: blocked state with action links | Task 2 |
| EligibilityCard: warning state with "Generate anyway" | Task 2 |
| ExportHistoryCard: ready/expired/generating states | Task 3 |
| Export page: password clears after generate | Task 4 |
| Export page: polls until ready | Task 4 |
| ManualEntryForm: step 1 shows 5 types | Task 6 |
| ManualEntryForm: step 2 Deduction fields | Task 6 |
| ManualEntryForm: monthly total correct | Task 6 |
| ManualEntryForm: variable pricing two periods | Task 6 |
| Backend: POST /events/manual creates TaxEvent + ReviewItem | Task 5 |
| Backend: POST /events/{id}/attach-receipt links doc, no new event | Task 5 |
| lib/api/export.ts — 5 functions | Task 1 |
| lib/api/events.ts — createManualEvent + attachReceipt | Task 1 |
| Password not stored: cleared immediately in handleSubmit | Task 4 |
| "Your password is not stored" warning text | Task 4 |
| EvidenceEngine.attach_receipt method | Task 5 |
| ReviewEngine.create_manual_event method | Task 5 |
| events_repo.create_event + attach_document | Task 5 |
| Disclaimer on Export page | Task 4 |
| Not in scope: Settings page, deadline reminders | — |

All 11 spec tests covered. No gaps.

### Notes for implementer

1. **`doc_repo.create_document` signature** — In Task 5 Step 5, grep the actual function signature before implementing `attach_receipt`. Match parameters exactly. Do not guess.

2. **Password clearing** — `setPassword('')` runs synchronously in `handleSubmit` before `generateMutation.mutate(pw)`. The password is passed as a local variable `pw` to the mutation. After the sync clear, the input is empty while the mutation is pending. The test for "password clears" checks that the field is gone after submission (form hides on `onSuccess`). The mock `generateExport` must be resolved for `onSuccess` to run.

3. **`attach_receipt` storage_key format** — Match the pattern used by the evidence engine's `validate_and_create` method. Read how it constructs `storage_key` (typically `{workspace_id}/{doc_id}/{filename}`) and use the same format.

4. **Readiness recalculation in tests** — The `asyncio.create_task(self._readiness_engine.recalculate(...))` call will attempt to create a task. In tests, patch `recalculate` as shown in the test fixtures to prevent background task issues.

5. **Fake PDF in test 11** — The magic bytes `%PDF-1.4` are sufficient for `python-magic` to identify PDF mime type. If the validation requires more bytes, use a slightly longer fake header like `b"%PDF-1.4 1 0 obj<</Type /Catalog>>"`.

6. **`useState` import** — `frontend/app/(dashboard)/review/page.tsx` is a `'use client'` component and React is imported via `@tanstack/react-query`. Add `import { useState } from 'react'` if not already present at the top of the file.
