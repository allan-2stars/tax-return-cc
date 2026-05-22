# M10 Phase 8: Integration + Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete every open gap from Phases 1–7 and add final polish: Danger Zone wiring, New Financial Year flow, deadline and network banners, loading skeletons, Tax Estimate section, onboarding fix, and PWA manifest.

**Architecture:** All new backend endpoints follow the existing repository pattern; frontend components use React Query for data and Zustand for auth state. No new DB tables — all new state fits in existing models (Workspace.status, TaxProfile copy).

**Tech Stack:** FastAPI + SQLAlchemy async, Next.js 14 App Router, React Query v5, Zustand, Tailwind design tokens from DESIGN.md.

---

## File Map

### Backend
| File | Change |
|------|--------|
| `backend/app/api/routes/auth.py` | Fix `GET /auth/session` + `POST /auth/login` response format (add financial_year, is_unlocked, user_lodger_type) |
| `backend/app/api/routes/workspaces.py` | Add `DELETE /{id}`, `POST /{id}/archive`, `POST /` (new FY) |
| `backend/tests/test_settings.py` | 13 new tests covering all new endpoints |

### Frontend
| File | Change |
|------|--------|
| `frontend/lib/api/types.ts` | Add `DeleteWorkspaceResult`, `CreateWorkspaceResult`, `TaxEstimateSummary`; extend `SessionData` |
| `frontend/lib/api/settings.ts` | Add `deleteWorkspace`, `archiveWorkspace`, `createWorkspace` |
| `frontend/lib/api/estimator.ts` | Create: `getEstimatorSummary` |
| `frontend/lib/utils/fy.ts` | Add `computeNextFY`, `daysUntilFYEnd`, `deadlineState` |
| `frontend/lib/stores/workspace.store.ts` | Add `userLodgerType: string \| null` field |
| `frontend/lib/hooks/useAuth.ts` | Set `userLodgerType` from session response |
| `frontend/components/settings/WorkspaceTab.tsx` | Wire Archive + Delete buttons |
| `frontend/components/settings/NewFYModal.tsx` | Create: new FY creation modal |
| `frontend/app/(dashboard)/layout.tsx` | Open NewFYModal from FY switcher; render DeadlineBanner + NetworkBanner |
| `frontend/components/shared/DeadlineBanner.tsx` | Create: amber/terracotta FY deadline banner |
| `frontend/components/shared/NetworkBanner.tsx` | Create: offline detection banner with health polling |
| `frontend/app/(dashboard)/readiness/page.tsx` | Replace spinner with skeleton; add TaxEstimate section |
| `frontend/app/(dashboard)/review/page.tsx` | Replace spinner with skeleton |
| `frontend/app/(dashboard)/evidence/page.tsx` | Replace spinner with skeleton |
| `frontend/components/readiness/TaxEstimate.tsx` | Create: tax estimate section |
| `frontend/app/(auth)/setup/page.tsx` | Add FY-selection step; call `setWorkspace` after confirm |
| `frontend/public/manifest.json` | Create: PWA manifest |
| `frontend/app/layout.tsx` | Add `<link rel="manifest">` |
| `frontend/__tests__/settings-page.test.tsx` | Extend: 6 new WorkspaceTab + NewFYModal tests |
| `frontend/__tests__/DeadlineBanner.test.tsx` | Create: 5 tests |
| `frontend/__tests__/NetworkBanner.test.tsx` | Create: 4 tests |
| `frontend/__tests__/TaxEstimate.test.tsx` | Create: 4 tests |
| `frontend/__tests__/setup.test.tsx` | Extend: 2 new tests |

---

## Task 1: Backend — Session/Login fix + Danger Zone

**Files:**
- Modify: `backend/app/api/routes/auth.py`
- Modify: `backend/app/api/routes/workspaces.py`
- Modify: `backend/tests/test_settings.py`

### Background

`GET /auth/session` currently returns `{"authenticated": true, "workspace_id": "..."}` with no `data` wrapper. The frontend `useAuth` hook and login page both do `res.data.data.workspace_id` (the `ApiResponse<SessionData>` pattern), so the production app is broken. `POST /auth/login` has the same issue. Both endpoints must return `{"data": {...}, "status": "ok"}` including `financial_year`, `is_unlocked`, and `user_lodger_type`.

The Danger Zone in Settings had Archive and Delete buttons disabled with `title="Coming soon"`. This task wires them up on the backend. Frontend wiring is Task 4.

### Step 1: Write failing tests

- [ ] In `backend/tests/test_settings.py`, add to the **imports** block:

```python
from sqlalchemy import select
from app.db.models import TaxProfile
```

- [ ] Append these 8 tests to `test_settings.py` (after the existing tests, inside the file — no new class wrapper needed):

```python
# ── Session / login format fix ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_returns_data_wrapper(client):
    res = await client.get("/api/v1/auth/session")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "status" in body
    assert body["status"] == "ok"
    assert "workspace_id" in body["data"]
    assert "financial_year" in body["data"]
    assert "is_unlocked" in body["data"]
    assert "user_lodger_type" in body["data"]


@pytest.mark.asyncio
async def test_login_returns_financial_year(client, db_session):
    res = await client.post("/api/v1/auth/login", json={"password": "testpassword"})
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "financial_year" in body["data"]
    assert body["data"]["financial_year"] == "2024-25"


# ── Archive workspace ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_archive_workspace_sets_status(client, workspace_id):
    res = await client.post(f"/api/v1/workspaces/{workspace_id}/archive")
    assert res.status_code == 200
    body = res.json()
    assert body["data"]["status"] == "archived"


@pytest.mark.asyncio
async def test_archive_workspace_forbidden_for_other(client):
    res = await client.post("/api/v1/workspaces/other-ws-id/archive")
    assert res.status_code == 403


# ── Delete workspace ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_workspace_success(client, workspace_id):
    res = await client.request(
        "DELETE",
        f"/api/v1/workspaces/{workspace_id}",
        json={"password": "testpassword"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "redirect_to" in body["data"]


@pytest.mark.asyncio
async def test_delete_workspace_wrong_password(client, workspace_id):
    res = await client.request(
        "DELETE",
        f"/api/v1/workspaces/{workspace_id}",
        json={"password": "wrongpassword"},
    )
    assert res.status_code == 400
    assert res.json()["error_code"] == "invalid_password"


@pytest.mark.asyncio
async def test_delete_workspace_no_other_workspaces_redirects_setup(client, workspace_id):
    res = await client.request(
        "DELETE",
        f"/api/v1/workspaces/{workspace_id}",
        json={"password": "testpassword"},
    )
    body = res.json()
    assert body["data"]["redirect_to"] == "/setup"


@pytest.mark.asyncio
async def test_delete_workspace_forbidden_for_other(client):
    res = await client.request(
        "DELETE",
        "/api/v1/workspaces/other-ws-id",
        json={"password": "testpassword"},
    )
    assert res.status_code == 403
```

- [ ] Run tests, confirm they all **FAIL**:

```bash
docker compose exec backend pytest tests/test_settings.py -v -k "session_returns_data or login_returns_financial or archive_workspace or delete_workspace" 2>&1 | tail -20
```

Expected: 8 FAILED

### Step 2: Fix GET /auth/session

- [ ] In `backend/app/api/routes/auth.py`, add `from sqlalchemy import select` to imports (if not present) and add `TaxProfile` to the `from app.db.models import` line.

- [ ] Replace the existing `session_status` function (lines ~121-123):

```python
@router.get("/auth/session")
async def session_status(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    ws = await db.get(Workspace, workspace_id)
    sec = await auth_repo.get_security(db, workspace_id)
    now = datetime.now(timezone.utc)
    is_unlocked = bool(
        sec
        and sec.unlock_session_token
        and sec.unlock_session_expires
        and sec.unlock_session_expires > now
    )
    profile_result = await db.execute(
        select(TaxProfile).where(TaxProfile.workspace_id == workspace_id).limit(1)
    )
    profile = profile_result.scalar_one_or_none()
    return {
        "data": {
            "workspace_id": workspace_id,
            "financial_year": ws.financial_year if ws else "2024-25",
            "is_unlocked": is_unlocked,
            "user_lodger_type": profile.user_lodger_type if profile else None,
        },
        "status": "ok",
    }
```

### Step 3: Fix POST /auth/login

- [ ] In `backend/app/api/routes/auth.py`, replace the return statement at the end of `login` (currently `return {"status": "ok", "workspace_id": workspace_id_for_session}`):

```python
    fin_year = workspace.financial_year if workspace else "2024-25"
    return {
        "data": {
            "workspace_id": workspace_id_for_session,
            "financial_year": fin_year,
            "is_unlocked": False,
        },
        "status": "ok",
    }
```

### Step 4: Add archive + delete endpoints to workspaces.py

- [ ] Open `backend/app/api/routes/workspaces.py`. Add these imports at the top:

```python
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth, sign_session
from app.config import settings
from app.db.base import get_db
from app.db.models import ReadinessScore, Workspace
from app.errors import error_response
from app.repositories import auth as auth_repo
```

(Replace the existing import block — `Response`, `sign_session`, `settings`, `auth_repo`, `bcrypt` are additions.)

- [ ] Add a local helper after the imports:

```python
def _cookie_secure() -> bool:
    return settings.ENVIRONMENT != "development"
```

- [ ] Add `DeleteWorkspaceRequest` to the existing `UpdateWorkspaceRequest` block:

```python
class DeleteWorkspaceRequest(BaseModel):
    password: str
```

- [ ] Append the two new endpoints after the existing `update_workspace` function:

```python
@router.post("/workspaces/{target_id}/archive")
async def archive_workspace(
    target_id: str,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if target_id != workspace_id:
        raise HTTPException(
            status_code=403,
            detail=error_response("forbidden", "Cannot archive another workspace.", retryable=False),
        )
    ws = await db.get(Workspace, target_id)
    if not ws:
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "Workspace not found.", retryable=False),
        )
    ws.status = "archived"
    await db.commit()
    return {"data": _ws_dict(ws, 0.0), "status": "ok"}


@router.delete("/workspaces/{target_id}")
async def delete_workspace(
    target_id: str,
    body: DeleteWorkspaceRequest,
    response: Response,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if target_id != workspace_id:
        raise HTTPException(
            status_code=403,
            detail=error_response("forbidden", "Cannot delete another workspace.", retryable=False),
        )
    ws = await db.get(Workspace, target_id)
    if not ws:
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "Workspace not found.", retryable=False),
        )
    sec = await auth_repo.get_security(db, workspace_id)
    if not sec or not bcrypt.checkpw(body.password.encode(), sec.password_hash.encode()):
        raise HTTPException(
            status_code=400,
            detail=error_response("invalid_password", "Incorrect password.", retryable=True),
        )
    ws.status = "deleted"
    await db.commit()
    rows = await db.execute(
        select(Workspace)
        .where(Workspace.status == "active", Workspace.id != target_id)
        .order_by(Workspace.created_at.desc())
        .limit(1)
    )
    other_ws = rows.scalar_one_or_none()
    if other_ws:
        max_age = settings.SESSION_MAX_AGE_DAYS * 86400
        response.set_cookie(
            "session",
            sign_session(other_ws.id),
            max_age=max_age,
            httponly=True,
            secure=_cookie_secure(),
            samesite="strict",
            path="/",
        )
        redirect_to = "/journey"
    else:
        response.delete_cookie("session", path="/")
        response.delete_cookie("unlock_session", path="/")
        redirect_to = "/setup"
    return {"data": {"redirect_to": redirect_to}, "status": "ok"}
```

### Step 5: Run tests and confirm they pass

- [ ] Run the 8 new tests:

```bash
docker compose exec backend pytest tests/test_settings.py -v -k "session_returns_data or login_returns_financial or archive_workspace or delete_workspace" 2>&1 | tail -15
```

Expected: 8 PASSED

- [ ] Run full backend test suite to confirm no regressions:

```bash
docker compose exec backend pytest tests/ -v 2>&1 | tail -10
```

Expected: all previously-passing tests still pass, total ~158

### Step 6: Commit

```bash
git add backend/app/api/routes/auth.py backend/app/api/routes/workspaces.py backend/tests/test_settings.py
git commit -m "feat: fix session/login response format + add archive/delete workspace endpoints"
```

---

## Task 2: Backend — POST /workspaces (New Financial Year)

**Files:**
- Modify: `backend/app/api/routes/workspaces.py`
- Modify: `backend/tests/test_settings.py`

### Background

When a user starts a new financial year, the app creates a fresh workspace, copies the TaxProfile fields that carry over year-to-year (employment type, resident status, lodger type, flags like has_wfh), and kicks off the YoY engine which suggests items from the prior year's confirmed deductions. The new session cookie switches the user to the new workspace.

### Step 1: Write failing tests

- [ ] Add these 5 tests to `backend/tests/test_settings.py`:

```python
# ── Create workspace (new FY) ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_workspace_success(client):
    res = await client.post(
        "/api/v1/workspaces",
        json={"name": "FY 2025-26", "financial_year": "2025-26"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["data"]["financial_year"] == "2025-26"
    assert body["data"]["name"] == "FY 2025-26"
    assert "yoy_count" in body["data"]


@pytest.mark.asyncio
async def test_create_workspace_duplicate_fy_rejected(client, workspace_id):
    res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Dupe", "financial_year": "2024-25"},
    )
    assert res.status_code == 409
    assert res.json()["error_code"] == "already_exists"


@pytest.mark.asyncio
async def test_create_workspace_invalid_fy_format(client):
    res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Bad", "financial_year": "2025"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_workspace_copies_taxprofile(client, workspace_id, db_session):
    from app.repositories import profiles as profiles_repo
    profile = await profiles_repo.get_by_workspace(db_session, workspace_id)
    await profiles_repo.update_fields(
        db_session, profile, {"employment_type": "full_time", "resident_status": "resident"}
    )
    res = await client.post(
        "/api/v1/workspaces",
        json={"name": "New FY", "financial_year": "2025-26"},
    )
    assert res.status_code == 200
    new_ws_id = res.json()["data"]["id"]
    new_profile = await profiles_repo.get_by_workspace(db_session, new_ws_id)
    assert new_profile.employment_type == "full_time"
    assert new_profile.resident_status == "resident"


@pytest.mark.asyncio
async def test_create_workspace_yoy_no_error_without_prior_fy(client):
    res = await client.post(
        "/api/v1/workspaces",
        json={"name": "YoY Test", "financial_year": "2026-27"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["yoy_count"] == 0
```

- [ ] Run and confirm 5 FAILED:

```bash
docker compose exec backend pytest tests/test_settings.py -v -k "create_workspace" 2>&1 | tail -10
```

### Step 2: Add POST /workspaces to workspaces.py

- [ ] Add imports to the top of `backend/app/api/routes/workspaces.py`:

```python
from app.engines.yoy import YoYEngine
from app.repositories import profiles as profiles_repo
```

- [ ] Add the request model after `DeleteWorkspaceRequest`:

```python
class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
```

- [ ] Append the new endpoint at the bottom of `workspaces.py`:

```python
@router.post("/workspaces")
async def create_workspace(
    body: CreateWorkspaceRequest,
    response: Response,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Workspace).where(Workspace.financial_year == body.financial_year)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=error_response(
                "already_exists",
                f"A workspace for {body.financial_year} already exists.",
                retryable=False,
            ),
        )

    new_ws = Workspace(
        name=body.name,
        financial_year=body.financial_year,
        status="active",
    )
    db.add(new_ws)
    await db.commit()
    await db.refresh(new_ws)

    current_profile = await profiles_repo.get_by_workspace(db, workspace_id)
    new_profile = await profiles_repo.get_or_create(db, new_ws.id, body.financial_year)
    if current_profile:
        copy_keys = [
            "employment_type", "resident_status", "user_lodger_type",
            "has_wfh", "has_investments", "has_crypto", "has_property",
            "has_private_health", "has_sole_trader", "has_spouse",
            "has_dependents",
        ]
        await profiles_repo.update_fields(
            db, new_profile, {k: getattr(current_profile, k) for k in copy_keys}
        )

    yoy = YoYEngine()
    suggestions = await yoy.generate_suggestions(new_ws.id, db)

    max_age = settings.SESSION_MAX_AGE_DAYS * 86400
    response.set_cookie(
        "session",
        sign_session(new_ws.id),
        max_age=max_age,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        path="/",
    )
    return {
        "data": {**_ws_dict(new_ws, 0.0), "yoy_count": len(suggestions)},
        "status": "ok",
    }
```

### Step 3: Run tests

- [ ] Run the 5 new tests:

```bash
docker compose exec backend pytest tests/test_settings.py -v -k "create_workspace" 2>&1 | tail -10
```

Expected: 5 PASSED

- [ ] Run full suite to confirm no regressions:

```bash
docker compose exec backend pytest tests/ -v 2>&1 | tail -5
```

### Step 4: Commit

```bash
git add backend/app/api/routes/workspaces.py backend/tests/test_settings.py
git commit -m "feat: add POST /workspaces — new FY workspace with TaxProfile copy + YoY suggestions"
```

---

## Task 3: Frontend API Layer

**Files:**
- Modify: `frontend/lib/api/types.ts`
- Modify: `frontend/lib/api/settings.ts`
- Create: `frontend/lib/api/estimator.ts`
- Modify: `frontend/lib/utils/fy.ts`
- Modify: `frontend/lib/stores/workspace.store.ts`
- Modify: `frontend/lib/hooks/useAuth.ts`

No new tests in this task — all coverage comes from component tests in Tasks 4–8.

### Step 1: Update types.ts

- [ ] In `frontend/lib/api/types.ts`, update `SessionData` to include `user_lodger_type`:

```typescript
export interface SessionData {
  workspace_id: string
  financial_year: string
  is_unlocked: boolean
  user_lodger_type?: string | null
}
```

- [ ] Append new types after the existing `WorkspaceListData` interface (look for it and add after):

```typescript
export interface DeleteWorkspaceResult {
  redirect_to: string
}

export interface CreateWorkspaceResult extends WorkspaceInfo {
  yoy_count: number
}

export interface TaxEstimateSummary {
  gross_income: string
  total_deductions: string
  taxable_income: string
  payg_withheld: string
  confirmed_only: boolean
  pending_count: number
  ato_calculator_url: string
  disclaimer: string
}
```

### Step 2: Update settings.ts

- [ ] In `frontend/lib/api/settings.ts`, add these three functions after the existing exports:

```typescript
export const deleteWorkspace = (id: string, password: string) =>
  client.delete<ApiResponse<DeleteWorkspaceResult>>(`/api/v1/workspaces/${id}`, {
    data: { password },
  })

export const archiveWorkspace = (id: string) =>
  client.post<ApiResponse<WorkspaceInfo>>(`/api/v1/workspaces/${id}/archive`)

export const createWorkspace = (name: string, financial_year: string) =>
  client.post<ApiResponse<CreateWorkspaceResult>>('/api/v1/workspaces', {
    name,
    financial_year,
  })
```

Also add the missing import for the new types at the top if not present:
```typescript
import type { ApiResponse, WorkspaceInfo, DeleteWorkspaceResult, CreateWorkspaceResult } from './types'
```

### Step 3: Create estimator.ts

- [ ] Create `frontend/lib/api/estimator.ts`:

```typescript
import client from './client'
import type { ApiResponse, TaxEstimateSummary } from './types'

export const getEstimatorSummary = () =>
  client.get<ApiResponse<TaxEstimateSummary>>('/api/v1/estimator/summary')
```

### Step 4: Update fy.ts

- [ ] In `frontend/lib/utils/fy.ts`, append three new exports:

```typescript
export function computeNextFY(fy: string): string {
  const start = parseInt(fy.split('-')[0])
  const next = start + 1
  return `${next}-${String(next + 1).slice(-2)}`
}

export function daysUntilFYEnd(fy: string): number {
  const endYear = parseInt(fy.split('-')[1]) + 2000
  const endDate = new Date(endYear, 5, 30) // June 30
  const now = new Date()
  return Math.ceil((endDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
}

export function deadlineState(fy: string): 'amber' | 'terracotta' | null {
  const days = daysUntilFYEnd(fy)
  if (days < 0) return null
  if (days <= 7) return 'terracotta'
  if (days <= 30) return 'amber'
  return null
}
```

### Step 5: Update workspace store

- [ ] In `frontend/lib/stores/workspace.store.ts`, add `userLodgerType` to the interface and state:

```typescript
interface WorkspaceStore {
  workspaceId: string | null
  financialYear: string | null
  userLodgerType: string | null
  isAuthenticated: boolean
  isUnlocked: boolean
  setWorkspace: (id: string, fy: string) => void
  setUserLodgerType: (type: string | null) => void
  setAuthenticated: (value: boolean) => void
  setUnlocked: (value: boolean) => void
}

const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  workspaceId: null,
  financialYear: null,
  userLodgerType: null,
  isAuthenticated: false,
  isUnlocked: false,
  setWorkspace: (id, fy) => set({ workspaceId: id, financialYear: fy }),
  setUserLodgerType: (type) => set({ userLodgerType: type }),
  setAuthenticated: (value) => set({ isAuthenticated: value }),
  setUnlocked: (value) => set({ isUnlocked: value }),
}))
```

### Step 6: Update useAuth hook

- [ ] In `frontend/lib/hooks/useAuth.ts`, update to set `userLodgerType`:

```typescript
export function useAuth() {
  const router = useRouter()
  const { setWorkspace, setAuthenticated, setUnlocked, setUserLodgerType, isAuthenticated } =
    useWorkspaceStore()

  useEffect(() => {
    getSession()
      .then((res) => {
        const { workspace_id, financial_year, is_unlocked, user_lodger_type } = res.data.data
        setWorkspace(workspace_id, financial_year)
        setAuthenticated(true)
        setUnlocked(is_unlocked)
        setUserLodgerType(user_lodger_type ?? null)
      })
      .catch((err: unknown) => {
        const errorCode = (
          err as {
            response?: { data?: { error_code?: string } }
          }
        )?.response?.data?.error_code
        if (errorCode === 'setup_not_confirmed') {
          router.replace('/setup')
        } else {
          router.replace('/login')
        }
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return { isAuthenticated }
}
```

### Step 7: Commit

```bash
git add frontend/lib/api/types.ts frontend/lib/api/settings.ts frontend/lib/api/estimator.ts \
        frontend/lib/utils/fy.ts frontend/lib/stores/workspace.store.ts frontend/lib/hooks/useAuth.ts
git commit -m "feat: add API functions, FY utilities, and userLodgerType to workspace store"
```

---

## Task 4: WorkspaceTab Danger Zone + NewFYModal + FY Switcher

**Files:**
- Modify: `frontend/components/settings/WorkspaceTab.tsx`
- Create: `frontend/components/settings/NewFYModal.tsx`
- Modify: `frontend/app/(dashboard)/layout.tsx`
- Modify: `frontend/__tests__/settings-page.test.tsx`

### Step 1: Write failing tests

- [ ] In `frontend/__tests__/settings-page.test.tsx`, add these tests inside the existing `describe('WorkspaceTab', ...)` block (or as a new describe). First check that `WorkspaceTab` is NOT mocked in this test file — if it is, add a new `describe('WorkspaceTab real', ...)` block that renders it directly:

```typescript
// Add a new describe block at the bottom of the file

import WorkspaceTab from '@/components/settings/WorkspaceTab'
import NewFYModal from '@/components/settings/NewFYModal'
import * as settingsApi from '@/lib/api/settings'
import * as authApi from '@/lib/api/auth'

jest.mock('@/lib/api/settings', () => ({
  ...jest.requireActual('@/lib/api/settings'),
  listWorkspaces: jest.fn(),
  updateWorkspaceName: jest.fn(),
  archiveWorkspace: jest.fn(),
  createWorkspace: jest.fn(),
  deleteWorkspace: jest.fn(),
}))
jest.mock('@/lib/api/auth')

const mockWs = { id: 'ws-1', name: 'My Return', financial_year: '2024-25', status: 'active', readiness_pct: 45 }

describe('WorkspaceTab danger zone', () => {
  beforeEach(() => {
    (settingsApi.listWorkspaces as jest.Mock).mockResolvedValue({
      data: { data: { items: [mockWs] } },
    })
    ;(settingsApi.updateWorkspaceName as jest.Mock).mockResolvedValue({
      data: { data: mockWs },
    })
  })

  it('archive button is enabled and calls archiveWorkspace', async () => {
    (settingsApi.archiveWorkspace as jest.Mock).mockResolvedValue({
      data: { data: { ...mockWs, status: 'archived' } },
    })
    render(<WorkspaceTab />)
    const btn = await screen.findByRole('button', { name: /archive/i })
    expect(btn).not.toBeDisabled()
    fireEvent.click(btn)
    await waitFor(() =>
      expect(settingsApi.archiveWorkspace).toHaveBeenCalledWith('ws-1')
    )
  })

  it('delete button opens password modal', async () => {
    render(<WorkspaceTab />)
    const btn = await screen.findByRole('button', { name: /delete workspace/i })
    fireEvent.click(btn)
    expect(await screen.findByLabelText(/password/i)).toBeInTheDocument()
  })

  it('delete confirms and calls deleteWorkspace', async () => {
    (settingsApi.deleteWorkspace as jest.Mock).mockResolvedValue({
      data: { data: { redirect_to: '/setup' } },
    })
    render(<WorkspaceTab />)
    fireEvent.click(await screen.findByRole('button', { name: /delete workspace/i }))
    const pwInput = await screen.findByLabelText(/password/i)
    fireEvent.change(pwInput, { target: { value: 'mypassword' } })
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }))
    await waitFor(() =>
      expect(settingsApi.deleteWorkspace).toHaveBeenCalledWith('ws-1', 'mypassword')
    )
  })
})

describe('NewFYModal', () => {
  it('renders with next FY pre-filled', () => {
    render(<NewFYModal currentFY="2024-25" onSuccess={jest.fn()} onCancel={jest.fn()} />)
    expect(screen.getByDisplayValue('2025-26')).toBeInTheDocument()
  })

  it('calls createWorkspace on submit', async () => {
    (settingsApi.createWorkspace as jest.Mock).mockResolvedValue({
      data: { data: { id: 'ws-2', name: 'New FY', financial_year: '2025-26', status: 'active', readiness_pct: 0, yoy_count: 0 } },
    })
    const onSuccess = jest.fn()
    render(<NewFYModal currentFY="2024-25" onSuccess={onSuccess} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /create/i }))
    await waitFor(() => expect(onSuccess).toHaveBeenCalled())
  })

  it('shows validation error for empty name', async () => {
    render(<NewFYModal currentFY="2024-25" onSuccess={jest.fn()} onCancel={jest.fn()} />)
    const nameInput = screen.getByLabelText(/workspace name/i)
    fireEvent.change(nameInput, { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: /create/i }))
    expect(await screen.findByText(/name is required/i)).toBeInTheDocument()
  })
})
```

- [ ] Run tests, confirm 6 FAIL:

```bash
docker compose exec frontend npx jest --testPathPattern="settings-page" 2>&1 | tail -20
```

### Step 2: Update WorkspaceTab

- [ ] In `frontend/components/settings/WorkspaceTab.tsx`, replace the Archive and Delete buttons in the Danger Zone section. Remove the `title="Coming soon"` and `disabled` attributes. Wire up actual functionality:

The current Danger Zone section (near the bottom of step-2 form) has two disabled buttons. Replace with:

```tsx
'use client'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import {
  listWorkspaces,
  updateWorkspaceName,
  archiveWorkspace,
  deleteWorkspace,
} from '@/lib/api/settings'
import type { WorkspaceInfo } from '@/lib/api/types'
import PasswordModal from './PasswordModal'

export default function WorkspaceTab() {
  const queryClient = useQueryClient()
  const router = useRouter()
  const [nameInput, setNameInput] = useState('')
  const [nameInitialized, setNameInitialized] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data: wsData } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => listWorkspaces().then((r) => r.data.data.items[0] as WorkspaceInfo | undefined),
  })

  useEffect(() => {
    if (wsData && !nameInitialized) {
      setNameInput(wsData.name)
      setNameInitialized(true)
    }
  }, [wsData, nameInitialized])

  const renameMutation = useMutation({
    mutationFn: (name: string) => updateWorkspaceName(wsData!.id, name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workspaces'] }),
  })

  const archiveMutation = useMutation({
    mutationFn: () => archiveWorkspace(wsData!.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workspaces'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (password: string) => deleteWorkspace(wsData!.id, password),
    onSuccess: (res) => {
      const redirectTo = res.data.data.redirect_to
      router.replace(redirectTo)
    },
  })

  async function handleDelete(password: string) {
    setDeleteError(null)
    try {
      await deleteMutation.mutateAsync(password)
      setShowDeleteModal(false)
    } catch {
      setDeleteError('Incorrect password or delete failed. Please try again.')
    }
  }

  if (!wsData) return null

  return (
    <div className="space-y-6">
      {/* Workspace name */}
      <div>
        <label htmlFor="ws-name" className="text-sm font-ui text-text-body block mb-1">
          Workspace name
        </label>
        <div className="flex gap-3">
          <input
            id="ws-name"
            type="text"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            className="flex-1 rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
            aria-label="Workspace name"
          />
          <button
            type="button"
            disabled={renameMutation.isPending || nameInput === wsData.name}
            onClick={() => renameMutation.mutate(nameInput)}
            className="px-4 py-2 rounded-md bg-accent text-white text-sm font-ui disabled:opacity-50"
          >
            {renameMutation.isPending ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>

      {/* Financial year (read only) */}
      <div>
        <p className="text-sm font-ui text-text-body mb-1">Financial year</p>
        <p aria-label="Financial year (read only)" className="text-sm font-mono text-text-primary">
          FY {wsData.financial_year}
        </p>
      </div>

      {/* Danger Zone */}
      <div className="border border-risk-high rounded-lg p-4 space-y-3">
        <h3 className="font-ui text-sm font-semibold text-risk-high">Danger Zone</h3>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-ui text-text-primary">Archive workspace</p>
            <p className="text-xs font-ui text-text-muted">
              Mark this FY as complete. Data is preserved.
            </p>
          </div>
          <button
            type="button"
            onClick={() => archiveMutation.mutate()}
            disabled={archiveMutation.isPending || wsData.status === 'archived'}
            className="px-4 py-2 rounded-md border border-risk-high text-risk-high text-sm font-ui disabled:opacity-50"
          >
            {archiveMutation.isPending ? 'Archiving…' : 'Archive'}
          </button>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-ui text-text-primary">Delete workspace</p>
            <p className="text-xs font-ui text-text-muted">
              Permanently removes all data. Requires your password.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowDeleteModal(true)}
            className="px-4 py-2 rounded-md bg-risk-high text-white text-sm font-ui"
          >
            Delete workspace
          </button>
        </div>
      </div>

      {showDeleteModal && (
        <PasswordModal
          title="Delete workspace"
          description="Enter your password to permanently delete this workspace. This cannot be undone."
          confirmLabel="Delete"
          pending={deleteMutation.isPending}
          error={deleteError}
          onConfirm={handleDelete}
          onCancel={() => { setShowDeleteModal(false); setDeleteError(null) }}
        />
      )}
    </div>
  )
}
```

### Step 3: Create NewFYModal

- [ ] Create `frontend/components/settings/NewFYModal.tsx`:

```tsx
'use client'
import { useState } from 'react'
import { createWorkspace } from '@/lib/api/settings'
import type { CreateWorkspaceResult } from '@/lib/api/types'
import { computeNextFY } from '@/lib/utils/fy'

interface Props {
  currentFY: string
  onSuccess: (ws: CreateWorkspaceResult) => void
  onCancel: () => void
}

export default function NewFYModal({ currentFY, onSuccess, onCancel }: Props) {
  const [name, setName] = useState('My Tax Return')
  const [fy, setFy] = useState(() => computeNextFY(currentFY))
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setError('Name is required.')
      return
    }
    setPending(true)
    setError(null)
    try {
      const res = await createWorkspace(name.trim(), fy)
      onSuccess(res.data.data)
    } catch {
      setError('Could not create workspace. Please try again.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center px-4"
    >
      <div className="w-full max-w-sm bg-canvas rounded-lg shadow-lg p-6 space-y-4">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          New financial year
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="new-fy-name" className="text-sm font-ui text-text-body block mb-1">
              Workspace name
            </label>
            <input
              id="new-fy-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="Workspace name"
              required
            />
          </div>

          <div>
            <label htmlFor="new-fy-year" className="text-sm font-ui text-text-body block mb-1">
              Financial year
            </label>
            <input
              id="new-fy-year"
              type="text"
              value={fy}
              onChange={(e) => setFy(e.target.value)}
              pattern="\d{4}-\d{2}"
              placeholder="YYYY-YY"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
              aria-label="Financial year"
              required
            />
          </div>

          {error && <p className="text-sm font-ui text-risk-high">{error}</p>}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={pending}
              className="flex-1 min-h-11 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
            >
              {pending ? 'Creating…' : 'Create'}
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
      </div>
    </div>
  )
}
```

### Step 4: Wire FY switcher in layout + banners placeholder

- [ ] In `frontend/app/(dashboard)/layout.tsx`, wire the FY switcher button to open a `NewFYModal`. Add to the imports at the top:

```tsx
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import NewFYModal from '@/components/settings/NewFYModal'
import useWorkspaceStore from '@/lib/stores/workspace.store'
```

(Some of these may already be imported — only add what's missing.)

- [ ] Inside `DashboardLayout`, add state and handler:

```tsx
const [showNewFY, setShowNewFY] = useState(false)
const { financialYear, setWorkspace } = useWorkspaceStore()
const router = useRouter()

function handleNewFYSuccess(ws: { id: string; financial_year: string }) {
  setWorkspace(ws.id, ws.financial_year)
  setShowNewFY(false)
  router.push('/journey')
}
```

- [ ] Replace the FY switcher button (the stub `<button type="button" ...>FY {financialYear} ▾</button>`):

```tsx
{financialYear && (
  <div className="px-4 py-3 border-b border-border">
    <button
      type="button"
      className="font-ui text-xs text-text-muted hover:text-text-body flex items-center gap-1"
      onClick={() => setShowNewFY(true)}
    >
      FY {financialYear} ▾
    </button>
  </div>
)}
```

- [ ] Add the modal just before the closing `</div>` of the layout:

```tsx
{showNewFY && financialYear && (
  <NewFYModal
    currentFY={financialYear}
    onSuccess={handleNewFYSuccess}
    onCancel={() => setShowNewFY(false)}
  />
)}
```

### Step 5: Run tests

```bash
docker compose exec frontend npx jest --testPathPattern="settings-page" 2>&1 | tail -20
```

Expected: all 6 new tests PASSED

- [ ] Run full frontend suite:

```bash
docker compose exec frontend npx jest 2>&1 | tail -5
```

### Step 6: Commit

```bash
git add frontend/components/settings/WorkspaceTab.tsx \
        frontend/components/settings/NewFYModal.tsx \
        frontend/app/\(dashboard\)/layout.tsx \
        frontend/__tests__/settings-page.test.tsx
git commit -m "feat: wire danger zone (archive/delete) + NewFYModal + FY switcher"
```

---

## Task 5: DeadlineBanner

**Files:**
- Create: `frontend/components/shared/DeadlineBanner.tsx`
- Modify: `frontend/app/(dashboard)/layout.tsx`
- Create: `frontend/__tests__/DeadlineBanner.test.tsx`

### Step 1: Write failing tests

- [ ] Create `frontend/__tests__/DeadlineBanner.test.tsx`:

```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import DeadlineBanner from '@/components/shared/DeadlineBanner'
import * as readinessHook from '@/lib/hooks/useReadiness'
import useWorkspaceStore from '@/lib/stores/workspace.store'

jest.mock('@/lib/hooks/useReadiness')
jest.mock('@/lib/stores/workspace.store')

const mockReadiness = readinessHook.useReadiness as jest.Mock
const mockStore = useWorkspaceStore as unknown as jest.Mock

function setStore(financialYear: string | null, userLodgerType: string | null = null) {
  mockStore.mockReturnValue({ financialYear, userLodgerType })
}

// Freeze time helpers
const RealDate = global.Date
function freezeDate(isoString: string) {
  global.Date = class extends RealDate {
    constructor(...args: ConstructorParameters<typeof Date>) {
      if (args.length === 0) super(isoString)
      else super(...args)
    }
    static now() { return new RealDate(isoString).getTime() }
  } as typeof Date
}
afterEach(() => { global.Date = RealDate })

beforeEach(() => {
  sessionStorage.clear()
  mockReadiness.mockReturnValue({ data: { percentage: 50 } })
})

describe('DeadlineBanner', () => {
  it('renders nothing when no financialYear', () => {
    setStore(null)
    const { container } = render(<DeadlineBanner />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders nothing when more than 30 days remain', () => {
    setStore('2024-25')
    freezeDate('2025-05-01T00:00:00.000Z') // 60 days before June 30
    const { container } = render(<DeadlineBanner />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders amber banner at 15 days', () => {
    setStore('2024-25')
    freezeDate('2025-06-15T00:00:00.000Z') // 15 days before June 30
    render(<DeadlineBanner />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('alert').className).toContain('review')
  })

  it('renders terracotta banner at 5 days', () => {
    setStore('2024-25')
    freezeDate('2025-06-25T00:00:00.000Z') // 5 days before June 30
    render(<DeadlineBanner />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('alert').className).toContain('risk-high')
  })

  it('dismisses when × is clicked', () => {
    setStore('2024-25')
    freezeDate('2025-06-25T00:00:00.000Z')
    render(<DeadlineBanner />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(sessionStorage.getItem('deadline-banner-dismissed')).toBe('1')
  })
})
```

- [ ] Run tests, confirm 5 FAIL:

```bash
docker compose exec frontend npx jest --testPathPattern="DeadlineBanner" 2>&1 | tail -15
```

### Step 2: Create DeadlineBanner component

- [ ] Create `frontend/components/shared/DeadlineBanner.tsx`:

```tsx
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
    userLodgerType === 'self_lodger' &&
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
```

### Step 3: Wire banner in layout

- [ ] In `frontend/app/(dashboard)/layout.tsx`, add import:

```tsx
import DeadlineBanner from '@/components/shared/DeadlineBanner'
```

- [ ] Add the banner just before `{children}` inside `<main>`:

```tsx
<main className="flex-1 flex flex-col min-w-0 pb-16 md:pb-0">
  <DeadlineBanner />
  <div className="flex-1 max-w-4xl w-full mx-auto px-4 py-6">
    {children}
  </div>
</main>
```

### Step 4: Run tests

```bash
docker compose exec frontend npx jest --testPathPattern="DeadlineBanner" 2>&1 | tail -15
```

Expected: 5 PASSED

### Step 5: Commit

```bash
git add frontend/components/shared/DeadlineBanner.tsx \
        frontend/app/\(dashboard\)/layout.tsx \
        frontend/__tests__/DeadlineBanner.test.tsx
git commit -m "feat: add DeadlineBanner — amber at 30 days, terracotta at 7 days before FY end"
```

---

## Task 6: NetworkBanner + Loading Skeletons

**Files:**
- Create: `frontend/components/shared/NetworkBanner.tsx`
- Modify: `frontend/app/(dashboard)/layout.tsx`
- Modify: `frontend/app/(dashboard)/readiness/page.tsx`
- Modify: `frontend/app/(dashboard)/review/page.tsx`
- Modify: `frontend/app/(dashboard)/evidence/page.tsx`
- Create: `frontend/__tests__/NetworkBanner.test.tsx`

### Step 1: Write failing NetworkBanner tests

- [ ] Create `frontend/__tests__/NetworkBanner.test.tsx`:

```typescript
import { render, screen, act } from '@testing-library/react'
import NetworkBanner from '@/components/shared/NetworkBanner'
import client from '@/lib/api/client'
import axios from 'axios'

jest.mock('@/lib/api/client', () => ({
  get: jest.fn(),
}))

const mockGet = client.get as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('NetworkBanner', () => {
  it('renders nothing when API is reachable', async () => {
    mockGet.mockResolvedValue({ status: 200 })
    const { container } = render(<NetworkBanner />)
    await act(async () => { /* let first poll run */ })
    expect(container).toBeEmptyDOMElement()
  })

  it('shows offline banner when API is unreachable', async () => {
    mockGet.mockRejectedValue(new axios.AxiosError('Network Error'))
    render(<NetworkBanner />)
    await act(async () => {})
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/offline/i)).toBeInTheDocument()
  })

  it('hides banner when API comes back online', async () => {
    mockGet
      .mockRejectedValueOnce(new axios.AxiosError('Network Error'))
      .mockResolvedValue({ status: 200 })
    render(<NetworkBanner />)
    await act(async () => {})
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    await act(async () => {})
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows reconnecting message when offline', async () => {
    mockGet.mockRejectedValue(new axios.AxiosError('Network Error'))
    render(<NetworkBanner />)
    await act(async () => {})
    expect(await screen.findByText(/checking connection/i)).toBeInTheDocument()
  })
})
```

- [ ] Run tests, confirm 4 FAIL:

```bash
docker compose exec frontend npx jest --testPathPattern="NetworkBanner" 2>&1 | tail -10
```

### Step 2: Create NetworkBanner

- [ ] Create `frontend/components/shared/NetworkBanner.tsx`:

```tsx
'use client'
import { useEffect, useState, useRef } from 'react'
import client from '@/lib/api/client'

export default function NetworkBanner() {
  const [offline, setOffline] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function checkHealth() {
    try {
      await client.get('/api/v1/health')
      setOffline(false)
    } catch {
      setOffline(true)
    }
  }

  useEffect(() => {
    checkHealth()
    intervalRef.current = setInterval(checkHealth, 5000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [])

  if (!offline) return null

  return (
    <div role="alert" className="bg-risk-high text-white px-4 py-2 flex items-center justify-between">
      <p className="text-sm font-ui">
        Offline — checking connection…
      </p>
    </div>
  )
}
```

### Step 3: Wire NetworkBanner in layout

- [ ] In `frontend/app/(dashboard)/layout.tsx`, add import:

```tsx
import NetworkBanner from '@/components/shared/NetworkBanner'
```

- [ ] Add it above `<DeadlineBanner />` inside `<main>`:

```tsx
<main className="flex-1 flex flex-col min-w-0 pb-16 md:pb-0">
  <NetworkBanner />
  <DeadlineBanner />
  <div className="flex-1 max-w-4xl w-full mx-auto px-4 py-6">
    {children}
  </div>
</main>
```

### Step 4: Replace spinner loading states with skeletons

The current loading states show a centered paragraph. Replace with a skeleton that fills the page structure without making the UI jump.

- [ ] In `frontend/app/(dashboard)/readiness/page.tsx`, replace the `isLoading` return:

```tsx
if (isLoading) {
  return (
    <div className="space-y-8 animate-pulse">
      <div className="h-8 w-48 bg-surface rounded" />
      <div className="bg-surface rounded-lg shadow-sm p-6 flex flex-col items-center gap-6">
        <div className="w-40 h-40 rounded-full bg-border" />
        <div className="w-full space-y-2">
          <div className="h-4 bg-border rounded w-3/4" />
          <div className="h-4 bg-border rounded w-1/2" />
        </div>
      </div>
      <div className="bg-surface rounded-lg shadow-sm p-6 space-y-3">
        <div className="h-4 bg-border rounded w-1/3" />
        <div className="h-3 bg-border rounded" />
        <div className="h-3 bg-border rounded w-5/6" />
      </div>
    </div>
  )
}
```

- [ ] In `frontend/app/(dashboard)/review/page.tsx`, replace the `isLoading` return:

```tsx
if (isLoading) {
  return (
    <div className="space-y-8 animate-pulse">
      <div className="h-8 w-32 bg-surface rounded" />
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-surface rounded-lg p-4 h-20" />
      ))}
    </div>
  )
}
```

- [ ] In `frontend/app/(dashboard)/evidence/page.tsx`, replace the `isLoading` return:

```tsx
if (isLoading) {
  return (
    <div className="space-y-8 animate-pulse">
      <div className="h-8 w-48 bg-surface rounded" />
      <div className="bg-surface border border-border rounded-lg h-32" />
      {[1, 2].map((i) => (
        <div key={i} className="bg-surface rounded-lg p-4 h-16" />
      ))}
    </div>
  )
}
```

### Step 5: Run tests

```bash
docker compose exec frontend npx jest --testPathPattern="NetworkBanner" 2>&1 | tail -10
```

Expected: 4 PASSED

- [ ] Run full frontend suite:

```bash
docker compose exec frontend npx jest 2>&1 | tail -5
```

### Step 6: Commit

```bash
git add frontend/components/shared/NetworkBanner.tsx \
        frontend/app/\(dashboard\)/layout.tsx \
        frontend/app/\(dashboard\)/readiness/page.tsx \
        frontend/app/\(dashboard\)/review/page.tsx \
        frontend/app/\(dashboard\)/evidence/page.tsx \
        frontend/__tests__/NetworkBanner.test.tsx
git commit -m "feat: add NetworkBanner (health polling) + loading skeletons on readiness, review, evidence"
```

---

## Task 7: Tax Estimate Section

**Files:**
- Create: `frontend/components/readiness/TaxEstimate.tsx`
- Modify: `frontend/app/(dashboard)/readiness/page.tsx`
- Create: `frontend/__tests__/TaxEstimate.test.tsx`

### Background

The backend `GET /api/v1/estimator/summary` already exists and returns:
```json
{
  "gross_income": "85000.00",
  "total_deductions": "3200.00",
  "taxable_income": "81800.00",
  "payg_withheld": "20000.00",
  "confirmed_only": false,
  "pending_count": 5,
  "ato_calculator_url": "https://...",
  "disclaimer": "..."
}
```

This task renders it below the readiness ring, above the `<Disclaimer />`.

### Step 1: Write failing tests

- [ ] Create `frontend/__tests__/TaxEstimate.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react'
import TaxEstimate from '@/components/readiness/TaxEstimate'
import type { TaxEstimateSummary } from '@/lib/api/types'

const mockData: TaxEstimateSummary = {
  gross_income: '85000.00',
  total_deductions: '3200.00',
  taxable_income: '81800.00',
  payg_withheld: '20000.00',
  confirmed_only: false,
  pending_count: 5,
  ato_calculator_url: 'https://www.ato.gov.au/calculators',
  disclaimer: 'Indicative estimate only.',
}

describe('TaxEstimate', () => {
  it('renders gross income', () => {
    render(<TaxEstimate data={mockData} isLoading={false} />)
    expect(screen.getByText(/gross income/i)).toBeInTheDocument()
    expect(screen.getByText('$85,000')).toBeInTheDocument()
  })

  it('renders taxable income and deductions', () => {
    render(<TaxEstimate data={mockData} isLoading={false} />)
    expect(screen.getByText(/total deductions/i)).toBeInTheDocument()
    expect(screen.getByText('$3,200')).toBeInTheDocument()
    expect(screen.getByText(/taxable income/i)).toBeInTheDocument()
    expect(screen.getByText('$81,800')).toBeInTheDocument()
  })

  it('renders pending items notice when pending_count > 0', () => {
    render(<TaxEstimate data={mockData} isLoading={false} />)
    expect(screen.getByText(/5 items? still/i)).toBeInTheDocument()
  })

  it('renders ATO calculator link', () => {
    render(<TaxEstimate data={mockData} isLoading={false} />)
    const link = screen.getByRole('link', { name: /ato/i })
    expect(link).toHaveAttribute('href', 'https://www.ato.gov.au/calculators')
    expect(link).toHaveAttribute('target', '_blank')
  })
})
```

- [ ] Run tests, confirm 4 FAIL:

```bash
docker compose exec frontend npx jest --testPathPattern="TaxEstimate" 2>&1 | tail -10
```

### Step 2: Create TaxEstimate component

- [ ] Create `frontend/components/readiness/TaxEstimate.tsx`:

```tsx
import type { TaxEstimateSummary } from '@/lib/api/types'

function fmt(value: string): string {
  const n = parseFloat(value)
  if (isNaN(n)) return value
  return `$${Math.round(n).toLocaleString('en-AU')}`
}

interface Props {
  data: TaxEstimateSummary | undefined
  isLoading: boolean
}

export default function TaxEstimate({ data, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="bg-surface rounded-lg shadow-sm p-6 space-y-3 animate-pulse">
        <div className="h-4 bg-border rounded w-1/3" />
        <div className="h-3 bg-border rounded" />
        <div className="h-3 bg-border rounded w-3/4" />
      </div>
    )
  }

  if (!data) return null

  const rows = [
    { label: 'Gross income', value: fmt(data.gross_income) },
    { label: 'Total deductions', value: `− ${fmt(data.total_deductions)}` },
    { label: 'Taxable income', value: fmt(data.taxable_income) },
    { label: 'PAYG withheld', value: fmt(data.payg_withheld) },
  ]

  return (
    <div className="bg-surface rounded-lg shadow-sm p-6 space-y-4">
      <h2 className="font-display text-base font-semibold text-text-primary">
        Tax estimate
      </h2>

      <div className="space-y-2">
        {rows.map(({ label, value }) => (
          <div key={label} className="flex justify-between items-baseline">
            <span className="text-sm font-ui text-text-body">{label}</span>
            <span className="text-sm font-mono text-text-primary">{value}</span>
          </div>
        ))}
      </div>

      {!data.confirmed_only && data.pending_count > 0 && (
        <p className="text-xs font-ui text-text-muted">
          {data.pending_count} item{data.pending_count !== 1 ? 's' : ''} still pending review — estimate will change.
        </p>
      )}

      <p className="text-xs font-ui text-text-muted">{data.disclaimer}</p>

      <a
        href={data.ato_calculator_url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs font-ui text-accent underline"
      >
        ATO income tax calculator →
      </a>
    </div>
  )
}
```

### Step 3: Add TaxEstimate to readiness page

- [ ] In `frontend/app/(dashboard)/readiness/page.tsx`, add these imports:

```tsx
import { useQuery } from '@tanstack/react-query'
import { getEstimatorSummary } from '@/lib/api/estimator'
import TaxEstimate from '@/components/readiness/TaxEstimate'
import type { TaxEstimateSummary } from '@/lib/api/types'
```

- [ ] Inside `ReadinessPage`, add the estimator query after `useReadiness`:

```tsx
const { data: estimate, isLoading: estimateLoading } = useQuery<TaxEstimateSummary>({
  queryKey: ['tax-estimate'],
  queryFn: () => getEstimatorSummary().then((r) => r.data.data),
})
```

- [ ] Add `<TaxEstimate />` between the per-skill breakdown section and `<Disclaimer />`:

```tsx
      {/* Tax estimate */}
      <TaxEstimate data={estimate} isLoading={estimateLoading} />

      <Disclaimer />
```

### Step 4: Run tests

```bash
docker compose exec frontend npx jest --testPathPattern="TaxEstimate" 2>&1 | tail -10
```

Expected: 4 PASSED

- [ ] Run full frontend suite:

```bash
docker compose exec frontend npx jest 2>&1 | tail -5
```

### Step 5: Commit

```bash
git add frontend/components/readiness/TaxEstimate.tsx \
        frontend/app/\(dashboard\)/readiness/page.tsx \
        frontend/__tests__/TaxEstimate.test.tsx \
        frontend/lib/api/estimator.ts
git commit -m "feat: add Tax Estimate section to Readiness page — income, deductions, PAYG, ATO link"
```

---

## Task 8: Onboarding Fix + PWA Manifest

**Files:**
- Modify: `frontend/app/(auth)/setup/page.tsx`
- Create: `frontend/public/manifest.json`
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/__tests__/setup.test.tsx` (or create if it doesn't exist)

### Background

**Onboarding fix:** The `POST /auth/setup` creates a workspace with `financial_year` from the request body (defaulting to `"2024-25"`). The setup page doesn't ask the user which FY they're preparing for. Add a FY selection step (new Step 1) before the password step. After `setupConfirm` succeeds, call `setWorkspace` with the workspace data returned by `POST /auth/setup` so the dashboard store is populated immediately.

**PWA manifest:** A minimal `manifest.json` enables "Add to Home Screen" on mobile. No service worker needed.

### Step 1: Extend setup tests

- [ ] Find or create `frontend/__tests__/setup.test.tsx`. If it exists, add; if not, create. Append these 2 tests:

```typescript
// If creating new file:
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import SetupPage from '@/app/(auth)/setup/page'
import * as authApi from '@/lib/api/auth'
import useWorkspaceStore from '@/lib/stores/workspace.store'

jest.mock('@/lib/api/auth')
jest.mock('next/navigation', () => ({ useRouter: () => ({ push: jest.fn(), replace: jest.fn() }) }))
jest.mock('@/lib/stores/workspace.store', () => {
  const setWorkspace = jest.fn()
  return jest.fn(() => ({ setWorkspace }))
})

describe('SetupPage FY selection', () => {
  it('renders FY selection as first step', () => {
    render(<SetupPage />)
    expect(screen.getByText(/which financial year/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /2024-25/i })).toBeInTheDocument()
  })

  it('calls setWorkspace with workspace data after confirm', async () => {
    (authApi.setup as jest.Mock).mockResolvedValue({
      data: { data: { recovery_key: 'AAAA-BBBB-CCCC-DDDD', workspace_id: 'ws-1', financial_year: '2024-25' } },
    })
    ;(authApi.setupConfirm as jest.Mock).mockResolvedValue({})
    const mockSetWorkspace = (useWorkspaceStore as unknown as jest.Mock)().setWorkspace

    render(<SetupPage />)
    fireEvent.click(screen.getByRole('button', { name: /2024-25/i }))
    // Fill password
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'Abcd1234!' } })
    fireEvent.change(screen.getByLabelText(/confirm/i), { target: { value: 'Abcd1234!' } })
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(authApi.setup).toHaveBeenCalledWith('Abcd1234!', '2024-25'))

    // Step 2: click "I've saved it"
    fireEvent.click(screen.getByRole('button', { name: /saved it/i }))
    // Step 3: enter confirmation
    fireEvent.change(screen.getByLabelText(/last key segment/i), { target: { value: 'CCCC-DDDD' } })
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }))
    await waitFor(() =>
      expect(mockSetWorkspace).toHaveBeenCalledWith('ws-1', '2024-25')
    )
  })
})
```

- [ ] Run tests, confirm 2 FAIL:

```bash
docker compose exec frontend npx jest --testPathPattern="setup" 2>&1 | tail -10
```

### Step 2: Update setup page

- [ ] In `frontend/app/(auth)/setup/page.tsx`:

1. Change `type Step = 1 | 2 | 3` to `type Step = 0 | 1 | 2 | 3` (step 0 = FY selection).

2. Add `selectedFY` state and `workspaceId` state to store workspace data returned by setup:

```tsx
const [selectedFY, setSelectedFY] = useState('2024-25')
const [setupWorkspaceId, setSetupWorkspaceId] = useState('')
```

3. Add `setWorkspace` from workspace store:

```tsx
import useWorkspaceStore from '@/lib/stores/workspace.store'
// inside component:
const { setWorkspace } = useWorkspaceStore()
```

4. Change initial step to 0:

```tsx
const [step, setStep] = useState<Step>(0)
```

5. Update `onPasswordSubmit` to pass `selectedFY` to `setup()` and store the returned workspace data:

The current `setup` call is `await setup(password)`. Change to:
```tsx
const res = await setup(password, selectedFY)
setSetupWorkspaceId(res.data.data.workspace_id ?? '')
setRecoveryKey(res.data.data.recovery_key)
setStep(2)
```

6. Update `onConfirmSubmit` to call `setWorkspace` after confirm:

```tsx
async function onConfirmSubmit({ confirmation }: ConfirmForm) {
  setServerError(null)
  try {
    await setupConfirm(confirmation)
    setWorkspace(setupWorkspaceId, selectedFY)
    router.push('/journey')
  } catch (err: unknown) {
    const msg = (
      err as { response?: { data?: { detail?: { message?: string } } } }
    )?.response?.data?.detail?.message
    setServerError(msg ?? 'Confirmation failed. Check the last key segment.')
  }
}
```

7. Add step 0 render block before the `{step === 1 && ...}` block:

```tsx
{/* ── Step 0: Financial year selection ── */}
{step === 0 && (
  <div className="space-y-4">
    <h2 className="font-ui text-xl font-semibold text-text-primary">
      Which financial year are you preparing?
    </h2>
    <div className="space-y-2">
      {(['2024-25', '2023-24', '2025-26'] as const).map((fy) => (
        <button
          key={fy}
          type="button"
          onClick={() => { setSelectedFY(fy); setStep(1) }}
          className={`w-full text-left px-4 py-3 rounded-md border font-ui text-sm font-medium transition-colors ${
            selectedFY === fy
              ? 'border-accent text-accent bg-accent-soft'
              : 'border-border text-text-body hover:border-accent'
          }`}
        >
          FY {fy}
        </button>
      ))}
    </div>
  </div>
)}
```

8. Update `setup` call in `lib/api/auth.ts` to accept `financialYear`:

```typescript
export const setup = (password: string, financialYear: string = '2024-25') =>
  client.post<ApiResponse<SetupData>>('/api/v1/auth/setup', { password, financial_year: financialYear })
```

Also update `SetupData` in `types.ts` to include `workspace_id`:

```typescript
export interface SetupData {
  recovery_key: string
  workspace_id: string
}
```

### Step 3: Create PWA manifest

- [ ] Create `frontend/public/manifest.json`:

```json
{
  "name": "Tax Return AI",
  "short_name": "Tax AI",
  "description": "AI-guided Australian tax preparation workspace",
  "start_url": "/journey",
  "display": "standalone",
  "background_color": "#f9f7f4",
  "theme_color": "#1a1a2e",
  "icons": [
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

(Icons don't need to exist for the manifest to be valid — the app still works without them.)

### Step 4: Add manifest link to root layout

- [ ] In `frontend/app/layout.tsx`, update the `<head>` to include the manifest. In Next.js 14, add `icons` and `manifest` to the `metadata` export:

```typescript
export const metadata: Metadata = {
  title: 'Tax Return AI',
  description: 'AI-guided tax preparation workspace for Australian taxpayers',
  manifest: '/manifest.json',
}
```

### Step 5: Run tests

```bash
docker compose exec frontend npx jest --testPathPattern="setup" 2>&1 | tail -10
```

Expected: 2 PASSED

- [ ] Run full frontend suite:

```bash
docker compose exec frontend npx jest 2>&1 | tail -5
```

### Step 6: Commit

```bash
git add frontend/app/\(auth\)/setup/page.tsx \
        frontend/lib/api/auth.ts \
        frontend/lib/api/types.ts \
        frontend/public/manifest.json \
        frontend/app/layout.tsx \
        frontend/__tests__/setup.test.tsx
git commit -m "feat: add FY selection to setup flow + setWorkspace after confirm + PWA manifest"
```

---

## Task 9: Full Test Suite Verification

**Files:** None modified — verification only.

### Step 1: Run all backend tests

```bash
docker compose exec backend pytest tests/ -v 2>&1 | tail -20
```

Expected: ~158 tests, all PASSED. If any fail, fix before proceeding.

### Step 2: Run all frontend tests

```bash
docker compose exec frontend npx jest 2>&1 | tail -20
```

Expected: ~237 tests, all PASSED. If any fail, fix before proceeding.

### Step 3: Record final counts

Note the exact counts from the test output.

### Step 4: Final commit if any fixes were needed

```bash
git add -p  # stage only the fix files
git commit -m "fix: test suite cleanup after Phase 8"
```

---

## Self-Review

### Spec coverage

| Spec item | Task |
|-----------|------|
| DELETE /workspaces/{id} with password, soft-delete, redirect target | Task 1 |
| Archive button sets status="archived" | Task 1 |
| Frontend: password modal → delete → redirect | Task 4 |
| POST /workspaces — new FY, copy TaxProfile, YoY suggestions | Task 2 |
| "+ New financial year" in FY switcher | Task 4 |
| Redirect to /journey after new FY | Task 4 |
| DeadlineBanner — amber 30 days, terracotta 7 days | Task 5 |
| DeadlineBanner — self-lodger Oct message | Task 5 |
| DeadlineBanner — dismiss to sessionStorage | Task 5 |
| Onboarding: FY selection step | Task 8 |
| Onboarding: setWorkspace after confirm | Task 8 |
| Onboarding: redirect to /journey (not /readiness) | Already correct in existing code; setWorkspace call added |
| NetworkBanner — poll GET /health every 5s | Task 6 |
| NetworkBanner — auto-dismiss on reconnect | Task 6 |
| Loading skeletons — readiness, review, evidence | Task 6 |
| Tax Estimate section on Readiness page | Task 7 |
| PWA manifest | Task 8 |
| Session/login response format fix (financial_year, is_unlocked) | Task 1 |

### Type consistency

- `CreateWorkspaceResult extends WorkspaceInfo` — both defined in `types.ts`
- `computeNextFY` used in `NewFYModal` — exported from `fy.ts`
- `deadlineState` and `daysUntilFYEnd` used in `DeadlineBanner` — exported from `fy.ts`
- `TaxEstimateSummary` used in `TaxEstimate` and `readiness/page.tsx` — defined in `types.ts`
- `userLodgerType` in workspace store — set by `useAuth`, read by `DeadlineBanner`
- `sign_session` imported from `app.api.dependencies` in `workspaces.py` — already exported there
- `profiles_repo.update_fields` commits internally — no double-commit needed in route handler
- `yoy_repo.create_suggestions` commits internally — no double-commit needed

### Placeholder scan

No TODOs, no "TBD", no "similar to Task N" references. All code blocks are complete.
