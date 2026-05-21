# M10 Phase 2: Tax Readiness Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Tax Readiness Dashboard — circular progress ring, per-skill breakdown, sub-indicators, missing evidence page, and all shared display components (StatusBadge, ConfidenceBar) — fully tested and styled with DESIGN.md tokens.

**Architecture:** All new components are pure display components receiving data via props. Data fetching lives exclusively in `lib/hooks/useReadiness.ts` (React Query, 30s refetch, 3s stale polling). The readiness page composes these components; the missing evidence page has its own query. `StatusBadge` and `ConfidenceBar` are stateless; `SkillBreakdown` owns its own expand/collapse state; `MissingEvidenceList` owns its own skip state. No component fetches data directly.

**Tech Stack:** Next.js 14 App Router, TypeScript strict, Tailwind CSS (CSS-var tokens only, no arbitrary values), React Query v5, Jest + React Testing Library

---

## Current State

| File | State |
|------|-------|
| `app/(dashboard)/readiness/page.tsx` | Stub — `<p>Readiness — coming soon</p>` |
| `app/(dashboard)/readiness/missing/page.tsx` | Does not exist |
| `components/shared/StatusBadge.tsx` | Does not exist |
| `components/shared/ConfidenceBar.tsx` | Does not exist |
| `components/readiness/` directory | Does not exist |
| `lib/api/readiness.ts` | Does not exist |
| `lib/hooks/useReadiness.ts` | Does not exist |
| `backend/app/api/routes/readiness.py` | Missing `how_to_get` in `/readiness/missing` response |

---

## API Response Shapes (from backend)

**GET /api/v1/readiness:**
```json
{
  "data": {
    "percentage": 72,
    "breakdown": [
      { "skill_id": "employee_tax_au", "percentage": 80, "achieved_weight": 4.0, "total_weight": 5.0 }
    ],
    "missing_items_count": 2,
    "review_items_count": 3,
    "agent_items_count": 1,
    "is_stale": false,
    "calculated_at": "2026-05-20T10:00:00+00:00"
  }
}
```

**GET /api/v1/readiness/missing:**
```json
{
  "data": {
    "available_now": [
      { "requirement_id": "work_receipt", "display": "Work receipts", "weight": 1.0, "skill_id": "employee_tax_au", "how_to_get": "Collect receipts for work-related purchases" }
    ],
    "available_after_fy": [
      { "requirement_id": "payg_summary", "display": "PAYG payment summary", "weight": 2.0, "skill_id": "employee_tax_au", "how_to_get": "Download from myGov after July" }
    ]
  }
}
```

---

## File Map

**Create:**
```
frontend/lib/api/readiness.ts
frontend/lib/hooks/useReadiness.ts
frontend/components/readiness/ReadinessRing.tsx
frontend/components/readiness/SkillBreakdown.tsx
frontend/components/readiness/MissingEvidenceList.tsx
frontend/components/shared/StatusBadge.tsx
frontend/components/shared/ConfidenceBar.tsx
frontend/app/(dashboard)/readiness/missing/page.tsx
frontend/__tests__/readiness-api.test.ts
frontend/__tests__/useReadiness.test.tsx
frontend/__tests__/ReadinessRing.test.tsx
frontend/__tests__/StatusBadge.test.tsx
frontend/__tests__/ConfidenceBar.test.tsx
frontend/__tests__/SkillBreakdown.test.tsx
frontend/__tests__/MissingEvidenceList.test.tsx
frontend/__tests__/readiness-page.test.tsx
```

**Modify:**
```
frontend/lib/api/types.ts         — add ReadinessData, SkillBreakdownItem, MissingItem, MissingData
frontend/app/(dashboard)/readiness/page.tsx  — real implementation
backend/app/api/routes/readiness.py  — add how_to_get to /readiness/missing response
```

---

## Task 1: API types + readiness API functions (TDD) + backend `how_to_get` fix

**Files:**
- Modify: `frontend/lib/api/types.ts`
- Create: `frontend/lib/api/readiness.ts`
- Create: `frontend/__tests__/readiness-api.test.ts`
- Modify: `backend/app/api/routes/readiness.py`

- [ ] **Step 1: Add types to `frontend/lib/api/types.ts`**

Append to the existing file:

```ts
// frontend/lib/api/types.ts — append these interfaces

export interface SkillBreakdownItem {
  skill_id: string
  percentage: number
  achieved_weight: number
  total_weight: number
}

export interface ReadinessData {
  percentage: number
  breakdown: SkillBreakdownItem[]
  missing_items_count: number
  review_items_count: number
  agent_items_count: number
  is_stale: boolean
  calculated_at: string | null
}

export interface MissingItem {
  requirement_id: string
  display: string
  weight: number
  skill_id: string
  how_to_get?: string
}

export interface MissingData {
  available_now: MissingItem[]
  available_after_fy: MissingItem[]
}
```

- [ ] **Step 2: Write failing test for readiness API**

```ts
// frontend/__tests__/readiness-api.test.ts
jest.mock('@/lib/api/client', () => ({
  default: { get: jest.fn(), post: jest.fn() },
  __esModule: true,
}))

import client from '@/lib/api/client'
import * as readinessApi from '@/lib/api/readiness'

const mockGet = client.get as jest.Mock
const mockPost = client.post as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('readiness API', () => {
  it('getReadiness GETs /api/v1/readiness', async () => {
    mockGet.mockResolvedValue({ data: { data: {} } })
    await readinessApi.getReadiness()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/readiness')
  })

  it('getMissing GETs /api/v1/readiness/missing', async () => {
    mockGet.mockResolvedValue({ data: { data: {} } })
    await readinessApi.getMissing()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/readiness/missing')
  })

  it('triggerRecalculate POSTs to /api/v1/readiness/recalculate', async () => {
    mockPost.mockResolvedValue({ data: { data: { status: 'recalculating' } } })
    await readinessApi.triggerRecalculate()
    expect(mockPost).toHaveBeenCalledWith('/api/v1/readiness/recalculate')
  })
})
```

- [ ] **Step 3: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=readiness-api --watchAll=false
```

Expected: FAIL — `Cannot find module '@/lib/api/readiness'`

- [ ] **Step 4: Create `frontend/lib/api/readiness.ts`**

```ts
// frontend/lib/api/readiness.ts
import client from './client'
import type { ApiResponse, ReadinessData, MissingData } from './types'

export const getReadiness = () =>
  client.get<ApiResponse<ReadinessData>>('/api/v1/readiness')

export const getMissing = () =>
  client.get<ApiResponse<MissingData>>('/api/v1/readiness/missing')

export const triggerRecalculate = () =>
  client.post('/api/v1/readiness/recalculate')
```

- [ ] **Step 5: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=readiness-api --watchAll=false
```

Expected: `PASS __tests__/readiness-api.test.ts` — 3 tests passing.

- [ ] **Step 6: Add `how_to_get` to backend `/readiness/missing` response**

In `backend/app/api/routes/readiness.py`, update both `available_now.append` and `available_after_fy.append` to include `how_to_get`:

```python
# Replace the two .append() calls in the get_missing_items route:

        if item.available_after_fy and not fy_ended:
            available_after_fy.append({
                "requirement_id": item.requirement_id,
                "display": item.display,
                "weight": item.weight,
                "skill_id": item.skill_id,
                "how_to_get": item.how_to_get,
            })
        else:
            available_now.append({
                "requirement_id": item.requirement_id,
                "display": item.display,
                "weight": item.weight,
                "skill_id": item.skill_id,
                "how_to_get": item.how_to_get,
            })
```

- [ ] **Step 7: Verify backend tests still pass**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend pytest tests/test_readiness.py -v
```

Expected: All readiness tests pass (no regressions from the route change).

- [ ] **Step 8: Commit**

```bash
git add frontend/lib/api/types.ts frontend/lib/api/readiness.ts frontend/__tests__/readiness-api.test.ts backend/app/api/routes/readiness.py
git commit -m "feat: add readiness API types and functions; expose how_to_get in missing items"
```

---

## Task 2: `useReadiness` and `useMissing` hooks (TDD)

**Files:**
- Create: `frontend/__tests__/useReadiness.test.tsx`
- Create: `frontend/lib/hooks/useReadiness.ts`

- [ ] **Step 1: Write failing tests**

```tsx
// frontend/__tests__/useReadiness.test.tsx
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'

jest.mock('@/lib/api/readiness', () => ({
  getReadiness: jest.fn(),
  getMissing: jest.fn(),
  __esModule: true,
}))

import { getReadiness as mockGetReadiness, getMissing as mockGetMissing } from '@/lib/api/readiness'
import { useReadiness, useMissing } from '@/lib/hooks/useReadiness'

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

const MOCK_READINESS = {
  percentage: 72,
  breakdown: [{ skill_id: 'employee_tax_au', percentage: 80, achieved_weight: 4, total_weight: 5 }],
  missing_items_count: 2,
  review_items_count: 3,
  agent_items_count: 1,
  is_stale: false,
  calculated_at: '2026-05-20T10:00:00+00:00',
}

const MOCK_MISSING = {
  available_now: [{ requirement_id: 'receipt', display: 'Work receipt', weight: 1, skill_id: 'employee_tax_au' }],
  available_after_fy: [],
}

beforeEach(() => jest.clearAllMocks())

describe('useReadiness', () => {
  it('returns readiness data when query resolves', async () => {
    ;(mockGetReadiness as jest.Mock).mockResolvedValue({ data: { data: MOCK_READINESS } })
    const { result } = renderHook(() => useReadiness(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data?.percentage).toBe(72)
  })

  it('isLoading is true while fetching', () => {
    ;(mockGetReadiness as jest.Mock).mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useReadiness(), { wrapper: createWrapper() })
    expect(result.current.isLoading).toBe(true)
  })

  it('isError is true when query rejects', async () => {
    ;(mockGetReadiness as jest.Mock).mockRejectedValue(new Error('network error'))
    const { result } = renderHook(() => useReadiness(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useMissing', () => {
  it('returns missing data when query resolves', async () => {
    ;(mockGetMissing as jest.Mock).mockResolvedValue({ data: { data: MOCK_MISSING } })
    const { result } = renderHook(() => useMissing(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data?.available_now).toHaveLength(1)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=useReadiness --watchAll=false
```

Expected: FAIL — `Cannot find module '@/lib/hooks/useReadiness'`

- [ ] **Step 3: Create `frontend/lib/hooks/useReadiness.ts`**

```ts
// frontend/lib/hooks/useReadiness.ts
'use client'

import { useQuery } from '@tanstack/react-query'
import { getReadiness, getMissing } from '@/lib/api/readiness'
import type { ReadinessData, MissingData } from '@/lib/api/types'

export function useReadiness() {
  const { data, isLoading, isError } = useQuery<ReadinessData>({
    queryKey: ['readiness'],
    queryFn: () => getReadiness().then((r) => r.data.data),
    refetchInterval: (query) =>
      query.state.data?.is_stale ? 3_000 : 30_000,
  })
  return { data, isLoading, isError }
}

export function useMissing() {
  const { data, isLoading, isError } = useQuery<MissingData>({
    queryKey: ['readiness', 'missing'],
    queryFn: () => getMissing().then((r) => r.data.data),
  })
  return { data, isLoading, isError }
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=useReadiness --watchAll=false
```

Expected: `PASS __tests__/useReadiness.test.tsx` — 4 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/__tests__/useReadiness.test.tsx frontend/lib/hooks/useReadiness.ts
git commit -m "feat: add useReadiness and useMissing hooks — React Query with stale polling"
```

---

## Task 3: `StatusBadge` component (TDD)

**Files:**
- Create: `frontend/__tests__/StatusBadge.test.tsx`
- Create: `frontend/components/shared/StatusBadge.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/__tests__/StatusBadge.test.tsx
import { render, screen } from '@testing-library/react'
import StatusBadge from '@/components/shared/StatusBadge'

describe('StatusBadge', () => {
  it('confirmed → "Ready" with ready colour class', () => {
    render(<StatusBadge status="confirmed" />)
    const badge = screen.getByText('Ready')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('text-ready')
  })

  it('needs_user_review → "Needs your look" with review colour class', () => {
    render(<StatusBadge status="needs_user_review" />)
    const badge = screen.getByText('Needs your look')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('text-review')
  })

  it('needs_agent_review → "Agent review" with agent colour class', () => {
    render(<StatusBadge status="needs_agent_review" />)
    expect(screen.getByText('Agent review')).toHaveClass('text-agent')
  })

  it('high_risk → "Flag to review" with risk-high colour class', () => {
    render(<StatusBadge status="high_risk" />)
    expect(screen.getByText('Flag to review')).toHaveClass('text-risk-high')
  })

  it('out_of_scope → "Specialist area" with agent colour class', () => {
    render(<StatusBadge status="out_of_scope" />)
    expect(screen.getByText('Specialist area')).toHaveClass('text-agent')
  })

  it('missing → "Still needed" with muted colour class', () => {
    render(<StatusBadge status="missing" />)
    expect(screen.getByText('Still needed')).toHaveClass('text-text-muted')
  })

  it('duplicate → "Possible duplicate" with review colour class', () => {
    render(<StatusBadge status="duplicate" />)
    expect(screen.getByText('Possible duplicate')).toHaveClass('text-review')
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=StatusBadge --watchAll=false
```

Expected: FAIL — `Cannot find module '@/components/shared/StatusBadge'`

- [ ] **Step 3: Create `frontend/components/shared/StatusBadge.tsx`**

```tsx
// frontend/components/shared/StatusBadge.tsx
type BadgeStatus =
  | 'confirmed'
  | 'needs_user_review'
  | 'needs_agent_review'
  | 'high_risk'
  | 'out_of_scope'
  | 'missing'
  | 'duplicate'

const STATUS_CONFIG: Record<BadgeStatus, { label: string; classes: string }> = {
  confirmed:          { label: 'Ready',              classes: 'text-ready bg-ready-bg' },
  needs_user_review:  { label: 'Needs your look',    classes: 'text-review bg-review-bg' },
  needs_agent_review: { label: 'Agent review',       classes: 'text-agent bg-agent-bg' },
  high_risk:          { label: 'Flag to review',     classes: 'text-risk-high bg-risk-bg' },
  out_of_scope:       { label: 'Specialist area',    classes: 'text-agent bg-agent-bg' },
  missing:            { label: 'Still needed',       classes: 'text-text-muted bg-surface-raised' },
  duplicate:          { label: 'Possible duplicate', classes: 'text-review bg-review-bg' },
}

export type { BadgeStatus }

interface StatusBadgeProps {
  status: BadgeStatus
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.missing
  return (
    <span className={`inline-block rounded-full px-2 py-1 text-xs font-ui font-medium ${config.classes}`}>
      {config.label}
    </span>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=StatusBadge --watchAll=false
```

Expected: `PASS __tests__/StatusBadge.test.tsx` — 7 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/__tests__/StatusBadge.test.tsx frontend/components/shared/StatusBadge.tsx
git commit -m "feat: implement StatusBadge component — 7 status states with design tokens"
```

---

## Task 4: `ConfidenceBar` component (TDD)

**Files:**
- Create: `frontend/__tests__/ConfidenceBar.test.tsx`
- Create: `frontend/components/shared/ConfidenceBar.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/__tests__/ConfidenceBar.test.tsx
import { render, screen } from '@testing-library/react'
import ConfidenceBar from '@/components/shared/ConfidenceBar'

describe('ConfidenceBar', () => {
  it('0.95 → "High confidence"', () => {
    render(<ConfidenceBar confidence={0.95} />)
    expect(screen.getByText('High confidence')).toBeInTheDocument()
  })

  it('0.90 → "High confidence" (boundary)', () => {
    render(<ConfidenceBar confidence={0.90} />)
    expect(screen.getByText('High confidence')).toBeInTheDocument()
  })

  it('0.80 → "Moderate"', () => {
    render(<ConfidenceBar confidence={0.80} />)
    expect(screen.getByText('Moderate')).toBeInTheDocument()
  })

  it('0.70 → "Moderate" (boundary)', () => {
    render(<ConfidenceBar confidence={0.70} />)
    expect(screen.getByText('Moderate')).toBeInTheDocument()
  })

  it('0.60 → "Uncertain"', () => {
    render(<ConfidenceBar confidence={0.60} />)
    expect(screen.getByText('Uncertain')).toBeInTheDocument()
  })

  it('0.30 → "Needs review"', () => {
    render(<ConfidenceBar confidence={0.30} />)
    expect(screen.getByText('Needs review')).toBeInTheDocument()
  })

  it('bar fill has bg-ready class for high confidence', () => {
    const { container } = render(<ConfidenceBar confidence={0.95} />)
    const bar = container.querySelector('[data-testid="confidence-fill"]')
    expect(bar).toHaveClass('bg-ready')
  })

  it('bar fill has bg-agent class for low confidence', () => {
    const { container } = render(<ConfidenceBar confidence={0.30} />)
    const bar = container.querySelector('[data-testid="confidence-fill"]')
    expect(bar).toHaveClass('bg-agent')
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=ConfidenceBar --watchAll=false
```

Expected: FAIL — `Cannot find module '@/components/shared/ConfidenceBar'`

- [ ] **Step 3: Create `frontend/components/shared/ConfidenceBar.tsx`**

```tsx
// frontend/components/shared/ConfidenceBar.tsx
interface ConfidenceBarProps {
  confidence: number  // 0.0–1.0
}

interface ConfidenceConfig {
  label: string
  fillClass: string
  widthPercent: number
}

function getConfig(confidence: number): ConfidenceConfig {
  if (confidence >= 0.90) return { label: 'High confidence', fillClass: 'bg-ready',      widthPercent: 100 }
  if (confidence >= 0.70) return { label: 'Moderate',        fillClass: 'bg-text-muted', widthPercent: 70  }
  if (confidence >= 0.50) return { label: 'Uncertain',       fillClass: 'bg-review',     widthPercent: 50  }
  return                         { label: 'Needs review',    fillClass: 'bg-agent',      widthPercent: 25  }
}

export default function ConfidenceBar({ confidence }: ConfidenceBarProps) {
  const { label, fillClass, widthPercent } = getConfig(confidence)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-progress-track rounded-full overflow-hidden">
        <div
          data-testid="confidence-fill"
          className={`h-full rounded-full ${fillClass}`}
          style={{ width: `${widthPercent}%` }}
        />
      </div>
      <span className="text-xs font-ui text-text-muted whitespace-nowrap">{label}</span>
    </div>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=ConfidenceBar --watchAll=false
```

Expected: `PASS __tests__/ConfidenceBar.test.tsx` — 8 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/__tests__/ConfidenceBar.test.tsx frontend/components/shared/ConfidenceBar.tsx
git commit -m "feat: implement ConfidenceBar — 4 confidence ranges with humanised labels"
```

---

## Task 5: `ReadinessRing` component (TDD)

**Files:**
- Create: `frontend/__tests__/ReadinessRing.test.tsx`
- Create: `frontend/components/readiness/ReadinessRing.tsx`

Note: the `components/readiness/` directory does not exist yet. Create it along with the file.

- [ ] **Step 1: Write failing test**

```tsx
// frontend/__tests__/ReadinessRing.test.tsx
import { render, screen } from '@testing-library/react'
import ReadinessRing from '@/components/readiness/ReadinessRing'

describe('ReadinessRing', () => {
  it('renders the percentage number in the centre', () => {
    render(<ReadinessRing percentage={72} />)
    expect(screen.getByText('72%')).toBeInTheDocument()
  })

  it('renders 0% correctly', () => {
    render(<ReadinessRing percentage={0} />)
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('renders 100% correctly', () => {
    render(<ReadinessRing percentage={100} />)
    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('progress arc has stroke-ready class (sage green)', () => {
    const { container } = render(<ReadinessRing percentage={50} />)
    const arc = container.querySelector('[data-testid="ring-progress"]')
    expect(arc).toHaveClass('stroke-ready')
  })

  it('background track has stroke-progress-track class', () => {
    const { container } = render(<ReadinessRing percentage={50} />)
    const track = container.querySelector('[data-testid="ring-track"]')
    expect(track).toHaveClass('stroke-progress-track')
  })

  it('SVG has aria-label with percentage', () => {
    const { container } = render(<ReadinessRing percentage={72} />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('aria-label', '72% ready')
  })

  it('clamps values above 100 to 100', () => {
    render(<ReadinessRing percentage={150} />)
    expect(screen.getByText('150%')).toBeInTheDocument()
    // SVG offset clamped so it still renders without crashing
    const { container } = render(<ReadinessRing percentage={150} />)
    expect(container.querySelector('[data-testid="ring-progress"]')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=ReadinessRing --watchAll=false
```

Expected: FAIL — `Cannot find module '@/components/readiness/ReadinessRing'`

- [ ] **Step 3: Create `frontend/components/readiness/ReadinessRing.tsx`**

```tsx
// frontend/components/readiness/ReadinessRing.tsx
interface ReadinessRingProps {
  percentage: number    // 0–100 (values outside range are displayed as-is but clamped for SVG)
  size?: number         // SVG size in px, default 200
  strokeWidth?: number  // ring thickness, default 12
}

export default function ReadinessRing({
  percentage,
  size = 200,
  strokeWidth = 12,
}: ReadinessRingProps) {
  const cx = size / 2
  const cy = size / 2
  const radius = (size - strokeWidth * 2) / 2
  const circumference = 2 * Math.PI * radius
  const clamped = Math.min(100, Math.max(0, percentage))
  const offset = circumference - (clamped / 100) * circumference

  return (
    <svg
      width={size}
      height={size}
      aria-label={`${percentage}% ready`}
      role="img"
    >
      {/* Background track */}
      <circle
        data-testid="ring-track"
        cx={cx}
        cy={cy}
        r={radius}
        fill="none"
        strokeWidth={strokeWidth}
        className="stroke-progress-track"
      />
      {/* Progress arc — rotated so 0° starts at top */}
      <circle
        data-testid="ring-progress"
        cx={cx}
        cy={cy}
        r={radius}
        fill="none"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        className="stroke-ready"
        strokeDasharray={`${circumference} ${circumference}`}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: 'stroke-dashoffset 600ms ease' }}
      />
      {/* Centre: percentage number */}
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="central"
        className="fill-ready font-mono text-3xl font-bold"
      >
        {percentage}%
      </text>
    </svg>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=ReadinessRing --watchAll=false
```

Expected: `PASS __tests__/ReadinessRing.test.tsx` — 7 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/__tests__/ReadinessRing.test.tsx frontend/components/readiness/ReadinessRing.tsx
git commit -m "feat: implement ReadinessRing SVG component — stroke-dasharray animation, sage green"
```

---

## Task 6: `SkillBreakdown` component (TDD)

**Files:**
- Create: `frontend/__tests__/SkillBreakdown.test.tsx`
- Create: `frontend/components/readiness/SkillBreakdown.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/__tests__/SkillBreakdown.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SkillBreakdown from '@/components/readiness/SkillBreakdown'
import type { SkillBreakdownItem } from '@/lib/api/types'

const MOCK_BREAKDOWN: SkillBreakdownItem[] = [
  { skill_id: 'employee_tax_au', percentage: 80, achieved_weight: 4, total_weight: 5 },
  { skill_id: 'wfh_skill',       percentage: 60, achieved_weight: 3, total_weight: 5 },
]

describe('SkillBreakdown', () => {
  it('renders each skill row with display name and percentage', () => {
    render(<SkillBreakdown breakdown={MOCK_BREAKDOWN} />)
    expect(screen.getByText('Employee Tax')).toBeInTheDocument()
    expect(screen.getByText('Work From Home')).toBeInTheDocument()
    expect(screen.getByText('80%')).toBeInTheDocument()
    expect(screen.getByText('60%')).toBeInTheDocument()
  })

  it('falls back to skill_id when display name is not mapped', () => {
    const breakdown: SkillBreakdownItem[] = [
      { skill_id: 'unknown_skill', percentage: 50, achieved_weight: 1, total_weight: 2 },
    ]
    render(<SkillBreakdown breakdown={breakdown} />)
    expect(screen.getByText('unknown_skill')).toBeInTheDocument()
  })

  it('renders no rows when breakdown is empty', () => {
    render(<SkillBreakdown breakdown={[]} />)
    expect(screen.queryByRole('listitem')).not.toBeInTheDocument()
  })

  it('collapses and expands the list when toggle is clicked', async () => {
    const user = userEvent.setup()
    render(<SkillBreakdown breakdown={MOCK_BREAKDOWN} />)
    // Starts expanded — items visible
    expect(screen.getByText('Employee Tax')).toBeInTheDocument()
    // Click to collapse
    await user.click(screen.getByRole('button', { name: /per-skill breakdown/i }))
    expect(screen.queryByText('Employee Tax')).not.toBeInTheDocument()
    // Click to expand again
    await user.click(screen.getByRole('button', { name: /per-skill breakdown/i }))
    expect(screen.getByText('Employee Tax')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=SkillBreakdown --watchAll=false
```

Expected: FAIL — `Cannot find module '@/components/readiness/SkillBreakdown'`

- [ ] **Step 3: Create `frontend/components/readiness/SkillBreakdown.tsx`**

```tsx
// frontend/components/readiness/SkillBreakdown.tsx
'use client'

import { useState } from 'react'
import type { SkillBreakdownItem } from '@/lib/api/types'

const SKILL_LABELS: Record<string, string> = {
  employee_tax_au: 'Employee Tax',
  wfh_skill:       'Work From Home',
  investment_skill:'Investments',
  crypto_skill:    'Crypto',
}

interface SkillBreakdownProps {
  breakdown: SkillBreakdownItem[]
}

export default function SkillBreakdown({ breakdown }: SkillBreakdownProps) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-2 text-sm font-ui font-medium text-text-body hover:text-text-primary transition-colors"
        aria-expanded={expanded}
      >
        Per-skill breakdown
        <span className="text-text-faint text-xs">{expanded ? '▴' : '▾'}</span>
      </button>

      {expanded && breakdown.length > 0 && (
        <ul className="mt-3 space-y-2">
          {breakdown.map((item) => (
            <li key={item.skill_id} className="flex items-center gap-3">
              <span className="text-sm font-ui text-text-muted flex-1 min-w-0 truncate">
                {SKILL_LABELS[item.skill_id] ?? item.skill_id}
              </span>
              <div className="flex-1 h-1 bg-progress-track rounded-full overflow-hidden">
                <div
                  className="h-full bg-progress-fill rounded-full"
                  style={{ width: `${item.percentage}%` }}
                />
              </div>
              <span className="text-xs font-mono text-text-muted shrink-0">
                {item.percentage}%
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=SkillBreakdown --watchAll=false
```

Expected: `PASS __tests__/SkillBreakdown.test.tsx` — 4 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/__tests__/SkillBreakdown.test.tsx frontend/components/readiness/SkillBreakdown.tsx
git commit -m "feat: implement SkillBreakdown — expandable list with mini progress bars"
```

---

## Task 7: `MissingEvidenceList` component (TDD)

**Files:**
- Create: `frontend/__tests__/MissingEvidenceList.test.tsx`
- Create: `frontend/components/readiness/MissingEvidenceList.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/__tests__/MissingEvidenceList.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MissingEvidenceList from '@/components/readiness/MissingEvidenceList'
import type { MissingItem } from '@/lib/api/types'

const NOW_ITEMS: MissingItem[] = [
  { requirement_id: 'receipt', display: 'Work receipts', weight: 1.0, skill_id: 'employee_tax_au', how_to_get: 'Collect receipts from purchases' },
  { requirement_id: 'invoice', display: 'Tax invoices', weight: 0.5, skill_id: 'employee_tax_au' },
]

const AFTER_FY_ITEMS: MissingItem[] = [
  { requirement_id: 'payg', display: 'PAYG payment summary', weight: 2.0, skill_id: 'employee_tax_au', how_to_get: 'Download from myGov after July' },
]

describe('MissingEvidenceList', () => {
  it('renders "Available now" section with items', () => {
    render(<MissingEvidenceList availableNow={NOW_ITEMS} availableAfterFY={[]} fyEndLabel="30 June 2025" />)
    expect(screen.getByText('Available now')).toBeInTheDocument()
    expect(screen.getByText('Work receipts')).toBeInTheDocument()
    expect(screen.getByText('Tax invoices')).toBeInTheDocument()
  })

  it('renders "Available after FY" section with end date', () => {
    render(<MissingEvidenceList availableNow={[]} availableAfterFY={AFTER_FY_ITEMS} fyEndLabel="30 June 2025" />)
    expect(screen.getByText(/available after 30 june 2025/i)).toBeInTheDocument()
    expect(screen.getByText('PAYG payment summary')).toBeInTheDocument()
  })

  it('renders how_to_get hint when present', () => {
    render(<MissingEvidenceList availableNow={NOW_ITEMS} availableAfterFY={[]} fyEndLabel="30 June 2025" />)
    expect(screen.getByText('Collect receipts from purchases')).toBeInTheDocument()
  })

  it('does not render "Available after FY" section when list is empty', () => {
    render(<MissingEvidenceList availableNow={NOW_ITEMS} availableAfterFY={[]} fyEndLabel="30 June 2025" />)
    expect(screen.queryByText(/available after/i)).not.toBeInTheDocument()
  })

  it('hides an item after "Skip for now" is clicked', async () => {
    const user = userEvent.setup()
    render(<MissingEvidenceList availableNow={NOW_ITEMS} availableAfterFY={[]} fyEndLabel="30 June 2025" />)
    expect(screen.getByText('Work receipts')).toBeInTheDocument()
    const skipButtons = screen.getAllByRole('button', { name: /skip for now/i })
    await user.click(skipButtons[0])
    expect(screen.queryByText('Work receipts')).not.toBeInTheDocument()
    // Other item still visible
    expect(screen.getByText('Tax invoices')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=MissingEvidenceList --watchAll=false
```

Expected: FAIL — `Cannot find module '@/components/readiness/MissingEvidenceList'`

- [ ] **Step 3: Create `frontend/components/readiness/MissingEvidenceList.tsx`**

```tsx
// frontend/components/readiness/MissingEvidenceList.tsx
'use client'

import { useState } from 'react'
import type { MissingItem } from '@/lib/api/types'

interface MissingEvidenceListProps {
  availableNow: MissingItem[]
  availableAfterFY: MissingItem[]
  fyEndLabel: string  // e.g., "30 June 2025"
}

function WeightPill({ weight }: { weight: number }) {
  const label = weight >= 2 ? 'High priority' : weight >= 1 ? 'Medium' : 'Low'
  const classes = weight >= 2 ? 'text-review bg-review-bg' : 'text-text-muted bg-surface-raised'
  return (
    <span className={`inline-block rounded-full px-2 py-1 text-xs font-ui ${classes}`}>
      {label}
    </span>
  )
}

function MissingItem({
  item,
  onSkip,
}: {
  item: MissingItem
  onSkip: (id: string) => void
}) {
  return (
    <li className="flex items-start justify-between gap-4 py-3 border-b border-border last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-ui text-text-body">{item.display}</span>
          <WeightPill weight={item.weight} />
        </div>
        {item.how_to_get && (
          <p className="mt-1 text-xs font-ui text-text-muted">{item.how_to_get}</p>
        )}
      </div>
      <button
        type="button"
        onClick={() => onSkip(item.requirement_id)}
        className="shrink-0 text-xs font-ui text-text-faint hover:text-text-muted transition-colors"
      >
        Skip for now
      </button>
    </li>
  )
}

export default function MissingEvidenceList({
  availableNow,
  availableAfterFY,
  fyEndLabel,
}: MissingEvidenceListProps) {
  const [skipped, setSkipped] = useState<Set<string>>(new Set())

  const skip = (id: string) =>
    setSkipped((prev) => new Set([...prev, id]))

  const visibleNow = availableNow.filter((i) => !skipped.has(i.requirement_id))
  const visibleAfterFY = availableAfterFY.filter((i) => !skipped.has(i.requirement_id))

  return (
    <div className="space-y-6">
      {visibleNow.length > 0 && (
        <section>
          <h3 className="text-sm font-ui font-medium text-text-muted uppercase tracking-wide mb-2">
            Available now
          </h3>
          <ul>
            {visibleNow.map((item) => (
              <MissingItem key={item.requirement_id} item={item} onSkip={skip} />
            ))}
          </ul>
        </section>
      )}

      {visibleAfterFY.length > 0 && (
        <section>
          <h3 className="text-sm font-ui font-medium text-text-muted uppercase tracking-wide mb-2">
            Available after {fyEndLabel}
          </h3>
          <ul>
            {visibleAfterFY.map((item) => (
              <MissingItem key={item.requirement_id} item={item} onSkip={skip} />
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=MissingEvidenceList --watchAll=false
```

Expected: `PASS __tests__/MissingEvidenceList.test.tsx` — 5 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/__tests__/MissingEvidenceList.test.tsx frontend/components/readiness/MissingEvidenceList.tsx
git commit -m "feat: implement MissingEvidenceList — two groups, skip button, weight pill, how_to_get"
```

---

## Task 8: Readiness page (TDD)

**Files:**
- Create: `frontend/__tests__/readiness-page.test.tsx`
- Modify: `frontend/app/(dashboard)/readiness/page.tsx`

The readiness page:
- Calls `useReadiness()` for data
- Loading state: skeleton placeholder text
- Stale: spinner + "Updating…" indicator
- Shows `ReadinessRing` with `percentage`
- Sub-indicators: review count, agent count, missing count
- CTA button: "Continue your tax journey →" — links to `/journey`
- Empty state (percentage === 0): "Upload your first document to get started"
- Full state (percentage === 100): "Your tax review package is ready"
- `SkillBreakdown` when breakdown is non-empty
- FY-aware banner: if current date < FY end date, show "Some evidence types become available after {fyEndLabel}" note
- `Disclaimer` at the bottom (AI output surface)

- [ ] **Step 1: Write failing tests**

```tsx
// frontend/__tests__/readiness-page.test.tsx
import { render, screen } from '@testing-library/react'
import ReadinessPage from '@/app/(dashboard)/readiness/page'

jest.mock('@/lib/hooks/useReadiness', () => ({
  useReadiness: jest.fn(),
  __esModule: true,
}))

jest.mock('@/lib/stores/workspace.store', () => ({
  default: () => ({
    workspaceId: 'ws-1',
    financialYear: '2024-25',
    isAuthenticated: true,
    isUnlocked: true,
  }),
  __esModule: true,
}))

import { useReadiness as mockUseReadiness } from '@/lib/hooks/useReadiness'

const MOCK_DATA = {
  percentage: 72,
  breakdown: [{ skill_id: 'employee_tax_au', percentage: 80, achieved_weight: 4, total_weight: 5 }],
  missing_items_count: 2,
  review_items_count: 3,
  agent_items_count: 1,
  is_stale: false,
  calculated_at: '2026-05-20T10:00:00+00:00',
}

beforeEach(() => jest.clearAllMocks())

describe('ReadinessPage', () => {
  it('shows loading state while data is fetching', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: true, data: undefined, isError: false })
    render(<ReadinessPage />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('shows readiness ring with correct percentage', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    render(<ReadinessPage />)
    expect(screen.getByText('72%')).toBeInTheDocument()
  })

  it('shows stale indicator when is_stale is true', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({
      isLoading: false,
      data: { ...MOCK_DATA, is_stale: true },
      isError: false,
    })
    render(<ReadinessPage />)
    expect(screen.getByText(/updating/i)).toBeInTheDocument()
  })

  it('shows CTA button linking to /journey', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    render(<ReadinessPage />)
    const cta = screen.getByRole('link', { name: /continue your tax journey/i })
    expect(cta).toHaveAttribute('href', '/journey')
  })

  it('shows empty state message when percentage is 0', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({
      isLoading: false,
      data: { ...MOCK_DATA, percentage: 0 },
      isError: false,
    })
    render(<ReadinessPage />)
    expect(screen.getByText(/upload your first document/i)).toBeInTheDocument()
  })

  it('shows ready message when percentage is 100', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({
      isLoading: false,
      data: { ...MOCK_DATA, percentage: 100 },
      isError: false,
    })
    render(<ReadinessPage />)
    expect(screen.getByText(/your tax review package is ready/i)).toBeInTheDocument()
  })

  it('shows sub-indicators for review, agent, and missing counts', () => {
    ;(mockUseReadiness as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_DATA, isError: false })
    render(<ReadinessPage />)
    expect(screen.getByText(/3.*need.*your review|your review.*3/i)).toBeInTheDocument()
    expect(screen.getByText(/1.*agent|agent.*1/i)).toBeInTheDocument()
    expect(screen.getByText(/2.*missing|missing.*2/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=readiness-page --watchAll=false
```

Expected: FAIL — page is a stub.

- [ ] **Step 3: Rewrite `frontend/app/(dashboard)/readiness/page.tsx`**

```tsx
// frontend/app/(dashboard)/readiness/page.tsx
'use client'

import Link from 'next/link'
import ReadinessRing from '@/components/readiness/ReadinessRing'
import SkillBreakdown from '@/components/readiness/SkillBreakdown'
import Disclaimer from '@/components/shared/Disclaimer'
import { useReadiness } from '@/lib/hooks/useReadiness'
import useWorkspaceStore from '@/lib/stores/workspace.store'

function getFYEndLabel(fy: string): string {
  const endYear = parseInt(fy.split('-')[1]) + 2000
  return `30 June ${endYear}`
}

function isFYActive(fy: string): boolean {
  const endYear = parseInt(fy.split('-')[1]) + 2000
  return new Date() < new Date(endYear, 5, 30)
}

export default function ReadinessPage() {
  const { data, isLoading } = useReadiness()
  const { financialYear } = useWorkspaceStore()

  if (isLoading || !data) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-text-muted">Loading your tax readiness…</p>
      </div>
    )
  }

  const fyLabel = financialYear ? getFYEndLabel(financialYear) : '30 June'
  const fyActive = financialYear ? isFYActive(financialYear) : false

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">
          Tax Readiness
        </h1>
        {data.is_stale && (
          <p className="mt-1 text-xs font-ui text-text-muted flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-review animate-pulse" />
            Updating…
          </p>
        )}
      </div>

      {/* Readiness ring + sub-indicators */}
      <div className="bg-surface rounded-lg shadow-sm p-6 flex flex-col items-center gap-6">
        <ReadinessRing percentage={data.percentage} />

        {/* State messages */}
        {data.percentage === 0 && (
          <p className="text-sm font-ui text-text-muted text-center">
            Upload your first document to get started
          </p>
        )}
        {data.percentage === 100 && (
          <p className="text-sm font-ui text-ready font-medium text-center">
            Your tax review package is ready
          </p>
        )}

        {/* Sub-indicators */}
        <div className="w-full grid grid-cols-1 gap-2">
          {data.review_items_count > 0 && (
            <p className="text-sm font-ui text-review">
              🟡 {data.review_items_count} item{data.review_items_count !== 1 ? 's' : ''} need your review
            </p>
          )}
          {data.agent_items_count > 0 && (
            <p className="text-sm font-ui text-agent">
              🔴 {data.agent_items_count} item{data.agent_items_count !== 1 ? 's' : ''} need a tax agent
            </p>
          )}
          {data.missing_items_count > 0 && (
            <p className="text-sm font-ui text-text-muted">
              ⬜ {data.missing_items_count} piece{data.missing_items_count !== 1 ? 's' : ''} of evidence still missing
            </p>
          )}
        </div>

        {/* CTA */}
        <Link
          href="/journey"
          className="inline-block px-6 py-3 rounded-md bg-accent hover:bg-accent-hover text-white font-ui font-medium text-sm transition-colors"
        >
          Continue your tax journey →
        </Link>
      </div>

      {/* Per-skill breakdown */}
      {data.breakdown.length > 0 && (
        <div className="bg-surface rounded-lg shadow-sm p-6">
          <SkillBreakdown breakdown={data.breakdown} />
        </div>
      )}

      {/* FY-aware banner */}
      {fyActive && data.missing_items_count > 0 && (
        <div className="bg-review-bg rounded-md px-4 py-3">
          <p className="text-sm font-ui text-review">
            Some evidence types become available after {fyLabel}. We&apos;ll remind you when the financial year ends.
          </p>
        </div>
      )}

      <Disclaimer />
    </div>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=readiness-page --watchAll=false
```

Expected: `PASS __tests__/readiness-page.test.tsx` — 7 tests passing.

**If sub-indicator test fails** because the regex `/3.*need.*your review/i` doesn't match, check the exact text rendered. The component renders: `"3 items need your review"`. Adjust the regex if needed: `screen.getByText('3 items need your review')`.

- [ ] **Step 5: Commit**

```bash
git add "frontend/__tests__/readiness-page.test.tsx" "frontend/app/(dashboard)/readiness/page.tsx"
git commit -m "feat: implement Tax Readiness page — ring, sub-indicators, FY banner, CTA"
```

---

## Task 9: Missing evidence page (TDD)

**Files:**
- Create: `frontend/__tests__/missing-page.test.tsx`
- Create: `frontend/app/(dashboard)/readiness/missing/page.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
// frontend/__tests__/missing-page.test.tsx
import { render, screen } from '@testing-library/react'
import MissingPage from '@/app/(dashboard)/readiness/missing/page'

jest.mock('@/lib/hooks/useReadiness', () => ({
  useMissing: jest.fn(),
  __esModule: true,
}))

jest.mock('@/lib/stores/workspace.store', () => ({
  default: () => ({
    workspaceId: 'ws-1',
    financialYear: '2024-25',
  }),
  __esModule: true,
}))

import { useMissing as mockUseMissing } from '@/lib/hooks/useReadiness'

const MOCK_MISSING = {
  available_now: [
    { requirement_id: 'receipt', display: 'Work receipts', weight: 1.0, skill_id: 'employee_tax_au', how_to_get: 'Keep your receipts' },
  ],
  available_after_fy: [
    { requirement_id: 'payg', display: 'PAYG payment summary', weight: 2.0, skill_id: 'employee_tax_au', how_to_get: 'Download from myGov' },
  ],
}

beforeEach(() => jest.clearAllMocks())

describe('MissingPage', () => {
  it('shows loading state while data is fetching', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: true, data: undefined })
    render(<MissingPage />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('shows page heading', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_MISSING })
    render(<MissingPage />)
    expect(screen.getByRole('heading', { name: /missing evidence/i })).toBeInTheDocument()
  })

  it('renders available now items', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_MISSING })
    render(<MissingPage />)
    expect(screen.getByText('Work receipts')).toBeInTheDocument()
  })

  it('renders available after FY items', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_MISSING })
    render(<MissingPage />)
    expect(screen.getByText('PAYG payment summary')).toBeInTheDocument()
  })

  it('shows empty state when both lists are empty', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({
      isLoading: false,
      data: { available_now: [], available_after_fy: [] },
    })
    render(<MissingPage />)
    expect(screen.getByText(/nothing missing/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=missing-page --watchAll=false
```

Expected: FAIL — `Cannot find module '@/app/(dashboard)/readiness/missing/page'`

- [ ] **Step 3: Create `frontend/app/(dashboard)/readiness/missing/page.tsx`**

```tsx
// frontend/app/(dashboard)/readiness/missing/page.tsx
'use client'

import Link from 'next/link'
import MissingEvidenceList from '@/components/readiness/MissingEvidenceList'
import { useMissing } from '@/lib/hooks/useReadiness'
import useWorkspaceStore from '@/lib/stores/workspace.store'

function getFYEndLabel(fy: string): string {
  const endYear = parseInt(fy.split('-')[1]) + 2000
  return `30 June ${endYear}`
}

export default function MissingPage() {
  const { data, isLoading } = useMissing()
  const { financialYear } = useWorkspaceStore()

  if (isLoading || !data) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-text-muted">Loading missing items…</p>
      </div>
    )
  }

  const fyLabel = financialYear ? getFYEndLabel(financialYear) : '30 June'
  const totalMissing = data.available_now.length + data.available_after_fy.length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-semibold text-text-primary">
          Missing Evidence
        </h1>
        <Link href="/readiness" className="text-sm font-ui text-text-muted hover:text-text-body transition-colors">
          ← Back to readiness
        </Link>
      </div>

      {totalMissing === 0 ? (
        <div className="bg-ready-bg rounded-lg p-8 text-center">
          <p className="text-sm font-ui text-ready font-medium">
            Nothing missing — you&apos;ve provided all available evidence.
          </p>
        </div>
      ) : (
        <MissingEvidenceList
          availableNow={data.available_now}
          availableAfterFY={data.available_after_fy}
          fyEndLabel={fyLabel}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=missing-page --watchAll=false
```

Expected: `PASS __tests__/missing-page.test.tsx` — 5 tests passing.

- [ ] **Step 5: Commit**

```bash
git add "frontend/__tests__/missing-page.test.tsx" "frontend/app/(dashboard)/readiness/missing/page.tsx"
git commit -m "feat: implement Missing Evidence page — two groups, empty state, back link"
```

---

## Task 10: Full test suite — verify all Phase 2 tests pass

- [ ] **Step 1: Run all frontend tests**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --watchAll=false
```

Expected: All tests pass. Phase 2 adds:

| Suite | Tests |
|-------|-------|
| `readiness-api.test.ts` | 3 |
| `useReadiness.test.tsx` | 4 |
| `StatusBadge.test.tsx` | 7 |
| `ConfidenceBar.test.tsx` | 8 |
| `ReadinessRing.test.tsx` | 7 |
| `SkillBreakdown.test.tsx` | 4 |
| `MissingEvidenceList.test.tsx` | 5 |
| `readiness-page.test.tsx` | 7 |
| `missing-page.test.tsx` | 5 |

Phase 2 total: **50 new tests** + Phase 1's **31** = **81 tests total**

- [ ] **Step 2: Run backend readiness tests**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend pytest tests/test_readiness.py -v
```

Expected: All readiness tests pass (the `how_to_get` addition is backward-compatible — adds a field, doesn't change existing fields).

- [ ] **Step 3: Final commit if any loose files remain**

```bash
git status
# if clean: nothing to do
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Task |
|-------------|------|
| `ReadinessRing` — SVG ring, stroke-dasharray, 600ms animation | Task 5 |
| `ReadinessRing` — `--color-ready` fill, `--color-progress-track` background | Task 5 |
| `ReadinessRing` — large % number centre, `--font-mono` | Task 5 |
| `StatusBadge` — all 7 status states from DESIGN.md §5 | Task 3 |
| `ConfidenceBar` — 4 ranges, humanised text, no raw numbers | Task 4 |
| `SkillBreakdown` — expandable, skill name + mini bar + % | Task 6 |
| `MissingEvidenceList` — two groups, weight pill, how_to_get, skip | Task 7 |
| `lib/api/readiness.ts` — getReadiness, getMissing, triggerRecalculate | Task 1 |
| `lib/hooks/useReadiness.ts` — 30s refetch, 3s stale polling | Task 2 |
| Readiness page — loading state | Task 8 |
| Readiness page — stale indicator (spinner + "Updating…") | Task 8 |
| Readiness page — ring + sub-indicators (review, agent, missing counts) | Task 8 |
| Readiness page — CTA "Continue your tax journey →" | Task 8 |
| Readiness page — empty state at 0% | Task 8 |
| Readiness page — 100% state message | Task 8 |
| Readiness page — FY-aware banner when FY active | Task 8 |
| Readiness page — `Disclaimer` component | Task 8 |
| Missing evidence page — two sections | Task 9 |
| Missing evidence page — "Skip for now" per item | Task 7 (component) |
| Missing evidence page — empty state | Task 9 |
| Backend: `how_to_get` in `/readiness/missing` response | Task 1 |

**Placeholder scan:** None. Every step has complete code.

**Type consistency:**
- `SkillBreakdownItem` defined in Task 1, imported in Tasks 6 and 8 — consistent.
- `MissingItem` defined in Task 1, imported in Tasks 7 and 9 — consistent.
- `ReadinessData` defined in Task 1, used in Task 2 — consistent.
- `useReadiness()` defined in Task 2, used in Task 8 — consistent.
- `useMissing()` defined in Task 2, used in Task 9 — consistent.
- `getFYEndLabel(fy)` defined independently in Tasks 8 and 9 — duplicated by design (YAGNI; no shared util file for two callsites).

**Explicit DO NOT build (confirmed absent):**
- No Interview UI
- No Document Upload
- No Review cards
- No data fetching inside components (all via hooks)
