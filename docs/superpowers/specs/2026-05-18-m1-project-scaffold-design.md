# M1 Design: Project Scaffold + Docker Compose + DB Schema + Health Check
**Date:** 2026-05-18
**Milestone:** M1 of 11
**Status:** Approved — ready for implementation

---

## Overview

M1 establishes the complete project skeleton. No business logic is implemented.
Every file location, Docker configuration, environment variable, and database
table that later milestones depend on must exist and be correct after M1.

**Deliverables:**
- Backend: FastAPI app, all 16 DB tables (single Alembic migration), `GET /health`
- Frontend: Next.js 14 shell, full design token system, routing skeleton, health page
- Infrastructure: `docker-compose.yml`, `docker-compose.dev.yml`, `.env.example`, `README.md`

---

## Section 1: Directory Structure

Matches ARCHITECTURE.md §3 exactly. No files outside these locations.

```
tax-return-cc/
├── README.md
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── Makefile                          (already exists — no changes)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── errors.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── models.py
│   │   ├── repositories/
│   │   │   └── __init__.py           (stub — M3+)
│   │   ├── storage/
│   │   │   ├── base.py               (stub — M3)
│   │   │   ├── local.py              (stub — M3)
│   │   │   └── s3.py                 (stub — future)
│   │   ├── ai/
│   │   │   ├── base.py               (stub — M4)
│   │   │   └── providers/
│   │   │       ├── claude.py         (stub — M4)
│   │   │       ├── openai.py         (stub — future)
│   │   │       └── ollama.py         (stub — future local model)
│   │   ├── skills/
│   │   │   ├── base.py               (stub — M5)
│   │   │   └── registry.py           (stub — M5)
│   │   ├── engines/
│   │   │   ├── evidence.py           (stub — M3)
│   │   │   ├── interview.py          (stub — M6)
│   │   │   ├── readiness.py          (stub — M7)
│   │   │   ├── review.py             (stub — M8)
│   │   │   ├── export.py             (stub — M9)
│   │   │   ├── yoy.py                (stub — M9)
│   │   │   └── estimator.py          (stub — M9: tax figure summariser ONLY,
│   │   │                              NOT a calculator — see ARCHITECTURE.md §21)
│   │   ├── constants/
│   │   │   ├── __init__.py           (stub — M5)
│   │   │   ├── categories.py         (stub — M5)
│   │   │   └── fy_rules/
│   │   │       └── .gitkeep          (empty dir — M5 fills this)
│   │   └── api/
│   │       └── routes/
│   │           ├── health.py         (real — M1)
│   │           ├── auth.py           (stub — M2)
│   │           ├── workspaces.py     (stub — M2)
│   │           ├── documents.py      (stub — M3)
│   │           ├── interview.py      (stub — M6)
│   │           ├── events.py         (stub — M3)
│   │           ├── review.py         (stub — M8)
│   │           └── export.py         (stub — M9)
│   └── tests/
│       ├── conftest.py
│       └── test_health.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    ├── app/
    │   ├── layout.tsx                root layout, loads globals.css
    │   ├── health/
    │   │   └── page.tsx              real — health check UI
    │   ├── (auth)/
    │   │   └── login/
    │   │       └── page.tsx          stub — M2
    │   └── (dashboard)/
    │       ├── layout.tsx            stub — M10
    │       ├── readiness/page.tsx    stub — M10
    │       ├── journey/page.tsx      stub — M10
    │       ├── review/page.tsx       stub — M10
    │       ├── evidence/page.tsx     stub — M10
    │       ├── export/page.tsx       stub — M10
    │       └── settings/page.tsx     stub — M10
    ├── components/
    │   └── shared/
    │       └── Disclaimer.tsx        real — compliance disclaimer
    ├── lib/
    │   ├── api/
    │   │   ├── client.ts             real — axios instance
    │   │   └── types.ts              real — ApiSuccess / ApiError shapes
    │   ├── stores/
    │   │   ├── workspace.store.ts    stub — M6
    │   │   └── interview.store.ts    stub — M6
    │   └── hooks/
    │       ├── useSSE.ts             stub — M3
    │       └── useReadiness.ts       stub — M7
    └── styles/
        └── globals.css               real — all CSS variables from DESIGN.md
```

---

## Section 2: Backend Scaffold

### `backend/requirements.txt`

No version pinning. After first successful build run `make freeze` to capture
exact versions. The `freeze` Makefile target writes `backend/requirements.lock`.

```
# ── Web framework ──────────────────────────────────────────────
fastapi
uvicorn[standard]
python-multipart
aiofiles

# ── Validation & settings ──────────────────────────────────────
pydantic[email]
pydantic-settings

# ── Database ───────────────────────────────────────────────────
sqlalchemy[asyncio]
aiosqlite
alembic
greenlet

# ── Auth & security ────────────────────────────────────────────
bcrypt
cryptography
pyzipper
itsdangerous

# ── AI providers ───────────────────────────────────────────────
anthropic
openai
httpx

# ── OCR & document processing ──────────────────────────────────
pdfplumber
pytesseract
pillow

# ── Export ─────────────────────────────────────────────────────
weasyprint
jinja2

# ── File validation ────────────────────────────────────────────
python-magic

# ── Testing ────────────────────────────────────────────────────
pytest
pytest-asyncio
pytest-cov
```

> `poppler-utils` is an apt system package — NOT a pip package. Do not add it here.

### `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-eng \
    # WeasyPrint native deps
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libfreetype6 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    # pdfplumber
    poppler-utils \
    # python-magic
    libmagic1 \
    # SQLite shell (make db-shell)
    sqlite3 \
    # Health check (make health)
    curl \
    # Build tools for pip packages with C extensions
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `app/config.py`

`pydantic-settings` `Settings` class with one field per env var from
ARCHITECTURE.md §5. Module-level singleton: `settings = Settings()`.
All other modules import `from app.config import settings` — never `os.getenv()`.

### `app/db/base.py`

Async SQLAlchemy engine from `settings.DATABASE_URL`. `Base = DeclarativeBase()`.
`AsyncSessionLocal` factory. `get_db()` async generator for FastAPI dependency
injection.

### `app/db/models.py`

All 16 tables as SQLAlchemy ORM classes:

| # | Table | Notes |
|---|-------|-------|
| 1 | Workspace | |
| 2 | TaxProfile | `active_skills` JSON column |
| 3 | InterviewSession | Multiple JSON columns for state machine |
| 4 | Document | `extracted_fields` JSON, `sha256_hash` indexed |
| 5 | TaxEvent | `correction_history`, `inline_answers` JSON |
| 6 | ReviewItem | `inline_questions`, `inline_answers` JSON |
| 7 | ReadinessScore | `breakdown`, `missing_items` JSON |
| 8 | ExportRecord | `skills_active` JSON |
| 9 | WorkspaceSecurity | DEK fields, unlock session |
| 10 | AuditLog | AI usage tracking fields |
| 11 | YoySuggestion | |
| 12 | SkillVersionLock | |
| 13 | FeatureFlag | |
| 14 | BackgroundJob | `payload`, `result` JSON |
| 15 | TaxDeadlineReminder | `reminders` JSON |
| 16 | EncryptedDraft | `encrypted_content` |

Rules:
- All foreign keys have indexes
- All `DateTime` columns use `timezone=True`
- JSON columns use SQLAlchemy `JSON` type
- No business logic in models

### `alembic/env.py`

Imports `Base.metadata` from `app.db.models`. Uses async engine from config.
Single migration file `0001_initial_schema.py` — all 16 tables.

### `app/main.py`

FastAPI app with `lifespan` context manager:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_alembic_upgrade()   # runs on every startup
    yield
```

Middleware (in order):
1. `CORSMiddleware` — origins from `settings.CORS_ORIGINS` (exact match, never `*`)
2. `SessionMiddleware` — `secret_key=settings.SECRET_KEY`

Routers mounted: health only. All other route files imported as stubs.

### `app/errors.py`

`AppError(Exception)` with `error_code`, `message`, `action`, `retryable`.
FastAPI exception handler formats to ARCHITECTURE.md §6 unified shape.
Handler catches `AppError` and generic `Exception` — generic exceptions return
`error_code: "internal_error"` with no internal details exposed.

### `app/api/routes/health.py`

```
GET /health → 200 always
{
  "status": "ok" | "degraded",
  "db": "ok" | "error",
  "storage": "ok" | "error"
}
```

- DB check: `SELECT 1` via async session. Failure → `db: "error"`, `status: "degraded"`
- Storage check: `Path(settings.STORAGE_PATH).exists()`. Failure → `storage: "error"`, `status: "degraded"`
- Always returns HTTP 200 (Docker healthcheck must not restart on a missing storage path)

### `tests/conftest.py`

- In-memory SQLite test database (`sqlite+aiosqlite:///:memory:`)
- Tables created directly from `Base.metadata.create_all()` — migrations skipped in tests
- `AsyncClient` via `httpx` for endpoint testing
- `missing_storage_settings` fixture overrides `settings.STORAGE_PATH` to
  `"/nonexistent/path/that/does/not/exist"` — real code path, no `Path.exists()` mocking

### `tests/test_health.py`

| Test | Assertion |
|------|-----------|
| `test_health_ok` | `{"status": "ok", "db": "ok", "storage": "ok"}`, HTTP 200 |
| `test_health_storage_missing` | `{"status": "degraded", "storage": "error"}`, HTTP 200 |

---

## Section 3: Frontend Shell

### `frontend/Dockerfile`

Two-stage build:
- Stage 1 (`node:20-alpine`): `npm ci` + `npm run build` (Next.js standalone output)
- Stage 2: copies standalone bundle only — no `node_modules` in production image

Dev compose overrides command to `npm run dev` via volume mount.
Dockerfile is only exercised on `make build` (production).

### `package.json` dependencies

```
next@14, react, react-dom, typescript
tailwindcss, postcss, autoprefixer
axios
zustand
@tanstack/react-query
react-hook-form
lucide-react
next-pwa
```
Dev: `@types/react`, `@types/node`, `jest`, `@testing-library/react`,
`@testing-library/jest-dom`

### `styles/globals.css`

All CSS variables from DESIGN.md:
- Light mode colour tokens (canvas, surface, text, accent, status colours)
- Dark mode tokens in `@media (prefers-color-scheme: dark)`
- Typography scale tokens
- Spacing and radius tokens

Single source of truth. No other file hardcodes colours or font sizes.

### `tailwind.config.js`

`theme.extend.colors` maps Tailwind class names to CSS variables:
```js
colors: {
  canvas:  'var(--color-canvas)',
  surface: 'var(--color-surface)',
  accent:  'var(--color-accent)',
  // ... all tokens
}
```
`content`: `['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}']`

### `next.config.js`

Wrapped with `next-pwa`. Service worker enabled in production, disabled in dev
(avoids service worker conflicts during development).
`reactStrictMode: true`.

### `components/shared/Disclaimer.tsx`

Real component, not a stub. Required on every AI output surface
(ARCHITECTURE.md §1):

```tsx
export function Disclaimer() {
  return (
    <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
      This tool helps organise your tax information and prepare a review package.
      It does not provide final tax advice and does not replace review by
      a registered tax agent.
    </p>
  )
}
```

Uses CSS variables directly — no Tailwind dependency.

### `lib/api/client.ts`

```typescript
import axios from 'axios';

const client = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

export default client;
```

No interceptors or auth headers — those belong to M2.

### `lib/api/types.ts`

```typescript
export interface ApiSuccess<T> { data: T; status: 'ok' }
export interface ApiError {
  error_code: string;
  message: string;
  action: string | null;
  retryable: boolean;
}
```

### `app/health/page.tsx`

Three states — no design tokens, intentionally unstyled:
- **Loading:** `"Checking connection..."`
- **Success:** JSON response rendered as `<pre>`
- **Error:** `"Cannot reach backend — is the server running?"` (raw axios error never shown)

Diagnostic tool only. Removed or repurposed in M10.

---

## Section 4: Docker Compose & Environment

### `docker-compose.yml` and `docker-compose.dev.yml`

Exactly as specified in ARCHITECTURE.md §4. No deviations.

**Volume isolation — important:**

| Environment | Volume type | Path | Cleared by |
|-------------|-------------|------|------------|
| Production | Bind mount | `/home/pi/tax-return-data` | `make restore` only |
| Dev | Docker-managed | `tax_dev_data` | `make clean-all` |

These two volumes are completely independent. `make clean-all` removes the dev
volume but never touches the production bind mount. Production data is never
at risk from any `make` command except `make restore`.

### `.env.example`

All variables from ARCHITECTURE.md §5. `APP_PASSWORD_HASH` documented with
the exact bcrypt generation command:

```bash
# Generate via: make shell-be, then:
# python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
APP_PASSWORD_HASH=
```

### `README.md`

Minimal first-run instructions only:

```markdown
## First-time setup on Raspberry Pi

1. git clone <repo> && cd tax-return-cc
2. make setup-dirs
3. make env           # then edit .env with your values
4. make dev-build     # first build (~15–20 min on Pi)
5. make health        # confirm everything is running
```

**`make setup-dirs` must run before `make dev` or `make up`.** The lifespan
migration runner will fail if `/home/pi/tax-return-data/db/` does not exist.

---

## Implementation Notes

- `poppler-utils` is an apt package only — not in `requirements.txt`
- `python-jose` is not needed — session cookies use `itsdangerous` (via Starlette `SessionMiddleware`), not JWT
- `alembic upgrade head` runs on every startup via `lifespan` — no manual `make migrate` needed after `make dev`
- Health endpoint always returns HTTP 200 — degraded state does not trigger Docker container restart
- Test DB uses `Base.metadata.create_all()` directly — migrations are not run in tests
- All 16 tables in one migration file (`0001_initial_schema.py`)
- No business logic in M1 — all non-health route files are stubs
