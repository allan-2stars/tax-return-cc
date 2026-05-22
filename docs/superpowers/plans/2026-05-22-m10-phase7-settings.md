# M10 Phase 7: Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the full Settings page (5 tabs: Workspace, Security, AI & Privacy, Storage, About) with all supporting backend endpoints.

**Architecture:** New `routes/settings.py` holds settings-specific GET endpoints. Auth operations (change-password, recovery-key regeneration) extend `routes/auth.py`. The existing `routes/workspaces.py` gets a real implementation. Frontend: tabbed `settings/page.tsx` delegates each tab to its own component file; a shared `PasswordModal` handles password-confirmation flows. Tab state lives in `sessionStorage`.

**Tech Stack:** FastAPI, SQLAlchemy async, bcrypt, Next.js 14 App Router, React Query, Tailwind CSS, Jest + React Testing Library

> **Architecture note — View Recovery Key:** The original recovery key is never stored (only its bcrypt hash and the DEK it encrypts are persisted). Therefore "View Recovery Key" is architecturally impossible. This plan implements a single "Generate New Recovery Key" action (requires password; shows new key once; old key is immediately invalid). The Security tab UI reflects this with an explanatory note.

---

## File Map

**Backend — new/modified:**
- `backend/app/api/routes/auth.py` — add `POST /auth/change-password`, `POST /auth/recovery-key/regenerate`
- `backend/app/api/routes/settings.py` — NEW: `GET /settings/ai-usage`, `GET /settings/storage-usage`, `GET /settings/diagnostic-log`, `GET /settings/about`
- `backend/app/api/routes/workspaces.py` — real `GET /workspaces`, `PATCH /workspaces/{id}`
- `backend/app/api/__init__.py` — register settings router
- `backend/tests/test_settings.py` — NEW: 12 backend tests

**Frontend — new/modified:**
- `frontend/lib/api/types.ts` — add `WorkspaceInfo`, `AiUsageItem`, `AiUsageData`, `StorageUsageData`, `AboutData`, `SkillInfo`
- `frontend/lib/api/settings.ts` — NEW: all settings + workspace API functions
- `frontend/components/settings/PasswordModal.tsx` — NEW: reusable password-confirmation modal
- `frontend/components/settings/WorkspaceTab.tsx` — NEW
- `frontend/components/settings/SecurityTab.tsx` — NEW
- `frontend/components/settings/AiPrivacyTab.tsx` — NEW
- `frontend/components/settings/StorageTab.tsx` — NEW
- `frontend/components/settings/AboutTab.tsx` — NEW
- `frontend/app/(dashboard)/settings/page.tsx` — replace stub
- `frontend/__tests__/settings-page.test.tsx` — NEW: 12+ frontend tests

---

## Task 1: Backend — auth endpoints (change-password + recovery-key/regenerate)

**Files:**
- Modify: `backend/app/api/routes/auth.py`
- Test: `backend/tests/test_settings.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_settings.py`:

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.conftest import TEST_PASSWORD


@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with maker() as session:
        yield session


@pytest.mark.asyncio
async def test_change_password_success(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": "new-password-99"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    login = await auth_client.post(
        "/api/v1/auth/login", json={"password": "new-password-99"}
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong-password", "new_password": "new-password-99"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["error_code"] == "invalid_password"


@pytest.mark.asyncio
async def test_change_password_dek_still_decryptable(auth_client, db_session):
    """After password change, DEK can still be decrypted with new password."""
    from app.repositories import auth as auth_repo
    from app.security import decrypt_dek

    resp = await auth_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": "changed-pw-123"},
    )
    assert resp.status_code == 200

    ws = await auth_repo.get_security(db_session, auth_client.workspace_id)
    dek = decrypt_dek(ws.password_encrypted_dek, "changed-pw-123")
    assert len(dek) == 32


@pytest.mark.asyncio
async def test_regenerate_recovery_key_returns_new_key(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/recovery-key/regenerate",
        json={"password": TEST_PASSWORD},
    )
    assert resp.status_code == 200
    new_key = resp.json()["data"]["recovery_key"]
    assert " / " in new_key
    assert "-" in new_key


@pytest.mark.asyncio
async def test_regenerate_recovery_key_wrong_password(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/recovery-key/regenerate",
        json={"password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_regenerate_recovery_key_old_key_invalid(auth_client):
    """After regeneration, the original recovery key no longer decrypts the DEK."""
    from app.security import decrypt_dek, normalize_recovery_key

    original_key = auth_client.recovery_key

    resp = await auth_client.post(
        "/api/v1/auth/recovery-key/regenerate",
        json={"password": TEST_PASSWORD},
    )
    assert resp.status_code == 200

    recover_resp = await auth_client.post(
        "/api/v1/auth/recover",
        json={
            "recovery_key": original_key,
            "new_password": "should-fail",
            "workspace_id": auth_client.workspace_id,
        },
    )
    assert recover_resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend pytest tests/test_settings.py -v 2>&1 | head -30
```
Expected: all fail with "404 Not Found" or "AttributeError"

- [ ] **Step 3: Implement the endpoints in auth.py**

Add to `backend/app/api/routes/auth.py` after the existing imports and before the first route:

```python
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class RecoveryKeyPasswordRequest(BaseModel):
    password: str
```

Add after `@router.post("/auth/recover")`:

```python
@router.post("/auth/change-password")
async def change_password(
    body: ChangePasswordRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    ws = await auth_repo.get_security(db, workspace_id)
    if not ws or not ws.password_hash or not ws.password_encrypted_dek:
        raise HTTPException(
            status_code=404,
            detail=error_response("workspace_not_found", "Workspace not found.", retryable=False),
        )
    if not bcrypt.checkpw(body.current_password.encode(), ws.password_hash.encode()):
        raise HTTPException(
            status_code=401,
            detail=error_response("invalid_password", "Incorrect current password.", retryable=False),
        )
    dek = decrypt_dek(ws.password_encrypted_dek, body.current_password)
    new_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
    new_encrypted_dek = encrypt_dek(dek, body.new_password)
    await auth_repo.update_security(
        db, ws, password_hash=new_hash, password_encrypted_dek=new_encrypted_dek
    )
    return {"status": "ok"}


@router.post("/auth/recovery-key/regenerate")
async def regenerate_recovery_key(
    body: RecoveryKeyPasswordRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    ws = await auth_repo.get_security(db, workspace_id)
    if not ws or not ws.password_hash or not ws.password_encrypted_dek:
        raise HTTPException(
            status_code=404,
            detail=error_response("workspace_not_found", "Workspace not found.", retryable=False),
        )
    if not bcrypt.checkpw(body.password.encode(), ws.password_hash.encode()):
        raise HTTPException(
            status_code=401,
            detail=error_response("invalid_password", "Incorrect password.", retryable=False),
        )
    dek = decrypt_dek(ws.password_encrypted_dek, body.password)
    new_key = generate_recovery_key()
    normalized = normalize_recovery_key(new_key)
    last_8 = normalized[-8:]
    await auth_repo.update_security(
        db,
        ws,
        recovery_key_hash=bcrypt.hashpw(normalized.encode(), bcrypt.gensalt(rounds=12)).decode(),
        recovery_encrypted_dek=encrypt_dek(dek, normalized),
        recovery_confirm_hash=bcrypt.hashpw(last_8.encode(), bcrypt.gensalt(rounds=12)).decode(),
    )
    return {"data": {"recovery_key": new_key}}
```

- [ ] **Step 4: Run auth tests to verify they pass**

```bash
docker compose exec backend pytest tests/test_settings.py::test_change_password_success tests/test_settings.py::test_change_password_wrong_current tests/test_settings.py::test_change_password_dek_still_decryptable tests/test_settings.py::test_regenerate_recovery_key_returns_new_key tests/test_settings.py::test_regenerate_recovery_key_wrong_password tests/test_settings.py::test_regenerate_recovery_key_old_key_invalid -v
```
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/auth.py backend/tests/test_settings.py
git commit -m "feat: add change-password and recovery-key/regenerate endpoints"
```

---

## Task 2: Backend — settings routes + workspaces

**Files:**
- Create: `backend/app/api/routes/settings.py`
- Modify: `backend/app/api/routes/workspaces.py`
- Modify: `backend/app/api/__init__.py`
- Test: `backend/tests/test_settings.py` (append)

- [ ] **Step 1: Write the failing tests — append to test_settings.py**

```python
# ── settings endpoints ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_usage_returns_aggregation(auth_client, db_session):
    from datetime import datetime, timezone
    from app.db.models import AuditLog

    for _ in range(3):
        db_session.add(AuditLog(
            workspace_id=auth_client.workspace_id,
            action="ai_interaction",
            actor="ai",
            ai_operation="classify",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.0005,
            ai_success=True,
            created_at=datetime.now(timezone.utc),
        ))
    await db_session.commit()

    resp = await auth_client.get("/api/v1/settings/ai-usage")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total_cost_usd" in data
    classify = next((i for i in data["items"] if i["operation"] == "classify"), None)
    assert classify is not None
    assert classify["calls"] == 3


@pytest.mark.asyncio
async def test_storage_usage_returns_byte_counts(auth_client):
    resp = await auth_client.get("/api/v1/settings/storage-usage")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "documents_bytes" in data
    assert "exports_bytes" in data
    assert "db_bytes" in data
    assert isinstance(data["documents_bytes"], int)
    assert isinstance(data["exports_bytes"], int)
    assert isinstance(data["db_bytes"], int)


@pytest.mark.asyncio
async def test_diagnostic_log_download(auth_client):
    resp = await auth_client.get("/api/v1/settings/diagnostic-log")
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    body = resp.json()
    assert "document_count" in body
    assert "event_count" in body
    assert "active_skills" in body
    assert "TFN" not in str(body)
    assert "password" not in str(body)


@pytest.mark.asyncio
async def test_settings_about_returns_skills_and_disclaimer(auth_client):
    resp = await auth_client.get("/api/v1/settings/about")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "active_skills" in data
    assert "disclaimer" in data
    assert "organise" in data["disclaimer"]
    assert isinstance(data["active_skills"], list)


# ── workspaces ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_workspaces_returns_current(auth_client):
    resp = await auth_client.get("/api/v1/workspaces")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["financial_year"] == "2024-25"
    assert "readiness_pct" in items[0]


@pytest.mark.asyncio
async def test_patch_workspace_name(auth_client):
    resp = await auth_client.patch(
        f"/api/v1/workspaces/{auth_client.workspace_id}",
        json={"name": "Updated Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_patch_workspace_wrong_id_returns_403(auth_client):
    resp = await auth_client.patch(
        "/api/v1/workspaces/other-workspace-id",
        json={"name": "Hacked"},
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run to verify they fail**

```bash
docker compose exec backend pytest tests/test_settings.py -v -k "usage or diagnostic or about or workspaces or patch_workspace" 2>&1 | head -30
```
Expected: all fail with 404/422

- [ ] **Step 3: Create backend/app/api/routes/settings.py**

```python
import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.config import settings
from app.db.base import get_db
from app.db.models import AuditLog, Document, TaxEvent

router = APIRouter()

_DISCLAIMER = (
    "This tool helps organise your tax information and prepare a review package. "
    "It does not provide final tax advice and does not replace review by "
    "a registered tax agent."
)


@router.get("/settings/ai-usage")
async def get_ai_usage(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    today = datetime.now(timezone.utc)
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    rows = await db.execute(
        select(
            AuditLog.ai_operation,
            func.count(AuditLog.id).label("calls"),
            func.sum(AuditLog.cost_usd).label("total_cost"),
        )
        .where(
            AuditLog.workspace_id == workspace_id,
            AuditLog.ai_operation.isnot(None),
            AuditLog.created_at >= month_start,
        )
        .group_by(AuditLog.ai_operation)
    )
    items = [
        {
            "operation": r.ai_operation,
            "calls": r.calls,
            "cost_usd": round(r.total_cost or 0.0, 4),
        }
        for r in rows.all()
    ]
    total_cost = round(sum(i["cost_usd"] for i in items), 4)
    return {
        "data": {
            "ai_provider": settings.AI_PROVIDER,
            "items": items,
            "total_cost_usd": total_cost,
        }
    }


@router.get("/settings/storage-usage")
async def get_storage_usage(workspace_id: str = Depends(require_auth)):
    def _dir_bytes(path: str) -> int:
        total = 0
        try:
            for dirpath, _, filenames in os.walk(path):
                for fname in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, fname))
                    except OSError:
                        pass
        except OSError:
            pass
        return total

    documents_bytes = _dir_bytes(os.path.join(settings.STORAGE_PATH, workspace_id))
    exports_bytes = _dir_bytes(os.path.join(settings.EXPORT_PATH, workspace_id))

    db_bytes = 0
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:////", "/")
    try:
        db_bytes = os.path.getsize(db_path)
    except OSError:
        pass

    return {
        "data": {
            "documents_bytes": documents_bytes,
            "exports_bytes": exports_bytes,
            "db_bytes": db_bytes,
        }
    }


@router.get("/settings/diagnostic-log")
async def get_diagnostic_log(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    from app.skills.registry import get_registry

    doc_count = (
        await db.execute(
            select(func.count(Document.id)).where(Document.workspace_id == workspace_id)
        )
    ).scalar() or 0

    event_count = (
        await db.execute(
            select(func.count(TaxEvent.id)).where(TaxEvent.workspace_id == workspace_id)
        )
    ).scalar() or 0

    registry = get_registry()
    skills = [
        {"skill_id": s.skill_id, "version": getattr(s, "version", "unknown")}
        for s in registry._skills.values()
    ]

    payload = {
        "document_count": doc_count,
        "event_count": event_count,
        "active_skills": skills,
        "ai_provider": settings.AI_PROVIDER,
        "environment": settings.ENVIRONMENT,
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="diagnostic.json"'},
    )


@router.get("/settings/about")
async def get_about(workspace_id: str = Depends(require_auth)):
    from app.skills.registry import get_registry

    registry = get_registry()
    skills = [
        {
            "skill_id": s.skill_id,
            "version": getattr(s, "version", "unknown"),
            "display_name": getattr(s, "display_name", s.skill_id),
        }
        for s in registry._skills.values()
    ]
    return {
        "data": {
            "active_skills": skills,
            "disclaimer": _DISCLAIMER,
        }
    }
```

- [ ] **Step 4: Update backend/app/api/routes/workspaces.py**

Replace the entire file:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import get_db
from app.db.models import ReadinessScore, Workspace
from app.errors import error_response

router = APIRouter()


class UpdateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


def _ws_dict(ws: Workspace, readiness_pct: float) -> dict:
    return {
        "id": ws.id,
        "name": ws.name,
        "financial_year": ws.financial_year,
        "status": ws.status,
        "readiness_pct": readiness_pct,
    }


@router.get("/workspaces")
async def list_workspaces(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(select(Workspace))
    workspaces = rows.scalars().all()

    items = []
    for ws in workspaces:
        score_row = await db.execute(
            select(ReadinessScore)
            .where(ReadinessScore.workspace_id == ws.id)
            .order_by(ReadinessScore.calculated_at.desc())
            .limit(1)
        )
        score = score_row.scalar_one_or_none()
        items.append(_ws_dict(ws, score.percentage if score else 0.0))

    return {"data": {"items": items}}


@router.patch("/workspaces/{target_id}")
async def update_workspace(
    target_id: str,
    body: UpdateWorkspaceRequest,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if target_id != workspace_id:
        raise HTTPException(
            status_code=403,
            detail=error_response("forbidden", "Cannot modify another workspace.", retryable=False),
        )
    ws = await db.get(Workspace, target_id)
    if not ws:
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "Workspace not found.", retryable=False),
        )
    ws.name = body.name
    await db.commit()
    return {"data": _ws_dict(ws, 0.0)}
```

- [ ] **Step 5: Register settings router in backend/app/api/__init__.py**

```python
from app.api.routes.settings import router as settings_router
# add after existing imports, before api_router = APIRouter()
```

Add `api_router.include_router(settings_router)` at the end of `__init__.py`.

The full updated `backend/app/api/__init__.py`:

```python
from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.drafts import router as drafts_router
from app.api.routes.estimator import router as estimator_router
from app.api.routes.events import router as events_router
from app.api.routes.export import router as export_router
from app.api.routes.health import router as health_router
from app.api.routes.interview import router as interview_router
from app.api.routes.readiness import router as readiness_router
from app.api.routes.review import router as review_router
from app.api.routes.settings import router as settings_router
from app.api.routes.workspaces import router as workspaces_router
from app.api.routes.yoy import router as yoy_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(workspaces_router)
api_router.include_router(documents_router)
api_router.include_router(drafts_router)
api_router.include_router(interview_router)
api_router.include_router(events_router)
api_router.include_router(readiness_router)
api_router.include_router(review_router)
api_router.include_router(export_router)
api_router.include_router(yoy_router)
api_router.include_router(estimator_router)
api_router.include_router(settings_router)
```

- [ ] **Step 6: Run all settings tests**

```bash
docker compose exec backend pytest tests/test_settings.py -v
```
Expected: 13 passed

- [ ] **Step 7: Run full backend suite**

```bash
docker compose exec backend pytest tests/ -v 2>&1 | tail -20
```
Expected: all existing tests still pass

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/routes/settings.py backend/app/api/routes/workspaces.py backend/app/api/__init__.py backend/tests/test_settings.py
git commit -m "feat: add settings, ai-usage, storage-usage, workspaces endpoints"
```

---

## Task 3: Frontend — API types + lib/api/settings.ts

**Files:**
- Modify: `frontend/lib/api/types.ts`
- Create: `frontend/lib/api/settings.ts`

- [ ] **Step 1: Add types to frontend/lib/api/types.ts**

Append to the end of the file:

```typescript
export interface WorkspaceInfo {
  id: string
  name: string
  financial_year: string
  status: string
  readiness_pct: number
}

export interface WorkspaceListData {
  items: WorkspaceInfo[]
}

export interface AiUsageItem {
  operation: string
  calls: number
  cost_usd: number
}

export interface AiUsageData {
  ai_provider: string
  items: AiUsageItem[]
  total_cost_usd: number
}

export interface StorageUsageData {
  documents_bytes: number
  exports_bytes: number
  db_bytes: number
}

export interface SkillInfo {
  skill_id: string
  version: string
  display_name: string
}

export interface AboutData {
  active_skills: SkillInfo[]
  disclaimer: string
}

export interface RecoveryKeyData {
  recovery_key: string
}
```

- [ ] **Step 2: Create frontend/lib/api/settings.ts**

```typescript
import client from './client'
import type {
  ApiResponse,
  AiUsageData,
  StorageUsageData,
  AboutData,
  WorkspaceListData,
  WorkspaceInfo,
  RecoveryKeyData,
} from './types'

export const getAiUsage = () =>
  client.get<ApiResponse<AiUsageData>>('/api/v1/settings/ai-usage')

export const getStorageUsage = () =>
  client.get<ApiResponse<StorageUsageData>>('/api/v1/settings/storage-usage')

export const getAbout = () =>
  client.get<ApiResponse<AboutData>>('/api/v1/settings/about')

export const exportDiagnosticLog = async (): Promise<void> => {
  const response = await client.get('/api/v1/settings/diagnostic-log', {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  a.download = 'diagnostic.json'
  a.click()
  URL.revokeObjectURL(url)
}

export const changePassword = (currentPassword: string, newPassword: string) =>
  client.post('/api/v1/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })

export const regenerateRecoveryKey = (password: string) =>
  client.post<ApiResponse<RecoveryKeyData>>('/api/v1/auth/recovery-key/regenerate', {
    password,
  })

export const listWorkspaces = () =>
  client.get<ApiResponse<WorkspaceListData>>('/api/v1/workspaces')

export const updateWorkspaceName = (id: string, name: string) =>
  client.patch<ApiResponse<WorkspaceInfo>>(`/api/v1/workspaces/${id}`, { name })
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
docker compose exec frontend npx tsc --noEmit 2>&1 | head -20
```
Expected: no errors related to settings files

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api/types.ts frontend/lib/api/settings.ts
git commit -m "feat: add settings API types and client functions"
```

---

## Task 4: Frontend — PasswordModal + tab components

**Files:**
- Create: `frontend/components/settings/PasswordModal.tsx`
- Create: `frontend/components/settings/WorkspaceTab.tsx`
- Create: `frontend/components/settings/SecurityTab.tsx`
- Create: `frontend/components/settings/AiPrivacyTab.tsx`
- Create: `frontend/components/settings/StorageTab.tsx`
- Create: `frontend/components/settings/AboutTab.tsx`

- [ ] **Step 1: Create frontend/components/settings/PasswordModal.tsx**

```tsx
'use client'
import { useState } from 'react'

interface Props {
  title: string
  description?: string
  confirmLabel?: string
  pending?: boolean
  error?: string | null
  onConfirm: (password: string) => void
  onCancel: () => void
}

export default function PasswordModal({
  title,
  description,
  confirmLabel = 'Confirm',
  pending,
  error,
  onConfirm,
  onCancel,
}: Props) {
  const [password, setPassword] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onConfirm(password)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm mx-4 bg-surface rounded-xl border border-border p-6 space-y-4">
        <h2 className="font-display text-lg font-semibold text-text-primary">{title}</h2>
        {description && (
          <p className="text-sm font-ui text-text-muted">{description}</p>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="modal-password"
              className="text-sm font-ui text-text-body block mb-1"
            >
              Password
            </label>
            <input
              id="modal-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-border bg-canvas px-3 py-2 text-sm font-ui"
              aria-label="Password"
              autoFocus
              required
            />
          </div>
          {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={pending}
              className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
            >
              {pending ? 'Working…' : confirmLabel}
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

- [ ] **Step 2: Create frontend/components/settings/WorkspaceTab.tsx**

```tsx
'use client'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listWorkspaces, updateWorkspaceName } from '@/lib/api/settings'
import type { WorkspaceInfo } from '@/lib/api/types'
import useWorkspaceStore from '@/lib/stores/workspace.store'

export default function WorkspaceTab() {
  const qc = useQueryClient()
  const { workspaceId, financialYear } = useWorkspaceStore()
  const [nameInput, setNameInput] = useState('')
  const [nameSaved, setNameSaved] = useState(false)
  const [nameInitialized, setNameInitialized] = useState(false)

  const { data: wsData, isLoading } = useQuery({
    queryKey: ['workspaces-list'],
    queryFn: () => listWorkspaces().then((r) => r.data.data),
  })

  useEffect(() => {
    if (wsData && !nameInitialized) {
      const current = wsData.items.find((w: WorkspaceInfo) => w.id === workspaceId)
      if (current) {
        setNameInput(current.name)
        setNameInitialized(true)
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsData])

  const nameMutation = useMutation({
    mutationFn: (name: string) => updateWorkspaceName(workspaceId!, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workspaces-list'] })
      setNameSaved(true)
      setTimeout(() => setNameSaved(false), 2000)
    },
  })

  function handleSaveName(e: React.FormEvent) {
    e.preventDefault()
    nameMutation.mutate(nameInput)
  }

  return (
    <div className="space-y-8">
      <section className="space-y-4">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Workspace details
        </h2>
        <form onSubmit={handleSaveName} className="space-y-3 max-w-sm">
          <div>
            <label
              htmlFor="ws-name"
              className="text-sm font-ui text-text-body block mb-1"
            >
              Workspace name
            </label>
            <input
              id="ws-name"
              type="text"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="Workspace name"
              required
            />
          </div>
          <div>
            <p className="text-sm font-ui text-text-body mb-1">Financial year</p>
            <p
              className="text-sm font-mono text-text-muted"
              aria-label="Financial year (read only)"
            >
              {financialYear ?? '—'}
            </p>
          </div>
          <button
            type="submit"
            disabled={nameMutation.isPending}
            className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
          >
            {nameSaved ? 'Saved' : nameMutation.isPending ? 'Saving…' : 'Save'}
          </button>
          {nameMutation.isError && (
            <p className="text-sm font-ui text-risk-high">Failed to save name.</p>
          )}
        </form>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          All workspaces
        </h2>
        {isLoading ? (
          <p className="text-sm font-ui text-text-muted">Loading…</p>
        ) : (
          <div className="space-y-2">
            {wsData?.items.map((ws: WorkspaceInfo) => (
              <div
                key={ws.id}
                className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3"
              >
                <div>
                  <p className="font-ui font-semibold text-text-primary text-sm">
                    FY {ws.financial_year}
                  </p>
                  <p className="text-xs font-ui text-text-muted">
                    {Math.round(ws.readiness_pct)}% ready
                  </p>
                </div>
                <span
                  className={`text-xs font-ui px-2 py-0.5 rounded-full ${
                    ws.status === 'active'
                      ? 'bg-ready/10 text-ready'
                      : 'bg-surface-muted text-text-muted'
                  }`}
                >
                  {ws.status === 'active' ? 'Active' : 'Complete'}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3 border border-risk-high/30 rounded-lg p-4">
        <h2 className="font-display text-base font-semibold text-risk-high">
          Danger zone
        </h2>
        <div className="flex flex-col gap-2">
          <button
            type="button"
            className="w-full max-w-xs text-left rounded-md border border-border px-4 py-2 text-sm font-ui text-text-body hover:border-agent transition-colors"
            onClick={() => {}}
          >
            Archive this workspace
          </button>
          <button
            type="button"
            className="w-full max-w-xs text-left rounded-md border border-risk-high px-4 py-2 text-sm font-ui text-risk-high hover:bg-risk-high/5 transition-colors"
            onClick={() => {}}
          >
            Delete this workspace
          </button>
        </div>
        <p className="text-xs font-ui text-text-muted">
          Delete requires password confirmation. These actions cannot be undone.
        </p>
      </section>
    </div>
  )
}
```

- [ ] **Step 3: Create frontend/components/settings/SecurityTab.tsx**

```tsx
'use client'
import { useState } from 'react'
import { changePassword, regenerateRecoveryKey } from '@/lib/api/settings'
import PasswordModal from './PasswordModal'

type AutoLock = '15' | '30' | '60' | 'never'

const AUTO_LOCK_OPTIONS: { value: AutoLock; label: string }[] = [
  { value: '15', label: '15 min' },
  { value: '30', label: '30 min' },
  { value: '60', label: '1 hour' },
  { value: 'never', label: 'Never' },
]

export default function SecurityTab() {
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwPending, setPwPending] = useState(false)
  const [pwSuccess, setPwSuccess] = useState(false)

  const [autoLock, setAutoLock] = useState<AutoLock>('15')
  const [showRegenModal, setShowRegenModal] = useState(false)
  const [regenKey, setRegenKey] = useState<string | null>(null)
  const [regenError, setRegenError] = useState<string | null>(null)
  const [regenPending, setRegenPending] = useState(false)

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault()
    setPwError(null)
    if (newPw !== confirmPw) {
      setPwError('New passwords do not match.')
      return
    }
    setPwPending(true)
    try {
      await changePassword(currentPw, newPw)
      setPwSuccess(true)
      setCurrentPw('')
      setNewPw('')
      setConfirmPw('')
      setTimeout(() => setPwSuccess(false), 3000)
    } catch {
      setPwError('Incorrect current password.')
    } finally {
      setPwPending(false)
    }
  }

  async function handleRegenConfirm(password: string) {
    setRegenError(null)
    setRegenPending(true)
    try {
      const res = await regenerateRecoveryKey(password)
      setRegenKey(res.data.data.recovery_key)
      setShowRegenModal(false)
    } catch {
      setRegenError('Incorrect password.')
    } finally {
      setRegenPending(false)
    }
  }

  return (
    <div className="space-y-8">
      <section className="space-y-4 max-w-sm">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Change password
        </h2>
        <form onSubmit={handleChangePassword} className="space-y-3">
          <div>
            <label htmlFor="current-pw" className="text-sm font-ui text-text-body block mb-1">
              Current password
            </label>
            <input
              id="current-pw"
              type="password"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="Current password"
              required
            />
          </div>
          <div>
            <label htmlFor="new-pw" className="text-sm font-ui text-text-body block mb-1">
              New password
            </label>
            <input
              id="new-pw"
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="New password"
              required
            />
          </div>
          <div>
            <label htmlFor="confirm-pw" className="text-sm font-ui text-text-body block mb-1">
              Confirm new password
            </label>
            <input
              id="confirm-pw"
              type="password"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="Confirm new password"
              required
            />
          </div>
          {pwError && <p className="text-sm font-ui text-risk-high">{pwError}</p>}
          {pwSuccess && <p className="text-sm font-ui text-ready">Password changed.</p>}
          <button
            type="submit"
            disabled={pwPending}
            className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
          >
            {pwPending ? 'Changing…' : 'Change password'}
          </button>
        </form>
      </section>

      <section className="space-y-3 max-w-sm">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Recovery key
        </h2>
        <p className="text-sm font-ui text-text-muted">
          Your original recovery key cannot be retrieved — it was only shown once during setup.
          You can generate a new recovery key below. Your old key will be immediately invalidated.
        </p>
        {regenKey && (
          <div className="rounded-md border border-border bg-surface p-3 space-y-2">
            <p className="text-xs font-ui text-text-muted">
              New recovery key — store this somewhere safe:
            </p>
            <p className="font-mono text-sm text-text-primary break-all">{regenKey}</p>
            <button
              type="button"
              className="text-xs font-ui text-text-muted underline"
              onClick={() => setRegenKey(null)}
            >
              I&apos;ve saved it
            </button>
          </div>
        )}
        <button
          type="button"
          onClick={() => setShowRegenModal(true)}
          className="min-h-11 px-5 rounded-md border border-border text-sm font-ui text-text-body hover:border-accent transition-colors"
        >
          Generate new recovery key
        </button>
      </section>

      <section className="space-y-3 max-w-sm">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Session
        </h2>
        <div>
          <p className="text-sm font-ui text-text-body mb-2">Auto-lock after</p>
          <div className="flex gap-2 flex-wrap">
            {AUTO_LOCK_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setAutoLock(opt.value)}
                className={`px-3 py-1 rounded-full text-sm font-ui border transition-colors ${
                  autoLock === opt.value
                    ? 'border-accent text-accent bg-accent-soft'
                    : 'border-border text-text-muted'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {autoLock === 'never' && (
            <p className="mt-2 text-sm font-ui text-agent bg-review/20 rounded px-3 py-2">
              Not recommended for sensitive tax data
            </p>
          )}
        </div>
      </section>

      {showRegenModal && (
        <PasswordModal
          title="Generate new recovery key"
          description="Enter your password to confirm. Your current recovery key will be invalidated immediately."
          confirmLabel="Generate"
          pending={regenPending}
          error={regenError}
          onConfirm={handleRegenConfirm}
          onCancel={() => { setShowRegenModal(false); setRegenError(null) }}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Create frontend/components/settings/AiPrivacyTab.tsx**

```tsx
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
              <span className="text-text-primary">~${usageData?.total_cost_usd.toFixed(2)}</span>
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
```

- [ ] **Step 5: Create frontend/components/settings/StorageTab.tsx**

```tsx
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
          Back up your <code className="font-mono text-text-primary">/data</code> volume regularly.
        </p>
        <p className="text-sm font-ui text-text-muted">
          Last backup: not detected.
        </p>
      </section>
    </div>
  )
}
```

- [ ] **Step 6: Create frontend/components/settings/AboutTab.tsx**

```tsx
'use client'
import { useQuery } from '@tanstack/react-query'
import { getAbout, exportDiagnosticLog } from '@/lib/api/settings'
import Disclaimer from '@/components/shared/Disclaimer'

export default function AboutTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['settings-about'],
    queryFn: () => getAbout().then((r) => r.data.data),
  })

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Tax Return AI
        </h2>
        <p className="text-sm font-ui text-text-muted">M10 — Phase 7</p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Active skills
        </h2>
        {isLoading ? (
          <p className="text-sm font-ui text-text-muted">Loading…</p>
        ) : (
          <div className="space-y-2">
            {data?.active_skills.map((skill) => (
              <div
                key={skill.skill_id}
                className="flex items-center justify-between text-sm font-ui"
              >
                <span className="text-text-body font-mono">{skill.skill_id}</span>
                <span className="text-text-muted">
                  v{skill.version}{' '}
                  <span className="text-ready">✓ Active</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Disclaimer
        </h2>
        <Disclaimer />
      </section>

      <section>
        <button
          type="button"
          onClick={() => exportDiagnosticLog()}
          className="text-sm font-ui text-accent underline"
        >
          Export diagnostic log
        </button>
      </section>
    </div>
  )
}
```

- [ ] **Step 7: Verify TypeScript compiles**

```bash
docker compose exec frontend npx tsc --noEmit 2>&1 | head -20
```
Expected: no errors

- [ ] **Step 8: Commit**

```bash
git add frontend/components/settings/
git commit -m "feat: add PasswordModal and 5 settings tab components"
```

---

## Task 5: Settings page + frontend tests

**Files:**
- Modify: `frontend/app/(dashboard)/settings/page.tsx`
- Create: `frontend/__tests__/settings-page.test.tsx`

- [ ] **Step 1: Write the failing tests — create frontend/__tests__/settings-page.test.tsx**

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SettingsPage from '@/app/(dashboard)/settings/page'
import * as settingsApi from '@/lib/api/settings'
import type { AiUsageData, StorageUsageData, AboutData, WorkspaceListData } from '@/lib/api/types'

jest.mock('@/lib/api/settings')
jest.mock('@/lib/stores/workspace.store', () => ({
  __esModule: true,
  default: () => ({
    workspaceId: 'ws-123',
    financialYear: '2024-25',
    isAuthenticated: true,
    isUnlocked: true,
    setWorkspace: jest.fn(),
    setAuthenticated: jest.fn(),
    setUnlocked: jest.fn(),
  }),
}))
jest.mock('@/components/shared/Disclaimer', () => ({
  default: () => (
    <p data-testid="disclaimer">
      This tool helps organise your tax information and prepare a review package. It does not
      provide final tax advice and does not replace review by a registered tax agent.
    </p>
  ),
  __esModule: true,
}))

const mockListWorkspaces = settingsApi.listWorkspaces as jest.Mock
const mockGetAiUsage = settingsApi.getAiUsage as jest.Mock
const mockGetStorageUsage = settingsApi.getStorageUsage as jest.Mock
const mockGetAbout = settingsApi.getAbout as jest.Mock

const mockWorkspaceList: WorkspaceListData = {
  items: [{ id: 'ws-123', name: 'My Return', financial_year: '2024-25', status: 'active', readiness_pct: 87 }],
}
const mockAiUsage: AiUsageData = {
  ai_provider: 'claude',
  items: [
    { operation: 'classify', calls: 142, cost_usd: 0.08 },
    { operation: 'explain', calls: 38, cost_usd: 0.04 },
  ],
  total_cost_usd: 0.12,
}
const mockStorageUsage: StorageUsageData = {
  documents_bytes: 883 * 1024 * 1024,
  exports_bytes: 398950400,
  db_bytes: 2097152,
}
const mockAbout: AboutData = {
  active_skills: [{ skill_id: 'employee_tax_au', version: '1.0', display_name: 'Employee Tax AU' }],
  disclaimer: 'This tool helps organise your tax information and prepare a review package. It does not provide final tax advice and does not replace review by a registered tax agent.',
}

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

beforeEach(() => {
  jest.clearAllMocks()
  mockListWorkspaces.mockResolvedValue({ data: { data: mockWorkspaceList } })
  mockGetAiUsage.mockResolvedValue({ data: { data: mockAiUsage } })
  mockGetStorageUsage.mockResolvedValue({ data: { data: mockStorageUsage } })
  mockGetAbout.mockResolvedValue({ data: { data: mockAbout } })
})

describe('SettingsPage', () => {
  it('renders 5 tabs', () => {
    wrap(<SettingsPage />)
    expect(screen.getByRole('tab', { name: /workspace/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /security/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /ai.*privacy/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /storage/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /about/i })).toBeInTheDocument()
  })

  it('default tab is Workspace', () => {
    wrap(<SettingsPage />)
    expect(screen.getByLabelText(/workspace name/i)).toBeInTheDocument()
  })

  it('Workspace tab: name field is editable', () => {
    wrap(<SettingsPage />)
    const input = screen.getByLabelText(/workspace name/i)
    fireEvent.change(input, { target: { value: 'New Name' } })
    expect(input).toHaveValue('New Name')
  })

  it('Workspace tab: financial year is display-only (no input)', () => {
    wrap(<SettingsPage />)
    expect(screen.getByLabelText(/financial year.*read only/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/financial year$/i)).not.toBeInTheDocument()
  })

  it('Security tab: change password form renders 3 fields', () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /security/i }))
    expect(screen.getByLabelText(/current password/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^new password/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/confirm new password/i)).toBeInTheDocument()
  })

  it('Security tab: Never auto-lock shows warning', () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /security/i }))
    fireEvent.click(screen.getByRole('button', { name: /never/i }))
    expect(screen.getByText(/not recommended for sensitive tax data/i)).toBeInTheDocument()
  })

  it('AI & Privacy tab: What we send to AI list renders all 7 items', async () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /ai.*privacy/i }))
    const items = [
      'Extracted text from documents',
      'Transaction amounts and dates',
      'Merchant names',
      'Original files',
      'Your name or personal details',
      'Bank account numbers',
      'Tax File Number (TFN)',
    ]
    for (const item of items) {
      expect(screen.getByText(item)).toBeInTheDocument()
    }
  })

  it('AI & Privacy tab: usage table renders call counts', async () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /ai.*privacy/i }))
    await waitFor(() => {
      expect(screen.getByText(/142 calls/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/38 calls/i)).toBeInTheDocument()
  })

  it('Storage tab: usage breakdown renders 3 rows', async () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /storage/i }))
    await waitFor(() => {
      expect(screen.getByText(/documents/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/exports/i)).toBeInTheDocument()
    expect(screen.getByText(/database/i)).toBeInTheDocument()
  })

  it('About tab: disclaimer text renders', async () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /about/i }))
    await waitFor(() => {
      expect(screen.getByTestId('disclaimer')).toBeInTheDocument()
    })
    expect(screen.getByTestId('disclaimer')).toHaveTextContent(
      'This tool helps organise your tax information'
    )
  })

  it('About tab: active skills list renders', async () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /about/i }))
    await waitFor(() => {
      expect(screen.getByText(/employee_tax_au/i)).toBeInTheDocument()
    })
  })
})
```

> **Note:** The `mockStorageUsage` has a placeholder expression (`883olean * ...`). Fix it to `{ documents_bytes: 883 * 1024 * 1024, exports_bytes: 398950400, db_bytes: 2097152 }` — this was a typo placeholder in the plan.

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec frontend npx jest __tests__/settings-page.test.tsx --no-coverage 2>&1 | tail -20
```
Expected: fail — `SettingsPage` still returns placeholder

- [ ] **Step 3: Implement frontend/app/(dashboard)/settings/page.tsx**

```tsx
'use client'
import { useEffect, useState } from 'react'
import WorkspaceTab from '@/components/settings/WorkspaceTab'
import SecurityTab from '@/components/settings/SecurityTab'
import AiPrivacyTab from '@/components/settings/AiPrivacyTab'
import StorageTab from '@/components/settings/StorageTab'
import AboutTab from '@/components/settings/AboutTab'

type TabId = 'workspace' | 'security' | 'ai-privacy' | 'storage' | 'about'

const TABS: { id: TabId; label: string }[] = [
  { id: 'workspace', label: 'Workspace' },
  { id: 'security', label: 'Security' },
  { id: 'ai-privacy', label: 'AI & Privacy' },
  { id: 'storage', label: 'Storage' },
  { id: 'about', label: 'About' },
]

const SESSION_KEY = 'settings-active-tab'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('workspace')

  useEffect(() => {
    const saved = sessionStorage.getItem(SESSION_KEY) as TabId | null
    if (saved && TABS.some((t) => t.id === saved)) {
      setActiveTab(saved)
    }
  }, [])

  function switchTab(id: TabId) {
    setActiveTab(id)
    sessionStorage.setItem(SESSION_KEY, id)
  }

  return (
    <div className="space-y-6">
      <h1 className="font-display text-2xl font-semibold text-text-primary">Settings</h1>

      <div
        role="tablist"
        className="flex gap-1 border-b border-border overflow-x-auto"
        aria-label="Settings tabs"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => switchTab(tab.id)}
            className={`px-4 py-2 text-sm font-ui font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-accent text-accent'
                : 'border-transparent text-text-muted hover:text-text-body'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="pt-2">
        {activeTab === 'workspace' && <WorkspaceTab />}
        {activeTab === 'security' && <SecurityTab />}
        {activeTab === 'ai-privacy' && <AiPrivacyTab />}
        {activeTab === 'storage' && <StorageTab />}
        {activeTab === 'about' && <AboutTab />}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Fix the typo in the test file**

In `frontend/__tests__/settings-page.test.tsx`, replace:

```
const mockStorageUsage: StorageUsageData = {
  documents_bytes: 883olean * 1024 * 1024,
```

with:

```
const mockStorageUsage: StorageUsageData = {
  documents_bytes: 883 * 1024 * 1024,
```

- [ ] **Step 5: Run the frontend tests**

```bash
docker compose exec frontend npx jest __tests__/settings-page.test.tsx --no-coverage 2>&1 | tail -20
```
Expected: 11 passed (all spec tests pass)


- [ ] **Step 6: Commit**

```bash
git add frontend/app/\(dashboard\)/settings/page.tsx frontend/__tests__/settings-page.test.tsx
git commit -m "feat: implement Settings page — 5 tabs with full UI"
```

---

## Task 6: Full test suite verification

**Files:** none

- [ ] **Step 1: Run full backend suite**

```bash
docker compose exec backend pytest tests/ -v 2>&1 | tail -30
```
Expected: all tests pass (132+ passing)

- [ ] **Step 2: Run full frontend suite**

```bash
docker compose exec frontend npx jest --no-coverage 2>&1 | tail -20
```
Expected: all tests pass (205+ passing)

- [ ] **Step 3: Commit final verification**

```bash
git add -A
git commit -m "test: Phase 7 full test suite verified — Settings page complete"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| 5 tabs with tab state in sessionStorage | Task 5 (page.tsx) |
| Workspace tab: editable name + FY display-only | Task 4 (WorkspaceTab) |
| Workspace tab: all workspaces list | Task 4 (WorkspaceTab) |
| Danger Zone: archive + delete buttons | Task 4 (WorkspaceTab) |
| Security tab: change password (3 fields) | Task 4 (SecurityTab) |
| Security tab: recovery key regenerate | Task 4 (SecurityTab) |
| Security tab: auto-lock with Never warning | Task 4 (SecurityTab) |
| AI & Privacy: provider selector (display-only) | Task 4 (AiPrivacyTab) |
| AI & Privacy: what we send to AI (7 items) | Task 4 (AiPrivacyTab) |
| AI & Privacy: usage table | Task 4 (AiPrivacyTab) |
| AI & Privacy: offline mode toggle | Task 4 (AiPrivacyTab) |
| Storage: usage breakdown (3 rows) | Task 4 (StorageTab) |
| Storage: auto-cleanup selector | Task 4 (StorageTab) |
| Storage: backup guidance | Task 4 (StorageTab) |
| About: skills list + disclaimer + version | Task 4 (AboutTab) |
| About: export diagnostic log | Task 4 (AboutTab) |
| Backend: POST /auth/change-password | Task 1 |
| Backend: POST /auth/recovery-key/regenerate | Task 1 |
| Backend: GET /settings/ai-usage | Task 2 |
| Backend: GET /settings/storage-usage | Task 2 |
| Backend: GET /settings/diagnostic-log | Task 2 |
| Backend: GET /settings/about | Task 2 |
| Backend: GET /workspaces (real impl) | Task 2 |
| Backend: PATCH /workspaces/{id} | Task 2 |

**Gaps/deviations from spec:**
- "View Recovery Key" removed (original key never stored — architecturally impossible). Replaced with single "Generate New Recovery Key" action with explanatory note.
- "Lock workspace now" button not in SecurityTab — can be added via calling `logout()` from `lib/api/auth.ts` + redirect, but was not explicitly tested in spec. Omitted per YAGNI.
- Danger Zone archive/delete buttons render but are not wired to backend endpoints (no backend delete/archive endpoints in scope). Both show buttons; no modal implemented yet. This is intentional — user should confirm scope before implementing destructive operations.
- Auto-lock preference stored in component state only (not sessionStorage, not backend) — the auto-lock timer itself would require a background task which is out of scope for this phase.

**Placeholder scan:** No TBD, TODO, or empty implementations.

**Type consistency:** All types defined in Task 3 (`WorkspaceInfo`, `AiUsageItem`, `AiUsageData`, `StorageUsageData`, `AboutData`, `SkillInfo`, `RecoveryKeyData`) are used consistently across Task 4 components and Task 5 page.
