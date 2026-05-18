# CLAUDE.md — Tax Return AI
# Claude Code must read this file at the start of every session.
# This file defines how Claude Code must behave on this project.
# Last updated: May 2026

---

## 0. First Thing Every Session

Before writing any code, run this checklist:

```
□ Read ARCHITECTURE.md completely
□ Read DESIGN.md (if working on frontend)
□ Confirm understanding to the user in one paragraph
□ Ask: "Which module are we working on today?"
□ Wait for user approval before touching any file
```

If you have not done all five steps, stop and do them now.

---

## 0.1 General Coding Behaviour (always applies)

These principles apply to every task on this project, regardless of milestone.
When Section 0.1 conflicts with later sections, later sections (project-specific) win.

### Think Before Coding

```
Do NOT assume. Do NOT hide confusion. Surface tradeoffs.

Before implementing:
  → State your assumptions explicitly
  → If multiple interpretations exist, present them — don't pick silently
  → If a simpler approach exists, say so and push back
  → If something is unclear, STOP — name what's confusing and ask
  → Never start coding to "figure it out as you go"
```

### Simplicity First

```
Minimum code that solves the problem. Nothing speculative.

  → No features beyond what was asked
  → No abstractions for single-use code
  → No "flexibility" that wasn't requested
  → No error handling for impossible scenarios
  → If you write 200 lines and it could be 50, rewrite it

Ask yourself: "Would a senior engineer say this is overcomplicated?"
If yes → simplify before showing the user.
```

### Surgical Changes

```
Touch only what you must. Clean up only your own mess.

When editing existing code:
  → Don't "improve" adjacent code, comments, or formatting
  → Don't refactor things that aren't broken
  → Match existing style, even if you'd do it differently
  → If you notice unrelated dead code, mention it — don't delete it

When your changes create orphans:
  → Remove imports/variables/functions YOUR changes made unused
  → Don't remove pre-existing dead code unless explicitly asked

Test: every changed line should trace directly to the user's request.
```

### Goal-Driven Execution

```
Define success criteria. Loop until verified.

Transform every task into verifiable goals before starting:
  "Add upload validation"
    → "Write tests for invalid file type, oversized file, corrupted file.
       Then make them pass."

  "Fix the duplicate detection bug"
    → "Write a test that reproduces the bug. Then make it pass."

For multi-step tasks, state a brief plan first:
  1. [Step] → verify: [how to check]
  2. [Step] → verify: [how to check]
  3. [Step] → verify: [how to check]

Wait for user approval of the plan before executing.
Weak criteria ("make it work") → ask for clarification before starting.
```

---

## 1. Project Context

**Product:** AI-guided Australian tax preparation workspace
**Stack:** FastAPI (backend) + Next.js 14 (frontend) + SQLite + Docker Compose
**Deployment:** Raspberry Pi — Ubuntu Server CLI-only via Docker Compose
**Design system:** DESIGN.md (all colours, fonts, spacing)
**Architecture:** ARCHITECTURE.md (all design decisions)

**Core rule:** This tool organises tax documents. It never lodges returns,
never connects to ATO, never gives final tax advice.

---

## 2. Iron Laws (never violate under any circumstance)

### 2.1 Layer isolation

```python
# ✅ AI calls — always through adapter
from app.ai.base import AIAdapter

# ❌ FORBIDDEN — never in business logic
import anthropic
import openai

# ✅ Storage — always through backend
from app.storage.base import StorageBackend

# ❌ FORBIDDEN
open("/data/documents/file.pdf", "wb")
import boto3

# ✅ Database — always through repositories
from app.repositories.documents import DocumentRepository

# ❌ FORBIDDEN
await db.execute(text("SELECT * FROM documents WHERE ..."))

# ✅ Config — always from settings
from app.config import settings
timeout = settings.AI_TIMEOUT_SECONDS

# ❌ FORBIDDEN
timeout = 15
api_url = "http://localhost:8000"
```

### 2.2 Tax compliance language

```
❌ NEVER write these words in any UI string, comment, or prompt:
   "deductible" / "ATO-approved" / "ready to lodge"
   "guaranteed" / "final refund" / "AI tax agent"
   "automatic ATO submission" / "submission-ready"

✅ ALWAYS use:
   "candidate deduction" / "possibly deductible"
   "needs review" / "tax-ready evidence package"
   "pre-tax-agent preparation" / "supporting evidence"
```

### 2.3 Test-driven development

```
Every feature follows this exact order:
  1. Write failing test (RED) — commit or show user
  2. Write minimum implementation (GREEN)
  3. Refactor if needed
  4. All tests pass before moving to next task

NEVER write implementation before a failing test exists.
If user asks to skip tests, explain why TDD matters here and proceed with tests.
```

### 2.4 No hardcoding

```
NEVER hardcode:
  Port numbers          → use settings / env vars
  API URLs              → NEXT_PUBLIC_API_URL env var
  File paths            → STORAGE_PATH env var
  Database URLs         → DATABASE_URL env var
  API keys              → ANTHROPIC_API_KEY env var
  Tax rates / thresholds → app/constants/fy_rules/FY{year}.yaml
  Tax categories         → app/constants/categories.py
  Financial year strings → from workspace.financial_year
```

### 2.5 Scope discipline

```
Only build what is in the current milestone agreed with the user.
If you think something else is needed:
  → Tell the user
  → Wait for approval
  → Never self-expand scope

If ARCHITECTURE.md does not cover a situation:
  → Stop
  → Tell the user: "ARCHITECTURE.md does not define this — how should we proceed?"
  → Never invent architecture decisions independently
```

---

## 3. Docker-First Workflow

All commands run inside Docker containers. Never suggest running
npm, pip, python, or alembic directly on the host machine.

```bash
# ✅ CORRECT — always via make or docker compose exec
make test
make migrate-dev
make shell-be
docker compose exec backend pytest tests/ -v

# ❌ FORBIDDEN — never on host directly
pip install xxx
npm install
python script.py
alembic upgrade head
```

When writing instructions for the user, always use Makefile commands.
Refer to the Makefile for the full list of available commands.

---

## 4. File Structure Rules

```
New backend files go in:
  app/engines/        → business logic engines
  app/repositories/   → all database access
  app/api/routes/     → FastAPI route handlers
  app/ai/providers/   → new AI provider implementations
  app/storage/        → new storage backend implementations
  app/skills/         → new Tax Skills
  app/constants/      → tax categories, risk rules, FY configs
  tests/              → all test files

New frontend files go in:
  app/(dashboard)/    → new pages
  components/         → reusable components
  lib/api/            → API call functions
  lib/stores/         → Zustand stores
  lib/hooks/          → custom React hooks

NEVER create files outside these locations without user approval.
NEVER put business logic in route handlers (app/api/routes/).
NEVER put database queries outside app/repositories/.
```

---

## 5. Database Rules

```
Every schema change requires an Alembic migration.
NEVER modify the database directly (no raw SQL outside repositories).
NEVER use SQLite-specific syntax (must stay PostgreSQL-compatible).
NEVER drop a column or table without explicit user approval.
ALWAYS add indexes for foreign keys and high-frequency query fields.

Migration workflow:
  1. Update model in app/db/models.py
  2. make migration MSG="describe the change"
  3. Review generated migration file
  4. make migrate-dev
  5. Run tests to confirm
```

---

## 6. API Rules

```
All endpoints return consistent JSON:

Success:
  {"data": {...}, "status": "ok"}

Error:
  {
    "error_code": "snake_case_code",
    "message": "User-friendly message",
    "action": "suggested_action or null",
    "retryable": true/false
  }

NEVER expose in error responses:
  Stack traces, SQL errors, file paths,
  hashes, model names, internal IDs, environment names

All routes require auth dependency except:
  POST /auth/login
  GET  /health

SSE endpoints must include headers:
  Cache-Control: no-cache
  X-Accel-Buffering: no
```

---

## 7. Frontend Rules

```
State management:
  Global state     → Zustand stores only
  Server state     → React Query (useQuery, useMutation)
  UI-only state    → useState (local to component)

API calls:
  Always through lib/api/ functions
  Never fetch() or axios directly in components

Storage:
  NEVER localStorage (any data — sensitive or not)
  sessionStorage → non-sensitive UI state only
                   (active tab, scroll position, open panels)
  Sensitive drafts → backend EncryptedDraft table via API

Styling:
  CSS variables from globals.css for all colours and tokens
  Tailwind core utilities only (no arbitrary values like w-[347px])
  NEVER hardcode hex colours in components
  All components responsive (mobile-first, works at 380px)
  Sidebar collapses to bottom tab bar on mobile

TypeScript:
  Strict mode — no any types without explicit comment explaining why
  All API response types defined in lib/api/types.ts

Components:
  Always include loading state
  Always include error state
  Always include empty state
  Disclaimer component required on every AI output surface
```

---

## 8. Security Rules

```
Passwords:
  NEVER store plaintext passwords
  Always bcrypt with cost factor >= 12

Session cookies:
  httpOnly: true
  secure: true
  sameSite: "strict"

DEK (Data Encryption Key):
  NEVER log or expose the DEK
  NEVER store DEK in plaintext
  Always use password_encrypted_dek or recovery_encrypted_dek

Sanitization before AI:
  Always call sanitize_for_ai() before sending text to any AI provider
  Removes: TFN, BSB, account numbers, names (where possible)

File uploads:
  Validate magic bytes (not just file extension)
  Enforce MAX_FILE_SIZE_MB from settings
  SHA-256 hash before any write operation
  Write-once: original files never modified after upload
```

---

## 9. Skill Development Rules

```
Every new Skill must have:
  □ skills/{skill_id}/skill.yaml    (metadata, questions, evidence, risk rules)
  □ skills/{skill_id}/__init__.py   (implements TaxSkill ABC)
  □ tests/test_skills.py entry      (activation, missing evidence, risk flags, explain)

A Skill must declare:
  □ owned_categories (no overlap with other active Skills without conflict handling)
  □ activation conditions (which TaxProfile flags trigger it)
  □ evidence requirements with available_after_fy flag
  □ risk rules in YAML (simple conditions)
  □ Python modules only for: cost basis, depreciation, complex date math

Adding a new Skill must NOT break employee_tax_au tests.
Run full test suite after every new Skill addition.
```

---

## 10. Tax Rules

```
Tax categories, risk rules, and FY thresholds:
  NEVER hardcode in Python or TypeScript
  Always read from:
    app/constants/categories.py
    app/constants/fy_rules/FY{year}.yaml

Financial year boundary:
  Australian FY = 1 July – 30 June
  Always validate event dates fall within workspace.financial_year
  Dates outside FY → risk_level = medium, flag in review queue

If a tax rule, rate, or threshold is not in the constants files:
  → Do NOT invent it
  → Tell the user: "This rule is not in our constants. Should I add it?"

Classification is always conservative:
  When uncertain → needs_user_review (never auto-confirm)
  When risky     → needs_agent_review
  When complex   → out_of_scope, flag for specialist
```

---

## 11. Commit and Code Quality

```
Commit format:
  feat:     new feature
  fix:      bug fix
  test:     adding or fixing tests
  refactor: code change without behaviour change
  docs:     documentation only
  chore:    build, deps, config

Examples:
  feat: add SHA-256 duplicate detection to Evidence Engine
  fix: correct Readiness score denominator for active FY
  test: add Interview Engine back-navigation tests

Before marking any task complete:
  □ All tests pass (make test)
  □ No hardcoded values
  □ No imports violating layer isolation
  □ Frontend components have loading/error/empty states
  □ New DB tables have Alembic migration
  □ User-facing strings follow compliance language rules
```

---

## 12. Communication Rules

```
When starting a task:
  → Summarise what you will build (scope)
  → List the files you will create or modify
  → Wait for user confirmation before starting

When finishing a task:
  → List what was created/modified
  → Show test results
  → State if anything was deferred or needs follow-up
  → Ask: "Ready to move to the next task?"

When encountering a problem:
  → Describe the problem clearly
  → Give 2-3 options with trade-offs
  → Make a recommendation
  → Wait for user decision

When something is not in ARCHITECTURE.md:
  → Do NOT decide independently
  → Say: "This is not covered in ARCHITECTURE.md.
          Here are the options: [A] [B]. I recommend [X] because [reason].
          How would you like to proceed?"

Never:
  → Silently make architectural decisions
  → Expand scope without approval
  → Skip tests and promise to add them later
  → Use placeholder code ("TODO: implement this")
     unless explicitly asked by user
```

---

## 13. Milestone Structure

Work through milestones in order. Do not start the next milestone
until the current one is complete and approved by the user.

```
M1:  Project scaffold + Docker Compose + DB Schema + Health Check
M2:  Security layer (password, session, recovery key, DEK)
M3:  Evidence Engine (upload, OCR, dedup, storage)
M4:  AI Adapter (provider abstraction, classify, explain)
M5:  Skill system (base + employee_tax_au)
M6:  Interview Engine (state machine, questions, persistence)
M7:  Tax Readiness Engine (score, missing evidence, FY-aware)
M8:  Review Engine (queue, inline questions, actions)
M9:  Export Engine (WeasyPrint, encryption, download)
M10: Frontend (Next.js, core pages, components)
M11: Integration testing (end-to-end flow)
```

At the start of each milestone, say:
"Starting M{N}: {name}. Here is what I will build: ..."

---

## 14. Quick Reference

```
Start dev:           make dev
Run tests:           make test
Run single test:     make test-file FILE=tests/test_evidence.py
Open backend shell:  make shell-be
Run migration:       make migrate-dev
New migration:       make migration MSG="describe change"
Check health:        make health
View logs:           make dev-logs
Deploy to Pi:        make pi-deploy
```

---

*This file is mandatory reading at the start of every Claude Code session.*
*If instructions here conflict with ARCHITECTURE.md, ARCHITECTURE.md wins.*
*If instructions here conflict with user's direct request, ask the user.*
