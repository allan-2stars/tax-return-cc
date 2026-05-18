# Tax Return AI — DESIGN.md
# Complete Design System for an AI-guided Australian Tax Preparation Workspace
# Format: Stitch DESIGN.md (9 sections) + Product Architecture Extensions

---

## Section 1 — Design Identity

### Product Name
Tax Return AI

### One-line Description
An AI-guided tax preparation workspace for Australian individual taxpayers.

### Design Direction
Calm editorial. Warm off-white canvas. Sage green confidence indicators.
Muted amber for review-required states. Never alarming, never clinical.

### Personality
Calm, guided, trustworthy, non-accounting, non-enterprise, low-anxiety.
The product feels like a knowledgeable friend walking you through your tax year —
not a government portal, not an accountant's ERP.

### Anti-patterns (never do these)
- Admin dashboard chrome
- Raw technical language (no "OCR", "hash", "classification failed")
- Alarming red states for normal review items
- Enterprise CRUD table patterns
- Progress meters that feel like loading bars
- Any language that implies final tax advice or ATO approval

---

## Section 2 — Color Tokens

### Light Mode (primary)

```
--color-canvas:        #F7F5F0   /* warm off-white — main background */
--color-surface:       #FFFFFF   /* card surfaces */
--color-surface-raised:#FAFAF8   /* elevated cards, modals */
--color-border:        #E8E4DC   /* subtle dividers */
--color-border-strong: #D4CFC5   /* section separators */

--color-text-primary:  #1A1916   /* near-black — headings */
--color-text-body:     #3D3A35   /* body text */
--color-text-muted:    #7A7570   /* captions, labels */
--color-text-faint:    #ABA7A0   /* placeholders, disabled */

--color-accent:        #C17B4A   /* warm terracotta — primary CTA, active nav */
--color-accent-hover:  #A8673A   /* darker terracotta on hover */
--color-accent-soft:   #F2E8DF   /* terracotta tinted background */

--color-ready:         #4A7C6F   /* sage green — confirmed, complete */
--color-ready-bg:      #EBF3F1   /* sage green tint */
--color-review:        #C89B3C   /* muted amber — needs user review */
--color-review-bg:     #FBF4E5   /* amber tint */
--color-agent:         #7B5EA7   /* muted purple — needs tax agent */
--color-agent-bg:      #F3EEFB   /* purple tint */
--color-risk-high:     #B05A3C   /* terracotta-red — high risk flag */
--color-risk-bg:       #FCEEE9   /* risk tint */

--color-progress-track:#E8E4DC
--color-progress-fill: #4A7C6F
```

### Dark Mode

```
--color-canvas:        #1A1916
--color-surface:       #242220
--color-surface-raised:#2C2A27
--color-border:        #3A3733
--color-border-strong: #4A4740

--color-text-primary:  #F0EDE8
--color-text-body:     #C8C4BC
--color-text-muted:    #857F78
--color-text-faint:    #55514C

--color-accent:        #D4895A
--color-accent-hover:  #E09A6A
--color-accent-soft:   #2E2420

--color-ready:         #5A9B8C
--color-ready-bg:      #1A2E2B
--color-review:        #D4A84A
--color-review-bg:     #2A2415
--color-agent:         #9B7EC8
--color-agent-bg:      #221B30
--color-risk-high:     #CC6B4A
--color-risk-bg:       #2A1A15
```

---

## Section 3 — Typography

### Font Stack

```
--font-display:   'Lora', Georgia, serif          /* headings — warm editorial */
--font-body:      'Source Serif 4', Georgia, serif /* body — readable, human */
--font-ui:        'DM Sans', system-ui, sans-serif /* labels, buttons, nav */
--font-mono:      'JetBrains Mono', monospace      /* tax amounts, dates, IDs */
```

### Type Scale

```
--text-xs:    0.75rem  / 1.0rem   /* 12px — fine print, badges */
--text-sm:    0.875rem / 1.25rem  /* 14px — captions, meta */
--text-base:  1rem     / 1.6rem   /* 16px — body text */
--text-lg:    1.125rem / 1.6rem   /* 18px — lead paragraphs */
--text-xl:    1.25rem  / 1.4rem   /* 20px — section titles */
--text-2xl:   1.5rem   / 1.3rem   /* 24px — page headings */
--text-3xl:   2rem     / 1.2rem   /* 32px — hero headings */
--text-4xl:   2.5rem   / 1.1rem   /* 40px — splash only */
```

### Weight Usage

```
font-weight: 400   /* body, descriptions */
font-weight: 500   /* UI labels, nav items */
font-weight: 600   /* section headings, card titles */
font-weight: 700   /* readiness %, critical highlights */
```

---

## Section 4 — Spacing & Layout

```
--space-1:    4px
--space-2:    8px
--space-3:    12px
--space-4:    16px
--space-5:    20px
--space-6:    24px
--space-8:    32px
--space-10:   40px
--space-12:   48px
--space-16:   64px
--space-20:   80px

--radius-sm:  6px    /* inputs, tags */
--radius-md:  10px   /* cards, panels */
--radius-lg:  16px   /* modals, drawers */
--radius-xl:  24px   /* hero cards */
--radius-full: 9999px /* pills, badges */

--shadow-sm:   0 1px 3px rgba(26,25,22,0.06)
--shadow-md:   0 4px 12px rgba(26,25,22,0.08)
--shadow-lg:   0 8px 32px rgba(26,25,22,0.12)
--shadow-focus:0 0 0 3px rgba(193,123,74,0.25)
```

### Layout Grid

```
Main layout:   sidebar (240px fixed) + content (flex-grow)
Content max-width: 880px (centered)
Card gutter:   24px
Section gap:   48px
Mobile:        single column, sidebar collapses to bottom tab bar
```

---

## Section 5 — Component Patterns

### Tax Readiness Card (hero component)

```
Visual: large circular progress ring (sage green)
Shows:
  - Readiness % (large, --font-mono, --color-ready)
  - "X items need your review" (--color-review)
  - "Y items need a tax agent" (--color-agent)
  - "Z pieces of evidence still missing" (--color-text-muted)
  - CTA: "Continue your tax journey →" (--color-accent button)

Tone: progress-first, never alarming
Example: "72% ready · 3 items to review · 2 items missing"
```

### Status Badge

```
States → label → color token:
  confirmed         "Ready"           --color-ready
  needs_user_review "Needs your look" --color-review
  needs_agent_review"Agent review"    --color-agent
  high_risk         "Flag to review"  --color-risk-high
  out_of_scope      "Specialist area" --color-agent
  missing           "Still needed"    --color-text-muted
  duplicate         "Possible duplicate" --color-review

Style: pill shape, 12px font, soft background fill, no harsh borders
```

### Confidence Indicator

```
0.90-1.00  ███████████  "High confidence"   --color-ready
0.70-0.89  ████████░░░  "Moderate"          --color-text-muted
0.50-0.69  █████░░░░░░  "Uncertain"         --color-review
< 0.50     ██░░░░░░░░░  "Needs review"      --color-agent

Never show raw numbers to users. Always humanise.
"Claude is moderately confident about this item"
```

### Guided Interview Card

```
Style: one question per screen, conversational
Layout: question (--text-xl, --font-display) + contextual hint text
         + 2-4 response options (large tap targets, 56px min-height)
         + optional "Why do we ask?" expandable tooltip

Example question:
  "Did you work from home during the 2024–25 financial year?"
  Options: "Yes, regularly" | "Sometimes" | "No" | "Not sure"

Progress: dot indicator at top (not percentage)
Back link: top-left, always visible
Skip: available for optional questions ("Skip for now →")
```

### Evidence Upload Zone

```
Visual: dashed border card, --color-border-strong
States:
  idle:      "Drop your document here, or browse"
  hover:     border becomes --color-accent, slight scale
  uploading: progress bar, filename shown
  success:   check icon (--color-ready), filename, "Remove" link
  error:     "We couldn't read this file. Try a clearer photo."

Never show: "OCR failed", "extraction error", "hash mismatch"
```

### Review Draft Card

```
Layout: card with left border strip (color = status)
Shows:
  - Document type + amount + date (--font-mono for amount/date)
  - AI reasoning: "This looks like a work-related subscription" (italic)
  - Confidence bar
  - Action buttons: "Looks right" | "Change this" | "Ask Claude"
  - Expandable: "Why did Claude suggest this?" section

Edit flow: inline — never a separate page
Confirmation: "Thanks for reviewing. We've noted your input." (no toast pop)
```

### Household Timeline

```
Visual: vertical timeline (left-rail line, --color-border)
Events: dot markers colored by category
  - Employment (--color-accent)
  - Investment (--color-agent)
  - WFH period (--color-ready)
  - Missing window (dashed, --color-review)
Interaction: click event → side drawer with detail + evidence
```

### Explain This Report

```
Trigger: "Explain this →" link on any AI-generated item
Style: side drawer, not modal
Content:
  - Plain-English summary (--font-body, --text-base)
  - What we found
  - What we're not sure about
  - What you should tell your tax agent
  - Source documents referenced (listed, not linked inline)
Disclaimer: persistent at bottom (see Section 9)
```

### Security Lock State

```
Language:
  locked:    "Workspace locked"
  unlocking: "Unlocking your workspace…"
  locked_export: "Encrypted review pack"
  unlock_prompt: "Unlock to view sensitive tax data"

Never show: hashes, encryption algorithm names, key IDs
Visual: padlock icon (--color-text-muted when locked, --color-ready when open)
```

---

## Section 6 — Navigation

### Primary Navigation Items

```
Icon + Label — ordered as:

  🏠  Tax Journey         (entry point, guided interview hub)
  📊  Tax Readiness       (readiness % dashboard)
  🔍  Missing Evidence    (items still needed)
  💼  Income              (PAYG, interest, dividends)
  ✂️  Deductions          (candidate deductions)
  📈  Investments         (ETF, shares, crypto)
  🏠  Property            (rental — future skill)
  📁  Supporting Evidence (uploaded documents)
  ✅  Review              (human review queue)
  📦  Export Review Pack  (generate export)
  👨‍👩‍👧  Household           (family tax events)
  ⚙️  Settings
```

### Active State

```
Active nav item: --color-accent left border (3px), --color-accent-soft background
Hover: --color-accent-soft background, no border
Font: --font-ui, weight 500
```

### Mobile Navigation

```
Bottom tab bar: 5 primary items (Tax Journey, Readiness, Review, Evidence, More)
"More" expands to sheet with remaining items
Safe area insets respected
```

---

## Section 7 — Content & Tone

### Core Tone Rules

```
ALWAYS say:              NEVER say:
"Needs your review"      "Error" / "Invalid"
"Possibly deductible"    "Deductible" (without qualifier)
"You may still need…"    "Classification failed"
"Claude isn't certain"   "ATO-approved"
"Candidate deduction"    "Guaranteed deduction"
"Supporting evidence"    "OCR extracted"
"Review package"         "Final return"
"Workspace locked"       "Encryption key required"
"Needs a tax agent"      "Out of scope error"
```

### Status → Human Message Mapping

```
Status                     UI Message
confirmed                  "Looks good — ready for review"
needs_user_review          "We'd like your input on this"
needs_tax_agent_review     "A tax agent should look at this"
low_confidence             "Claude isn't certain — worth checking"
duplicate_document         "This might be a duplicate — can you confirm?"
out_of_scope               "This may need a specialist — we've flagged it"
date_outside_fy            "The date seems outside this financial year"
missing_evidence           "We still need a document to support this"
high_risk                  "This item has a few things to check"
```

### AI Explanation Style

```
Pattern: "This looks like [category] because [plain-English reason].
          We're [confidence word] about this.
          [Optional: You might want to check that…]"

Confidence words:
  0.90+  "fairly confident"
  0.70+  "moderately confident"
  0.50+  "not certain"
  < 0.50 "unsure — this needs your review"

Example:
  "This looks like a work-related subscription because it's a recurring
   charge from Adobe, and you've told us you use design software for work.
   We're fairly confident about this. You might want to check whether
   your employer reimbursed any of this cost."
```

---

## Section 8 — Data Architecture

### Core Model: Tax Event

The fundamental unit is a **Tax Event**, not a document.
Documents are evidence that support Tax Events.

```json
TaxEvent {
  id:              uuid
  financial_year:  "2024-25"
  event_type:      income | deduction | investment | wfh | other
  category:        string  // from classification taxonomy
  description:     string  // human-readable
  amount:          decimal
  currency:        "AUD"
  date:            date
  status:          confirmed | needs_user_review | needs_agent_review |
                   high_risk | out_of_scope | duplicate
  confidence:      0.0-1.0
  risk_level:      low | medium | high
  evidence_ids:    uuid[]  // linked documents
  review_status:   pending | user_confirmed | agent_required
  ai_reasoning:    string
  correction_history: CorrectionEntry[]
  audit:           AuditEntry[]
  skill_source:    string  // which Skill generated this
  schema_version:  string
}
```

### Tax Profile

```json
TaxProfile {
  id:              uuid
  financial_year:  string
  employment_type: employee | sole_trader | both
  has_wfh:         boolean
  has_investments: boolean
  has_crypto:      boolean
  has_property:    boolean
  has_private_health: boolean
  family_status:   single | partnered | family
  active_skills:   string[]  // skill IDs active for this profile
  interview_state: InterviewState
  created_at:      timestamp
  updated_at:      timestamp
}
```

### Guided Interview State Machine

```
States:
  not_started
  in_progress (current_step, completed_steps[], branch_path)
  paused      (resumable)
  complete

Entry point: Tax Profile creation
Branches activated by answers:
  "worked from home?" → activates wfh_skill interview branch
  "bought/sold shares?" → activates investment_skill branch
  "crypto activity?" → activates crypto_skill branch
  "rental income?" → activates property_skill branch (future)
  "ABN income?" → activates sole_trader_skill branch (future)

Resume: always resumable mid-interview (state persisted to DB)
Skip: any non-required question skippable with reason logged
```

### Skill Activation Logic

```
Skill              Activates when TaxProfile has:
employee_tax       employment_type = employee (always base skill)
wfh_skill          has_wfh = true
investment_skill   has_investments = true
crypto_skill       has_crypto = true
property_skill     has_property = true (future)
sole_trader_skill  employment_type = sole_trader | both (future)

Conflict resolution:
  If sole_trader active → income items require human disambiguation
  If property active → CGT events require specialist flag
  Skills run independently; shared evidence pool
```

### Export Package Structure

```
review-package-{fy}-{workspace-id}.zip
├── SUMMARY.pdf              // human-readable cover page
├── TAX_EVENTS.json          // all confirmed + review events
├── EVIDENCE/
│   ├── doc-{id}-{name}.pdf  // original uploaded documents
│   └── manifest.json        // filename → event_id mapping
├── REVIEW_QUEUE.json        // items still needing action
├── AI_REASONING.json        // all AI reasoning summaries
├── AUDIT_LOG.json           // full correction and review history
├── SCHEMA_VERSION.txt       // schema version for agent tools
└── DISCLAIMER.txt           // compliance statement

Encryption: AES-256 password at zip level
Password: user-set at export time, never stored
UI label: "Encrypted review pack"
```

### Multi-Edition Config

```
Edition     DB              Storage         AI Adapter
local       SQLite          local disk      claude-sonnet (env key)
self-hosted PostgreSQL       S3-compatible   configurable provider
saas        PostgreSQL (RLS) S3 + CDN        multi-tenant, managed

Switch via: DATABASE_URL + STORAGE_BACKEND + AI_PROVIDER env vars
No code changes required between editions.
```

---

## Section 9 — Compliance & Disclaimer

### Persistent Disclaimer (required on every AI output surface)

```
"This tool helps organise your tax information and prepare a review package.
 It does not provide final tax advice and does not replace review by you
 or a registered tax agent."
```

### Display Rules

```
- Show on: Review tab, Export screen, any AI explanation drawer
- Position: bottom of content area, not a banner (non-intrusive)
- Style: --text-sm, --color-text-muted, no border, subtle separator above
- Never auto-dismiss, never hide behind a toggle
```

### Prohibited Labels (never use in UI copy, marketing, or code comments)

```
✗  AI tax agent
✗  ATO-approved
✗  Ready to lodge
✗  Guaranteed deduction
✗  Automatic ATO submission
✗  Final refund estimate
✗  Submission-ready
```

### Safe Positioning Labels

```
✓  Tax document organiser
✓  Tax-ready evidence package generator
✓  Deduction review assistant
✓  Pre-tax-agent preparation tool
✓  AI-guided tax preparation workspace
```

---

## Development Priorities (ordered)

```
1. Tax Profile Engine          — profile creation, skill activation
2. Guided Interview Engine     — state machine, branching, resume
3. Tax Skill System            — employee_tax (base), then expand
4. Evidence Completeness Engine — missing evidence detection
5. Human Explanation Layer     — "Explain this" drawer
6. Tax Readiness Dashboard     — readiness %, progress surface
7. Estimate Engine             — rough tax estimate (clearly labelled)

Do NOT invest in:
  - OCR perfection beyond "good enough"
  - Endless AI provider swap abstraction
  - Admin/superuser management screens
  - Cosmetic polish before core flows work
```

---

## Skill Extension Protocol

To add a new Skill (e.g., `rental_property_skill`):

```
1. Create skills/property_skill.md with:
   - Scope (what it covers)
   - Interview goals (what questions to ask)
   - Evidence guidance (what docs to request)
   - AI responsibilities
   - AI must NOT list

2. Add activation condition to TaxProfile (e.g., has_property: true)

3. Add interview branch to Guided Interview state machine

4. Register new tax_event categories in app/constants/

5. Add test cases:
   - rental income with agent fees
   - repairs vs improvements split
   - CGT property event (flag to specialist)

6. Update Tax Readiness Engine to check new evidence types

Skills must remain isolated. Employee flows must never break
when a new Skill is added.
```

---

*End of DESIGN.md*
*Version: 1.0 — May 2026*
*This file is the source of truth for UI generation, architecture decisions, and product tone.*
*Feed to Claude Code, Claude Design, or any coding agent to scaffold consistent output.*
