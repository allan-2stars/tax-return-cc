# ARCHITECTURE.md — Tax Return AI
# Single source of truth for all design decisions.
# Claude Code must read this before writing any code.
# Last updated: May 2026

---

## 0. Project Overview

**Product:** AI-guided Australian tax preparation workspace
**Target user:** Australian individual taxpayer (PAYG employee, may have crypto/WFH/investments)
**Core value:** Organise documents → prepare a review package for a registered tax agent
**Not:** A tax lodgement tool. Not ATO-connected. Not tax advice.

### Compliance boundary (non-negotiable)
```
✅ Safe labels:
   Tax document organiser
   Tax-ready evidence package generator
   Pre-tax-agent preparation tool

❌ Never use:
   ATO-approved / Ready to lodge / Guaranteed deduction
   AI tax agent / Automatic ATO submission / Final refund
```

### Persistent disclaimer (shown on every AI output surface)
```
"This tool helps organise your tax information and prepare a review package.
 It does not provide final tax advice and does not replace review by
 a registered tax agent."
```

---

## 1. Deployment Architecture

### Runtime Environment
```
Development machine:  Developer's laptop (Claude Code runs here)
Deployment target:    Raspberry Pi — Ubuntu Server CLI-only
Orchestration:        Docker Compose
Tunnel:               Cloudflare Tunnel (already configured)
Domain example:
  Frontend → https://taxcc.signpega.com
  Backend  → https://taxcc-api.signpega.com
```

### Port Mapping
```
Service     Host port   Container port
frontend    3060        3000
backend     8060        8000
```

### Data Persistence
```
All persistent data lives in a single Docker volume:
  /home/pi/tax-return-data/     (bind mount on Pi)
    ├── db/
    │   └── tax_return.db       SQLite database
    ├── documents/
    │   └── {workspace_id}/
    │       └── {document_id}/
    │           ├── original.*  Original file (write-once, never modified)
    │           └── metadata.json
    └── exports/
        └── {workspace_id}/
            └── {export_id}.zip Encrypted review packages
```

### Future Migration Path
```
Docker Compose (Pi) → Tauri Desktop App → PWA Mobile → SaaS
All enabled by environment variables — zero code changes required.
```

---

## 2. Tech Stack

### Backend
```
Language:       Python 3.11+
Framework:      FastAPI
ORM:            SQLAlchemy (async)
Migrations:     Alembic (auto-run on startup)
Validation:     Pydantic v2
OCR:            pdfplumber (primary) + Tesseract (fallback)
PDF generation: WeasyPrint + Jinja2
Encryption:     pyzipper (AES-256), bcrypt, cryptography
Task runner:    FastAPI BackgroundTasks (light tasks)
                DB job table (Export generation — must survive restart)
Testing:        pytest + pytest-asyncio
```

### Frontend
```
Framework:      Next.js 14 (App Router)
Language:       TypeScript (strict mode)
Styling:        Tailwind CSS (core utilities only, no arbitrary values)
State:          Zustand (global) + React Query (server state)
HTTP:           axios (wrapped in /lib/api/)
Realtime:       EventSource API (SSE)
Forms:          React Hook Form
Icons:          Lucide React
Testing:        Jest + React Testing Library
PWA:            next-pwa (configured from day one)
```

### Design System
```
Source of truth: DESIGN.md
All colours, typography, spacing as CSS variables in globals.css
Tailwind theme extends those variables
No inline colours — always use CSS variables
Mobile-first, all components responsive
```

---

## 3. Project Structure

```
tax-return-ai/
├── CLAUDE.md                   Claude Code behaviour rules
├── ARCHITECTURE.md             This file
├── DESIGN.md                   UI design system
├── Makefile                    Docker convenience commands
├── docker-compose.yml          Production
├── docker-compose.dev.yml      Development overrides
├── .env.example                All env vars documented
├── .env                        Local secrets (never commit)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                DB migrations
│   ├── app/
│   │   ├── main.py             FastAPI app, middleware, startup
│   │   ├── config.py           All settings from env vars
│   │   ├── db/
│   │   │   ├── base.py         SQLAlchemy Base
│   │   │   └── models.py       All ORM models
│   │   ├── repositories/       All DB access (no raw SQL elsewhere)
│   │   ├── storage/
│   │   │   ├── base.py         StorageBackend ABC
│   │   │   ├── local.py        Docker volume backend
│   │   │   └── s3.py           Future S3 backend
│   │   ├── ai/
│   │   │   ├── base.py         AIProvider ABC + AIAdapter
│   │   │   └── providers/
│   │   │       ├── claude.py
│   │   │       ├── openai.py   Future
│   │   │       └── ollama.py   Future
│   │   ├── skills/
│   │   │   ├── base.py         TaxSkill ABC
│   │   │   ├── registry.py     SkillRegistry
│   │   │   └── employee_tax_au/
│   │   │       ├── skill.yaml
│   │   │       ├── __init__.py
│   │   │       └── calculator.py
│   │   ├── engines/
│   │   │   ├── evidence.py     Upload pipeline
│   │   │   ├── interview.py    State machine
│   │   │   ├── readiness.py    Score calculation
│   │   │   ├── review.py       Queue management
│   │   │   ├── export.py       Package generation
│   │   │   ├── yoy.py          Year-over-year suggestions
│   │   │   └── estimator.py    Tax figure summariser
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── auth.py
│   │   │       ├── workspaces.py
│   │   │       ├── documents.py
│   │   │       ├── interview.py
│   │   │       ├── events.py
│   │   │       ├── review.py
│   │   │       ├── export.py
│   │   │       └── health.py
│   │   ├── constants/          Tax categories, risk rules, FY rules
│   │   │   ├── categories.py
│   │   │   └── fy_rules/
│   │   │       ├── FY2024-25.yaml
│   │   │       └── FY2025-26.yaml
│   │   └── errors.py           Unified error messages
│   └── tests/
│       ├── conftest.py
│       ├── test_evidence.py
│       ├── test_interview.py
│       ├── test_readiness.py
│       ├── test_review.py
│       ├── test_export.py
│       └── test_skills.py
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── login/
│   │   └── (dashboard)/
│   │       ├── layout.tsx
│   │       ├── readiness/
│   │       ├── journey/
│   │       ├── review/
│   │       ├── evidence/
│   │       ├── export/
│   │       └── settings/
│   ├── components/
│   │   ├── review/
│   │   │   ├── ReviewCard.tsx
│   │   │   ├── InlineQuestion.tsx
│   │   │   └── BulkActionBar.tsx
│   │   ├── evidence/
│   │   │   ├── UploadZone.tsx
│   │   │   ├── DocumentCard.tsx
│   │   │   └── DuplicateModal.tsx
│   │   ├── readiness/
│   │   │   ├── ReadinessRing.tsx
│   │   │   ├── SkillBreakdown.tsx
│   │   │   └── MissingEvidenceList.tsx
│   │   ├── interview/
│   │   │   ├── QuestionCard.tsx
│   │   │   └── ProgressDots.tsx
│   │   └── shared/
│   │       ├── StatusBadge.tsx
│   │       ├── ConfidenceBar.tsx
│   │       └── Disclaimer.tsx
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── documents.ts
│   │   │   ├── events.ts
│   │   │   ├── review.ts
│   │   │   └── export.ts
│   │   ├── stores/
│   │   │   ├── workspace.store.ts
│   │   │   └── interview.store.ts
│   │   └── hooks/
│   │       ├── useSSE.ts
│   │       └── useReadiness.ts
│   └── styles/
│       └── globals.css         All CSS variables from DESIGN.md
│
└── scripts/
    └── seed_dev_data.py        Test data for development
```

---

## 4. Docker Compose

### docker-compose.yml (production)
```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "3060:3000"
    environment:
      - NEXT_PUBLIC_API_URL=https://taxcc-api.signpega.com
    depends_on:
      backend:
        condition: service_healthy

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "8060:8000"
    env_file:
      - .env
    environment:
      - DATABASE_URL=sqlite:////data/db/tax_return.db
      - STORAGE_BACKEND=local
      - STORAGE_PATH=/data/documents
      - ENVIRONMENT=production
    volumes:
      - tax_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  tax_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /home/pi/tax-return-data
```

### docker-compose.dev.yml (development overrides)
```yaml
services:
  frontend:
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next

  backend:
    environment:
      - DATABASE_URL=sqlite:////data/db/tax_return_dev.db
      - ENVIRONMENT=development
      - CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
    volumes:
      - ./backend:/app
      - tax_dev_data:/data
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

volumes:
  tax_dev_data:
```

---

## 5. Environment Variables

### Complete .env.example
```bash
# ── App ────────────────────────────────────────
ENVIRONMENT=development               # development | production
SECRET_KEY=change-me-random-string    # Session signing key

# ── Database ───────────────────────────────────
DATABASE_URL=sqlite:////data/db/tax_return.db
# PostgreSQL: postgresql+asyncpg://user:pass@db:5432/tax

# ── Storage ────────────────────────────────────
STORAGE_BACKEND=local                 # local | s3
STORAGE_PATH=/data/documents
# S3 vars (future):
# S3_BUCKET=
# S3_REGION=
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=

# ── AI ─────────────────────────────────────────
AI_PROVIDER=claude                    # claude | openai | ollama
ANTHROPIC_API_KEY=
AI_TIMEOUT_SECONDS=15
# OPENAI_API_KEY=
# OLLAMA_BASE_URL=http://localhost:11434

# ── Auth ───────────────────────────────────────
APP_PASSWORD_HASH=                    # bcrypt hash, set on first run
SESSION_MAX_AGE_DAYS=7
UNLOCK_SESSION_MINUTES=30

# ── CORS ───────────────────────────────────────
CORS_ORIGINS=https://taxcc.signpega.com,http://127.0.0.1:3060

# ── Frontend (Next.js) ─────────────────────────
NEXT_PUBLIC_API_URL=https://taxcc-api.signpega.com

# ── Features ───────────────────────────────────
MAX_FILE_SIZE_MB=20
EXPORT_RETENTION_HOURS=24
LOG_LEVEL=INFO                        # DEBUG | INFO | WARNING | ERROR
```

---

## 6. Database Schema

### All 11 tables

```python
# Table 1: Workspace
Workspace {
  id, name, financial_year,
  status,                   # active | archived
  created_at, updated_at
}

# Table 2: TaxProfile
TaxProfile {
  id, workspace_id, financial_year,
  employment_type,          # employee | sole_trader | both
  resident_status,          # resident | non_resident | part_year
  user_lodger_type,         # self | agent | unknown
  has_wfh, has_investments, has_crypto, has_property,
  has_private_health, has_sole_trader,
  has_spouse, has_dependents,
  spouse_income_range,      # under_18200 | 18200_48000 | 48000_90000 | over_90000
  dependent_count,
  has_novated_lease,
  spouse_has_novated_lease,
  spouse_rfba_amount,
  active_skills,            # JSON array of skill_ids
  fy_end_reminder_set,
  created_at, updated_at
}

# Table 3: InterviewSession
InterviewSession {
  id, workspace_id, financial_year,
  state,                    # not_started | in_progress | paused |
                            # awaiting_evidence | complete
  current_step,             # JSON {skill_id, question_id}
  completed_steps,          # JSON array
  skipped_steps,            # JSON array of {step, reason, timestamp}
  branch_path,              # JSON array (for back navigation)
  pending_queue,            # JSON array
  answers,                  # JSON dict {question_id: answer}
  activated_skills,         # JSON array
  started_at, last_active_at, completed_at, created_at
}

# Table 4: Document
Document {
  id, workspace_id, financial_year,
  original_filename, storage_key, file_type,
  file_size_bytes, sha256_hash,          # hash used for dedup
  extraction_method,        # pdfplumber | tesseract | csv_parse
  extracted_text,           # sanitized text sent to AI
  extracted_fields,         # JSON {amount, date, merchant}
  extraction_confidence,
  document_type,            # payg_summary | bank_statement | receipt | csv
  skill_id,
  status,                   # processing | ready | failed | archived
  archived, archived_reason,
  uploaded_at, processed_at
}

# Table 5: TaxEvent
TaxEvent {
  id, workspace_id, document_id, financial_year,
  event_type,               # income | deduction | investment | wfh
  category,                 # payg_income | wfh_deduction | ...
  description, amount, currency, date,
  source,                   # document_extracted | manual_entry
  ai_reasoning, confidence,
  risk_level,               # low | medium | high
  status,                   # confirmed | needs_user_review |
                            # needs_agent_review | high_risk |
                            # out_of_scope | duplicate
  review_status,            # pending | user_confirmed | agent_required
  possible_duplicate,
  user_action,              # confirmed | amended | flagged | skipped
  user_note, amended_amount, amended_category,
  skill_id, skill_version,
  group_id, group_display,  # recurring item grouping
  is_recurring, recurrence_index,
  correction_history,       # JSON array
  inline_answers,           # JSON dict
  created_at, reviewed_at
}

# Table 6: ReviewItem
ReviewItem {
  id, workspace_id, tax_event_id,
  title, category, amount, date, skill_id, risk_level,
  ai_reasoning, confidence,
  inline_questions,         # JSON array (B-plan inline questions)
  inline_answers,           # JSON dict
  questions_complete,
  status, user_action, user_note,
  amended_amount, amended_category,
  skipped_until,
  created_at, reviewed_at, review_duration_seconds
}

# Table 7: ReadinessScore
ReadinessScore {
  id, workspace_id, financial_year,
  percentage,
  breakdown,                # JSON per-skill breakdown
  missing_items,            # JSON list
  review_items,             # JSON list
  agent_items,              # JSON list
  is_stale,
  calculated_at
}

# Table 8: ExportRecord
ExportRecord {
  id, workspace_id, financial_year,
  readiness_pct, confirmed_count, review_count,
  agent_count, missing_count, skills_active,
  storage_key, file_size_bytes, expires_at,
  status,                   # generating | ready | expired | failed
  created_at
}

# Table 9: WorkspaceSecurity
WorkspaceSecurity {
  id, workspace_id,
  password_hash,            # bcrypt, never plaintext
  password_encrypted_dek,   # DEK encrypted with password
  recovery_key_hash,        # bcrypt hash of recovery key
  recovery_encrypted_dek,   # DEK encrypted with recovery key
  unlock_session_token,
  unlock_session_expires,
  created_at, updated_at
}

# Table 10: AuditLog
AuditLog {
  id, workspace_id, tax_event_id,
  action,                   # confirmed | amended | flagged | skipped |
                            # document_uploaded | export_generated |
                            # ai_interaction | manual_entry
  actor,                    # user | system | ai
  field, old_value, new_value, note,
  ai_operation,             # classify | explain | ask | risk
  ai_provider, ai_model,
  input_tokens, output_tokens, cost_usd,
  duration_ms, ai_success,
  created_at
}

# Table 11: YoySuggestion
YoySuggestion {
  id, workspace_id,
  source_workspace_id,      # previous FY workspace
  financial_year,
  category, description,
  amount_last_year, frequency,
  status,                   # pending | confirmed | dismissed | not_applicable
  shown_at, actioned_at
}

# Table 12: SkillVersionLock
SkillVersionLock {
  id, workspace_id, skill_id, skill_version,
  locked_at
}

# Table 13: FeatureFlag
FeatureFlag {
  id, workspace_id, feature, enabled, expires_at
}

# Table 14: BackgroundJob
BackgroundJob {
  id, workspace_id,
  job_type,                 # export_generate | readiness_recalc
  status,                   # pending | running | complete | failed
  payload,                  # JSON input
  result,                   # JSON output
  error,
  created_at, started_at, completed_at
}

# Table 15: TaxDeadlineReminder
TaxDeadlineReminder {
  id, workspace_id, financial_year,
  deadline_type,            # self_lodger | tax_agent
  deadline_date,
  reminders,                # JSON [{date, shown}]
}

# Table 16: EncryptedDraft
EncryptedDraft {
  id, workspace_id,
  form_type,                # tax_profile | interview | manual_entry
  encrypted_content,        # AES encrypted JSON
  last_saved_at
}
```

---

## 7. Core Abstractions (Iron Laws)

Claude Code must NEVER violate these:

### AI Layer
```python
# ✅ CORRECT — always go through adapter
from app.ai.base import AIAdapter
result = await ai_adapter.classify(text, fields, profile)

# ❌ FORBIDDEN — never import provider SDK in business logic
import anthropic
client = anthropic.Anthropic()
```

### Storage Layer
```python
# ✅ CORRECT
from app.storage.base import StorageBackend
storage.save(path, data)

# ❌ FORBIDDEN
with open("/data/documents/file.pdf", "wb") as f:
    f.write(data)
```

### Database Layer
```python
# ✅ CORRECT
from app.repositories.documents import DocumentRepository
doc = await doc_repo.find_by_hash(workspace_id, sha256)

# ❌ FORBIDDEN
result = await db.execute(text("SELECT * FROM documents WHERE..."))
```

### Config Layer
```python
# ✅ CORRECT
from app.config import settings
timeout = settings.AI_TIMEOUT_SECONDS

# ❌ FORBIDDEN
timeout = 15  # hardcoded
```

---

## 8. API Design

### Base URL
```
Development:  http://localhost:8000/api/v1
Production:   https://taxcc-api.signpega.com/api/v1
```

### Unified error format
```json
{
  "error_code": "duplicate_document",
  "message": "You've already uploaded this document.",
  "action": "view_existing",
  "retryable": false
}
```

### Never expose in errors
```
Stack traces, SQL errors, file paths,
hashes, model names, internal IDs
```

### Key endpoints
```
POST   /auth/login
POST   /auth/logout
GET    /auth/session

GET    /workspaces
POST   /workspaces
GET    /workspaces/{id}

POST   /documents/upload
GET    /documents/{id}/stream          SSE progress
GET    /documents/{id}/file            Preview
GET    /documents/{id}/summary

GET    /interview/session
POST   /interview/answer
POST   /interview/skip
POST   /interview/back

GET    /readiness
POST   /readiness/recalculate

GET    /review/queue
POST   /review/{item_id}/action
POST   /review/{item_id}/inline-answer
POST   /review/bulk-action

POST   /export/generate
GET    /export/{id}/download
GET    /export/history

GET    /health                         {status, db, storage}
```

### SSE Event Format
```json
{"document_id": "xxx", "status": "processing", "stage": "ocr", "progress": 40}
{"document_id": "xxx", "status": "ready", "events_created": 3}
{"document_id": "xxx", "status": "failed", "error_code": "ocr_failed"}
```

---

## 9. Security Architecture

### Auth Flow
```
Login → verify bcrypt(password) → set httpOnly session cookie (7 days)
Access sensitive data → verify DEK unlock session (30 min, extends on activity)
Two separate sessions: auth ≠ unlock
```

### DEK Architecture
```
User data → encrypted with DEK
DEK → encrypted with password (stored as password_encrypted_dek)
DEK → encrypted with recovery key (stored as recovery_encrypted_dek)

Password reset:
  recovery key → decrypt DEK → re-encrypt with new password → done
  User data never touched, DEK never changes
```

### Recovery Key
```
Format:    XXXX-XXXX-XXXX-XXXX / XXXX-XXXX-XXXX-XXXX (32 hex chars)
Storage:   bcrypt hash only — system cannot recover plaintext
Setup:     Generated on first run, user must confirm last 8 chars before proceeding
Reset:     Recovery key → new password → DEK re-encrypted → data preserved
```

### Draft Autosave
```
Forms autosave to EncryptedDraft table every 10-30 seconds
Content encrypted with DEK before storage
Restored only after successful DEK unlock
Never stored in localStorage
sessionStorage: non-sensitive UI state only (tab position, scroll)
```

### CORS
```python
origins = os.getenv("CORS_ORIGINS", "").split(",")
# Exact match only — never wildcard *
```

---

## 10. Evidence Engine

### Upload Pipeline
```
1. Validate file type (magic bytes) + size (< MAX_FILE_SIZE_MB)
2. Calculate SHA-256 hash
3. Check duplicate → if exists: return {status: "duplicate", existing_id}
4. Save to storage backend (write-once)
5. Create Document record (status: processing)
6. SSE stream opened by frontend
7. Extract text (pdfplumber → tesseract → csv_parse)
8. Sanitize extracted text (remove TFN, BSB, account numbers)
9. AI classification (sanitized text only — never raw file)
10. Skill extracts TaxEvent candidates
11. Dedup TaxEvent candidates against existing events
12. Write TaxEvents (status: needs_user_review)
13. Trigger: readiness recalculate, interview inline question check
14. Document status → ready, SSE closes
```

### OCR Strategy
```
PDF with text layer:  pdfplumber (fast, near 100% accuracy)
Scanned PDF/image:    tesseract (slower, 85-95% accuracy)
CSV file:             direct parse (no OCR)
Fallback:             manual entry prompt
```

### Sanitization Before AI
```python
# Remove before sending to Claude:
TFN:         \b\d{3}-\d{3}-\d{3}\b  → [TFN]
BSB:         \b\d{6}\b              → [BSB]
Account:     \b\d{8,16}\b           → [ACCT]
# Keep: amounts, dates, merchant names, descriptions
```

### Duplicate Document Handling
```
Duplicate detected → reject upload (zero writes)
Return: {status: "duplicate", existing_document_id, redirect: "review_cards"}
UI: show existing document summary, offer "View existing →"
```

### CSV Bank Parser Strategy
```
CommBank:    Built-in parser (column map defined in constants)
ANZ:         Built-in parser
Westpac:     Built-in parser
NAB:         Built-in parser
moomoo AU:   AI auto-detect
CoinSpot:    AI auto-detect
Other:       Generic CSV → user maps columns manually
```

---

## 11. Skill System

### Mixed Mode (YAML + Python)
```
YAML defines:    metadata, activation, questions, evidence requirements,
                 risk rules, explanation templates, category ownership
Python handles:  complex calculations (cost basis, depreciation, GST)
Rule:            if expressible as "condition: X AND Y" → YAML
                 if needs loops/math/external data → Python
```

### Skill Interface (all skills must implement)
```python
class TaxSkill(ABC):
    skill_id:         str
    version:          str
    owned_categories: list[str]

    def should_activate(profile: TaxProfile) -> bool
    def get_questions(profile: TaxProfile) -> list[Question]
    def get_evidence_requirements(profile) -> list[EvidenceRequirement]
    def get_missing_evidence(profile, events) -> list[MissingEvidence]
    def get_review_questions(event: TaxEvent) -> list[ReviewQuestion]
    def get_risk_flags(events) -> list[RiskFlag]
    def explain(event: TaxEvent) -> str
    def extract_events(doc, classification) -> list[EventCandidate]
    def calculate(event) -> CalculationResult | None  # optional
```

### Skill Activation
```
employee_tax_au:   always (base skill for employees)
wfh_skill:         profile.has_wfh = true
investment_skill:  profile.has_investments = true
crypto_skill_au:   profile.has_crypto = true
property_skill:    profile.has_property = true (future)
sole_trader_skill: profile.employment_type in [sole_trader, both] (future)
```

### Category Conflict Resolution
```
If two skills claim same category → flag conflict in SkillRegistry
Log warning, surface in AuditLog
Never silently pick one — require user disambiguation
```

### Skill Version Locking
```
When skill activates for a workspace → create SkillVersionLock record
Historical events always evaluated against locked version
Skill upgrades do not auto-reprocess historical data
User must manually trigger re-analysis if desired
```

---

## 12. Interview Engine

### State Machine
```
not_started → in_progress ↔ paused → awaiting_evidence → complete
```

### Platform Questions (always asked first, in order)
```
Q1: Which financial year are you preparing?
Q2: What is your residency status?
Q3: What best describes your work situation?
Q4: What is your family situation?
  Q4a: (if has_spouse) Spouse income range?
  Q4b: (if has_spouse) Does spouse have novated lease?
    Q4b-i: (if yes) Spouse RFBA amount?
  Q4c: (if has_dependents) Number of dependent children?
Q5: How are you planning to lodge your return?
    → sets user_lodger_type (self | agent | unknown)
Then: Skill questions (employee_tax_au first, then others)
```

### Inline Questions (B-Plan)
```
New document uploaded → check for inline questions → attach to ReviewItem
User answers inline on Review Card (not in separate Interview UI)
All answers written back to session.answers (single source of truth)
Exception: if answer triggers NEW skill activation → show banner → redirect to Interview
```

### Persistence
```
Every answer → immediate DB write (no batching)
Resume: restore from current_step + pending_queue
Back navigation: undo branch insertions and skill activations
```

### Branch Insertion Strategy
```
Answer triggers branch → insert branch questions immediately after current position
(not at end of queue) — maintains conversational context
```

---

## 13. Tax Readiness Engine

### Score Calculation
```
percentage = achieved_weight / total_weight × 100

Weight rules:
  confirmed event:      full weight
  needs_review event:   half weight
  missing:              zero weight

Dynamic denominator:
  FY still active → after_fy_end documents excluded from denominator
  No WFH on profile → WFH evidence excluded from denominator
  Evidence conditions must match active profile flags
```

### Recalculation Triggers
```
document_uploaded, event_status_changed,
interview_answer_saved, profile_updated, skill_activated
All async — non-blocking. is_stale = true while recalculating.
```

### FY-Aware Evidence
```yaml
# In skill.yaml
evidence_requirements:
  - id: payg_summary
    available_after_fy: true
    available_from: july        # myGov, after employer submits
  - id: work_receipt
    available_after_fy: false
    available_from: anytime
```

---

## 14. Review Engine

### Queue Priority Order
```
1. Inline questions incomplete (user must answer first)
2. high_risk items
3. Higher amount first
4. Most recently uploaded first
```

### User Actions
```
confirmed:  event.status = confirmed, review_status = user_confirmed
amended:    record to correction_history, then confirmed
flagged:    event.status = needs_agent_review → agent_required queue
skipped:    skipped_until = now + 1 day, stays in queue
```

### Bulk Actions
```
Bulk confirm only — no bulk amend
Each item logged individually in AuditLog (never merged)
Triggered when N similar items detected (same description, similar amount)
```

### Ask Claude
```
Context sent: event fields, extracted text, profile, FY
Never sent: original file, TFN, bank account numbers
System prompt enforces: always end with compliance disclaimer
AI response stored in AuditLog
```

### Amend Flow
```
Inline edit on Review Card (no separate page)
Category dropdown: only shows current skill's owned_categories
Save → correction_history appended → status = confirmed
```

---

## 15. Export Engine

### Export Eligibility
```
Hard blocks:    interview not complete, no confirmed events,
                documents still processing
Soft warnings:  pending review items, missing required evidence,
                agent-required items (warns but does not block)
```

### Package Structure
```
review-package-{fy}-{workspace_id[:8]}.zip  (AES-256 password)
├── 00-COVER.pdf
├── 01-TAX-EVENTS.json
├── 02-REVIEW-SUMMARY.pdf
├── 03-MISSING-ITEMS.pdf
├── 04-AI-REASONING.json
├── 05-AUDIT-LOG.json
├── 06-SCHEMA-VERSION.txt
├── 07-DISCLAIMER.txt
└── evidence/
    ├── manifest.json
    └── {original uploaded files}
```

### PDF Generation
```
Tool:     WeasyPrint + Jinja2
Template: templates/export/cover.html, summary.html, missing.html
Process:  render HTML → WeasyPrint → PDF bytes → include in zip
```

### Security
```
Password: user-set at export time — never stored by system
Format:   AES-256 via pyzipper
Cleanup:  zip file deleted after EXPORT_RETENTION_HOURS (default 24)
```

---

## 16. AI Adapter

### Provider Interface
```python
class AIProvider(ABC):
    async def complete(system, messages, max_tokens, temperature) -> AIResponse
    async def complete_with_search(system, messages) -> AIResponse
```

### AIAdapter Methods
```
classify()              Document type + skill routing
extract_events()        TaxEvent candidates from document
explain()               Plain-English event explanation
generate_inline_questions()  Review Card follow-up questions
ask()                   User free-form question
assess_risk()           Risk flag evaluation
```

### Reliability
```
Retry:      3 attempts on JSON parse failure
Timeout:    AI_TIMEOUT_SECONDS (default 15)
Fallback:   return low-confidence result, flag needs_user_review
Temperature: 0.1 (low — tax context needs consistency)
```

### Usage Tracking
```
Every AI call → AuditLog entry with:
  operation, provider, model, input_tokens, output_tokens, cost_usd, duration_ms
Visible in Settings → AI & Privacy → "AI Usage This Month"
```

---

## 17. Background Jobs

### Strategy
```
Light tasks (OCR, classification, readiness recalc):
  → FastAPI BackgroundTasks (fire and forget, acceptable if lost on restart)

Heavy tasks (Export generation):
  → BackgroundJob table record first, then BackgroundTasks
  → On startup: check for pending/running jobs → restart them
  → Status visible to frontend via polling GET /export/{id}/status
```

---

## 18. Multi-Year Support

### Workspace per FY
```
Each FY = separate Workspace record
All tables scoped by workspace_id
Switching FY = switching workspace_id in Zustand store
URL: /dashboard/ws_{workspace_id}/readiness
```

### FY Switcher UI
```
Location: sidebar top, below logo
Style: subdued — "FY 2024-25 ▾" — not a prominent control
Expanded: list of workspaces + "New financial year" option
```

### New FY Initialisation
```
Workspace created → copy TaxProfile basics from previous FY
(employment_type, resident_status, family flags)
Do NOT copy: answers, events, documents, interview state
YoY suggestions generated from previous FY confirmed deductions
```

### Deadline Reminders
```
self_lodger:  warn at 30 days, 7 days, 2 days before 31 Oct
              if readiness < 80% at 1 Oct → suggest tax agent
tax_agent:    warn at 30 days before 15 May
Delivery:     login-time banner (no push notifications)
```

---

## 19. Manual Entry

### Guided Form (2-step)
```
Step 1: Select type (Income / Deduction / Investment / WFH / Other)
Step 2: Type-specific fields (category dropdown, description, amount, date)

Recurring:
  Frequency selector → Monthly / Annual / One-off
  If monthly: pricing periods (supports variable pricing like Surfshark)
  Auto-calculates total for FY
```

### Recurring Item Storage
```
Store N individual TaxEvents with shared group_id
Display as one grouped card in Review Queue
Export: expanded to all individual records
Bulk confirm available for grouped items
```

### Attach Receipt to Manual Entry
```
Review Card has [ Attach receipt ] button
Upload → Evidence Engine normal pipeline
No new TaxEvent created — links to existing event via document_id
```

---

## 20. Year-over-Year Suggestions

```
Trigger:      New FY workspace created
Source:       Previous FY confirmed deduction TaxEvents
Filter:       Exclude income, exclude items already in current FY
Display:      Post-interview, max 3 suggestions shown
Actions:      "Yes, still use it" → prefilled manual entry form
              "No longer" → dismissed
              "Already added" → dismissed
```

---

## 21. Tax Figure Summary (Not a Calculator)

```
System provides: taxable income, total deductions, PAYG withheld (from confirmed events)
User copies to:  ATO Income Tax Estimator (external link)
                 https://www.ato.gov.au/calculators-and-tools

Complex crypto:  Koinly / CoinTracker external link recommendation
                 User enters crypto summary figures manually

Never:           Build our own tax calculator
                 Display estimated refund as a precise figure
```

---

## 22. Settings Pages

```
Workspace:   name, FY list, danger zone (archive/delete)
Security:    change password, view/regenerate recovery key, auto-lock timer
AI&Privacy:  provider selector, what we send to AI, usage this month, offline mode
Storage:     usage breakdown, auto-cleanup config, backup guidance
About:       version, active skills, disclaimer, export diagnostic log
```

---

## 23. Onboarding Flow

```
1. Set password (+ strength indicator)
2. Generate recovery key → copy/download → confirm last 8 chars
3. Welcome page (product positioning, "we don't lodge, we don't connect to ATO")
4. Select financial year (current FY highlighted)
5. Interview Engine (Platform Q1-Q5, then Skill questions)
6. Personalised "next steps" list (dynamic, based on profile)
```

---

## 24. Frontend Architecture Rules

```
All API calls:    through /lib/api/ — never fetch() directly in components
Global state:     Zustand stores only
Server state:     React Query (auto-refetch, caching)
SSE:              useSSE hook — EventSource, auto-close on terminal status
Sensitive data:   never in localStorage
UI state only:    sessionStorage (tab, scroll position)
Design tokens:    CSS variables from globals.css — never hardcode colours
Responsive:       mobile-first, all components work at 380px width
Sidebar mobile:   collapses to bottom tab bar
```

---

## 25. Testing Requirements

### Must have tests before Claude Code can mark a module complete
```
Evidence Engine:
  □ valid PDF upload → TaxEvent created
  □ duplicate hash → rejected, zero writes
  □ corrupted file → rejected with correct error
  □ CSV CommBank format → parsed correctly
  □ AI classification failure × 3 → fallback result

Interview Engine:
  □ all 5 state transitions
  □ branch insertion (immediate after current step)
  □ back navigation (undo branches + skill activations)
  □ resume from paused state
  □ new skill activation mid-interview

Readiness Engine:
  □ 0% when no events
  □ 50% for needs_review events (half weight)
  □ 100% only when all required evidence confirmed
  □ after_fy_end documents excluded from denominator during active FY
  □ missing evidence list correct

Review Engine:
  □ queue sort order correct
  □ confirmed action → event status updated
  □ amended action → correction_history appended
  □ flagged → moves to agent queue
  □ bulk confirm → each item individually logged

Skill System:
  □ employee_tax_au activates for employee profile
  □ crypto_skill activates for has_crypto = true
  □ skill conflict detected and logged
  □ skill version locked on activation

Security:
  □ duplicate password → rejected
  □ wrong recovery key → rejected
  □ DEK re-encryption on password reset → data accessible
  □ unlock session expires → sensitive endpoints return 401

AI Adapter:
  □ swap provider → same output schema
  □ timeout → fallback result returned
  □ 3 JSON failures → low-confidence fallback (not exception)
```

---

## 26. Development Workflow

```
New session:
  Read CLAUDE.md + ARCHITECTURE.md
  Confirm understanding before writing any code

Per task:
  Write failing test (RED)
  Write minimum implementation (GREEN)
  Refactor (REFACTOR)
  All tests pass before moving on

Per module:
  Confirm scope with user before starting
  Do not expand scope beyond what was agreed
  Report any ARCHITECTURE.md conflicts before resolving them independently

Never:
  Write code before a failing test exists
  Hardcode values that belong in .env
  Import AI/storage/DB providers directly in business logic
  Create tables or endpoints not in this document without approval
```

---

*Version: 1.0 — May 2026*
*This file is the single source of truth. All conflicts resolved by reading this file.*
*Do not modify without discussing with the project owner first.*
