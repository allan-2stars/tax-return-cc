# M10 Phase 3: Tax Journey (Interview) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Tax Journey page — a state-machine-driven interview hub with QuestionCard, ProgressDots, YoYSuggestionCard, and post-completion next steps — fully tested and styled with DESIGN.md tokens.

**Architecture:** The journey page uses React Query (`useQuery`) to fetch session state from `GET /api/v1/interview/session` and `useMutation` for all user actions (start, answer, back, skip). Mutations update the query cache directly via `setQueryData` to avoid re-fetching the full session on every answer. The Zustand `interview.store.ts` holds only `newSkillPending` — a pure UI flag that doesn't belong in the server cache. The backend `Question` dataclass is extended with `required`, `why`, and `hint` fields that flow through `_q_dict` to the frontend.

**Tech Stack:** Next.js 14 App Router, TypeScript strict, Tailwind CSS (CSS-var tokens only, no arbitrary values), React Query v5, Zustand 4, Jest + React Testing Library

---

## Current State

| File | State |
|------|-------|
| `backend/app/skills/base.py` | `Question` missing `required`, `why`, `hint` fields |
| `backend/app/api/routes/interview.py` | `_q_dict` doesn't expose `required`, `why`, `hint` |
| `backend/app/skills/employee_tax_au/__init__.py` | `get_questions` doesn't pass new fields |
| `backend/app/skills/employee_tax_au/skill.yaml` | Questions have no `required`, `why`, `hint` keys |
| `frontend/lib/api/types.ts` | No interview types |
| `frontend/lib/api/interview.ts` | Does not exist |
| `frontend/lib/stores/interview.store.ts` | Stub — only `sessionId` + `setSessionId` |
| `frontend/components/interview/` | Directory does not exist |
| `frontend/app/(dashboard)/journey/page.tsx` | Stub — "Journey — coming soon" |

---

## File Map

**Backend — modify:**
- `backend/app/skills/base.py` — add `required`, `why`, `hint` to `Question` dataclass
- `backend/app/api/routes/interview.py` — update `_q_dict` to expose new fields
- `backend/app/skills/employee_tax_au/__init__.py` — pass new fields in `get_questions`
- `backend/app/skills/employee_tax_au/skill.yaml` — add `required`, `why`, `hint` to questions

**Frontend — create:**
- `frontend/lib/api/interview.ts`
- `frontend/lib/hooks/useInterview.ts`
- `frontend/components/interview/QuestionCard.tsx`
- `frontend/components/interview/ProgressDots.tsx`
- `frontend/components/interview/YoYSuggestionCard.tsx`
- `frontend/__tests__/interview-api.test.ts`
- `frontend/__tests__/interview-store.test.ts`
- `frontend/__tests__/QuestionCard.test.tsx`
- `frontend/__tests__/ProgressDots.test.tsx`
- `frontend/__tests__/YoYSuggestionCard.test.tsx`
- `frontend/__tests__/journey-page.test.tsx`

**Frontend — modify:**
- `frontend/lib/api/types.ts` — add 6 interview/YoY types
- `frontend/lib/stores/interview.store.ts` — real implementation
- `frontend/app/(dashboard)/journey/page.tsx` — real implementation

---

## Task 1: Backend — extend Question + _q_dict

**Files:**
- Modify: `backend/app/skills/base.py`
- Modify: `backend/app/api/routes/interview.py`
- Modify: `backend/app/skills/employee_tax_au/__init__.py`
- Modify: `backend/app/skills/employee_tax_au/skill.yaml`

- [ ] **Step 1.1: Extend Question dataclass**

In `backend/app/skills/base.py`, replace the `Question` dataclass (lines 6–12):

```python
@dataclass
class Question:
    id: str
    ask: str
    type: str                                  # single_choice | multi_choice | text | number
    options: list[str] | None = None
    branches: dict[str, list[str]] | None = None
    trigger: str | None = None
    required: bool = True                      # False → show skip button in UI
    why: str | None = None                     # shown in "Why do we ask?" tooltip
    hint: str | None = None                    # shown as sub-text below question
```

- [ ] **Step 1.2: Update `_q_dict` in interview route**

In `backend/app/api/routes/interview.py`, replace the `_q_dict` function:

```python
def _q_dict(q: Question | None) -> dict | None:
    if q is None:
        return None
    return {
        "id": q.id,
        "ask": q.ask,
        "type": q.type,
        "options": q.options,
        "branches": q.branches,
        "required": q.required,
        "why": q.why,
        "hint": q.hint,
    }
```

- [ ] **Step 1.3: Update `get_questions` in EmployeeTaxAU**

In `backend/app/skills/employee_tax_au/__init__.py`, replace `get_questions`:

```python
def get_questions(self, profile) -> list[Question]:
    return [
        Question(
            id=q["id"],
            ask=q["ask"],
            type=q["type"],
            options=q.get("options"),
            branches=q.get("branches"),
            required=q.get("required", True),
            why=q.get("why"),
            hint=q.get("hint"),
        )
        for q in _YAML.get("questions", [])
    ]
```

- [ ] **Step 1.4: Update skill.yaml questions section**

In `backend/app/skills/employee_tax_au/skill.yaml`, replace the `questions:` block:

```yaml
questions:
  - id: wfh
    ask: "Did you work from home during this financial year?"
    type: single_choice
    options: [yes_regular, yes_sometimes, no]
    required: false
    why: "This helps us determine if you can claim a work-from-home deduction."
    branches:
      yes_regular:   [wfh_method, wfh_days]
      yes_sometimes: [wfh_method]

  - id: wfh_method
    ask: "Which WFH calculation method are you using?"
    type: single_choice
    options: [fixed_rate, actual_cost]
    required: false
    hint: "Fixed rate is 67¢/hour. Actual cost requires receipts."
    why: "The method affects what records you'll need to keep."

  - id: wfh_days
    ask: "How many days per week did you regularly work from home?"
    type: number
    required: false

  - id: has_private_health
    ask: "Do you have private health insurance?"
    type: single_choice
    options: [yes, no]
    required: false
    why: "Private health insurance may affect your Medicare Levy Surcharge."

  - id: has_novated_lease
    ask: "Do you have a novated lease through your employer?"
    type: single_choice
    options: [yes, no]
    required: false
    why: "Novated leases are reported on your PAYG Summary as fringe benefits."

  - id: self_education
    ask: "Did you pay for any work-related courses or training?"
    type: single_choice
    options: [yes, no]
    required: false
    why: "Self-education expenses may be a candidate deduction if the course directly relates to your current employment."
```

- [ ] **Step 1.5: Run backend tests to confirm no regressions**

```bash
make test-file FILE=tests/test_skills.py
make test-file FILE=tests/test_interview.py
```

Expected: all existing tests pass.

- [ ] **Step 1.6: Commit**

```bash
git add backend/app/skills/base.py \
        backend/app/api/routes/interview.py \
        backend/app/skills/employee_tax_au/__init__.py \
        backend/app/skills/employee_tax_au/skill.yaml
git commit -m "feat: extend Question with required/why/hint — expose in interview API"
```

---

## Task 2: API types + lib/api/interview.ts

**Files:**
- Modify: `frontend/lib/api/types.ts`
- Create: `frontend/lib/api/interview.ts`
- Create: `frontend/__tests__/interview-api.test.ts`

- [ ] **Step 2.1: Write the failing test**

Create `frontend/__tests__/interview-api.test.ts`:

```typescript
jest.mock('@/lib/api/client', () => ({
  default: { get: jest.fn(), post: jest.fn() },
}))

import client from '@/lib/api/client'
import {
  getSession, startInterview, answerQuestion,
  goBack, skipQuestion, getYoySuggestions, actOnSuggestion,
} from '@/lib/api/interview'

const mockGet = client.get as jest.Mock
const mockPost = client.post as jest.Mock

beforeEach(() => jest.clearAllMocks())

test('getSession calls GET /api/v1/interview/session', () => {
  mockGet.mockResolvedValue({ data: { data: {} } })
  getSession()
  expect(mockGet).toHaveBeenCalledWith('/api/v1/interview/session')
})

test('startInterview calls POST /api/v1/interview/start', () => {
  mockPost.mockResolvedValue({ data: { data: {} } })
  startInterview()
  expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/start')
})

test('answerQuestion calls POST /api/v1/interview/answer with body', () => {
  mockPost.mockResolvedValue({ data: { data: {} } })
  answerQuestion('q1', 'yes')
  expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/answer', { question_id: 'q1', answer: 'yes' })
})

test('goBack calls POST /api/v1/interview/back', () => {
  mockPost.mockResolvedValue({ data: { data: {} } })
  goBack()
  expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/back')
})

test('skipQuestion calls POST /api/v1/interview/skip with body', () => {
  mockPost.mockResolvedValue({ data: { data: {} } })
  skipQuestion('q1', 'user_skipped')
  expect(mockPost).toHaveBeenCalledWith('/api/v1/interview/skip', { question_id: 'q1', reason: 'user_skipped' })
})

test('getYoySuggestions calls GET /api/v1/yoy/suggestions', () => {
  mockGet.mockResolvedValue({ data: { data: [] } })
  getYoySuggestions()
  expect(mockGet).toHaveBeenCalledWith('/api/v1/yoy/suggestions')
})

test('actOnSuggestion calls POST /api/v1/yoy/{id}/action with body', () => {
  mockPost.mockResolvedValue({ data: { data: {} } })
  actOnSuggestion('sug-1', 'confirmed')
  expect(mockPost).toHaveBeenCalledWith('/api/v1/yoy/sug-1/action', { action: 'confirmed' })
})
```

- [ ] **Step 2.2: Run test to verify it fails**

```bash
docker compose exec frontend npm test -- --testPathPattern="interview-api" --no-coverage
```

Expected: FAIL — `Cannot find module '@/lib/api/interview'`

- [ ] **Step 2.3: Append types to types.ts**

Append to the end of `frontend/lib/api/types.ts`:

```typescript
export type InterviewState = 'not_started' | 'in_progress' | 'paused' | 'awaiting_evidence' | 'complete'

export interface InterviewQuestion {
  id: string
  ask: string
  type: 'single_choice' | 'multi_choice' | 'text' | 'number'
  options: string[] | null
  branches: Record<string, string[]> | null
  required: boolean
  why: string | null
  hint: string | null
}

export interface InterviewProgress {
  completed: number
  total: number
}

export interface InterviewSessionData {
  state: InterviewState
  session_id?: string
  current_question: InterviewQuestion | null
  answers?: Record<string, string>
  activated_skills?: string[]
  progress: InterviewProgress
  resumed?: boolean
}

export interface AnswerResponseData {
  session_id: string
  state: InterviewState
  next_question: InterviewQuestion | null
  activated_skills: string[]
  progress: InterviewProgress
}

export interface YoYSuggestion {
  id: string
  category: string
  description: string
  amount_last_year: number | null
  frequency: string | null
  status: string
}
```

- [ ] **Step 2.4: Create lib/api/interview.ts**

Create `frontend/lib/api/interview.ts`:

```typescript
import client from './client'
import type {
  ApiResponse,
  InterviewSessionData,
  AnswerResponseData,
  InterviewState,
  YoYSuggestion,
} from './types'

export const getSession = () =>
  client.get<ApiResponse<InterviewSessionData>>('/api/v1/interview/session')

export const startInterview = () =>
  client.post<ApiResponse<InterviewSessionData>>('/api/v1/interview/start')

export const answerQuestion = (question_id: string, answer: string) =>
  client.post<ApiResponse<AnswerResponseData>>('/api/v1/interview/answer', { question_id, answer })

export const goBack = () =>
  client.post<ApiResponse<InterviewSessionData>>('/api/v1/interview/back')

export const skipQuestion = (question_id: string, reason: string) =>
  client.post<ApiResponse<AnswerResponseData>>('/api/v1/interview/skip', { question_id, reason })

export const pauseInterview = () =>
  client.post<ApiResponse<{ session_id: string; state: InterviewState }>>('/api/v1/interview/pause')

export const completeInterview = () =>
  client.post<ApiResponse<{ session_id: string; state: InterviewState }>>('/api/v1/interview/complete')

export const getYoySuggestions = () =>
  client.get<ApiResponse<YoYSuggestion[]>>('/api/v1/yoy/suggestions')

export const actOnSuggestion = (id: string, action: string) =>
  client.post<ApiResponse<YoYSuggestion>>(`/api/v1/yoy/${id}/action`, { action })
```

- [ ] **Step 2.5: Run test to verify it passes**

```bash
docker compose exec frontend npm test -- --testPathPattern="interview-api" --no-coverage
```

Expected: PASS (7 tests)

- [ ] **Step 2.6: Commit**

```bash
git add frontend/lib/api/types.ts frontend/lib/api/interview.ts frontend/__tests__/interview-api.test.ts
git commit -m "feat: add interview API types and functions"
```

---

## Task 3: interview.store.ts — real implementation

**Files:**
- Modify: `frontend/lib/stores/interview.store.ts`
- Create: `frontend/__tests__/interview-store.test.ts`

- [ ] **Step 3.1: Write the failing test**

Create `frontend/__tests__/interview-store.test.ts`:

```typescript
import { act, renderHook } from '@testing-library/react'
import useInterviewStore from '@/lib/stores/interview.store'

beforeEach(() => {
  useInterviewStore.setState({ newSkillPending: null })
})

test('newSkillPending starts null', () => {
  const { result } = renderHook(() => useInterviewStore())
  expect(result.current.newSkillPending).toBeNull()
})

test('setNewSkillPending updates skill id', () => {
  const { result } = renderHook(() => useInterviewStore())
  act(() => result.current.setNewSkillPending('wfh_skill'))
  expect(result.current.newSkillPending).toBe('wfh_skill')
})

test('setNewSkillPending can clear to null', () => {
  const { result } = renderHook(() => useInterviewStore())
  act(() => result.current.setNewSkillPending('wfh_skill'))
  act(() => result.current.setNewSkillPending(null))
  expect(result.current.newSkillPending).toBeNull()
})
```

- [ ] **Step 3.2: Run test to verify it fails**

```bash
docker compose exec frontend npm test -- --testPathPattern="interview-store" --no-coverage
```

Expected: FAIL — stub has no `newSkillPending` property

- [ ] **Step 3.3: Replace the stub**

Replace `frontend/lib/stores/interview.store.ts`:

```typescript
import { create } from 'zustand'

interface InterviewStore {
  newSkillPending: string | null
  setNewSkillPending: (skillId: string | null) => void
}

const useInterviewStore = create<InterviewStore>((set) => ({
  newSkillPending: null,
  setNewSkillPending: (skillId) => set({ newSkillPending: skillId }),
}))

export default useInterviewStore
```

- [ ] **Step 3.4: Run test to verify it passes**

```bash
docker compose exec frontend npm test -- --testPathPattern="interview-store" --no-coverage
```

Expected: PASS (3 tests)

- [ ] **Step 3.5: Commit**

```bash
git add frontend/lib/stores/interview.store.ts frontend/__tests__/interview-store.test.ts
git commit -m "feat: implement interview.store — newSkillPending state"
```

---

## Task 4: QuestionCard component

**Files:**
- Create: `frontend/components/interview/QuestionCard.tsx`
- Create: `frontend/__tests__/QuestionCard.test.tsx`

- [ ] **Step 4.1: Write the failing tests**

Create `frontend/__tests__/QuestionCard.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import QuestionCard from '@/components/interview/QuestionCard'
import type { InterviewQuestion } from '@/lib/api/types'

const choiceQ: InterviewQuestion = {
  id: 'wfh',
  ask: 'Did you work from home?',
  type: 'single_choice',
  options: ['yes_regular', 'yes_sometimes', 'no'],
  branches: null,
  required: false,
  why: 'This helps determine your WFH deduction eligibility.',
  hint: null,
}

const requiredQ: InterviewQuestion = {
  id: 'residency',
  ask: 'What is your residency status?',
  type: 'single_choice',
  options: ['resident', 'non_resident'],
  branches: null,
  required: true,
  why: null,
  hint: 'For most Australians, this is "resident".',
}

test('renders question text', () => {
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByText('Did you work from home?')).toBeInTheDocument()
})

test('renders all options as buttons', () => {
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByRole('button', { name: 'yes_regular' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'yes_sometimes' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'no' })).toBeInTheDocument()
})

test('calls onAnswer with question id and selected option', () => {
  const onAnswer = jest.fn()
  render(<QuestionCard question={choiceQ} onAnswer={onAnswer} onBack={jest.fn()} onSkip={jest.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'yes_regular' }))
  expect(onAnswer).toHaveBeenCalledWith('wfh', 'yes_regular')
})

test('back button is always visible and calls onBack', () => {
  const onBack = jest.fn()
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={onBack} onSkip={jest.fn()} />)
  const back = screen.getByRole('button', { name: /back/i })
  expect(back).toBeInTheDocument()
  fireEvent.click(back)
  expect(onBack).toHaveBeenCalled()
})

test('skip button shown for non-required questions', () => {
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByRole('button', { name: /skip/i })).toBeInTheDocument()
})

test('skip button hidden for required questions', () => {
  render(<QuestionCard question={requiredQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.queryByRole('button', { name: /skip/i })).not.toBeInTheDocument()
})

test('hint text shown when present', () => {
  render(<QuestionCard question={requiredQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByText('For most Australians, this is "resident".')).toBeInTheDocument()
})

test('why tooltip hidden initially, shown on toggle', () => {
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.queryByText('This helps determine your WFH deduction eligibility.')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /why do we ask/i }))
  expect(screen.getByText('This helps determine your WFH deduction eligibility.')).toBeInTheDocument()
})

test('why button absent when question.why is null', () => {
  render(<QuestionCard question={requiredQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.queryByRole('button', { name: /why do we ask/i })).not.toBeInTheDocument()
})
```

- [ ] **Step 4.2: Run test to verify it fails**

```bash
docker compose exec frontend npm test -- --testPathPattern="QuestionCard" --no-coverage
```

Expected: FAIL — `Cannot find module '@/components/interview/QuestionCard'`

- [ ] **Step 4.3: Create the component**

Create `frontend/components/interview/QuestionCard.tsx`:

```tsx
'use client'
import { useState } from 'react'
import type { InterviewQuestion } from '@/lib/api/types'

interface Props {
  question: InterviewQuestion
  onAnswer: (questionId: string, answer: string) => void
  onBack: () => void
  onSkip: (questionId: string) => void
  isSubmitting?: boolean
}

export default function QuestionCard({
  question, onAnswer, onBack, onSkip, isSubmitting = false,
}: Props) {
  const [whyOpen, setWhyOpen] = useState(false)

  return (
    <div className="space-y-6">
      <button
        type="button"
        onClick={onBack}
        disabled={isSubmitting}
        aria-label="Back"
        className="text-sm font-ui text-text-muted hover:text-text-body transition-colors disabled:opacity-50"
      >
        ← Back
      </button>

      <div className="space-y-2">
        <h2 className="font-display text-xl text-text-primary">{question.ask}</h2>
        {question.hint && (
          <p className="text-sm font-body text-text-muted">{question.hint}</p>
        )}
      </div>

      {question.options && (
        <ul className="space-y-3">
          {question.options.map((opt) => (
            <li key={opt}>
              <button
                type="button"
                onClick={() => onAnswer(question.id, opt)}
                disabled={isSubmitting}
                className="w-full py-4 px-4 text-left rounded-md bg-surface border border-border hover:border-accent text-text-body font-ui transition-colors disabled:opacity-50"
              >
                {opt}
              </button>
            </li>
          ))}
        </ul>
      )}

      {(question.type === 'text' || question.type === 'number') && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            const val = (new FormData(e.currentTarget).get('answer') as string) ?? ''
            if (val.trim()) onAnswer(question.id, val.trim())
          }}
          className="space-y-3"
        >
          <input
            name="answer"
            type={question.type === 'number' ? 'number' : 'text'}
            required
            disabled={isSubmitting}
            className="w-full py-3 px-4 rounded-md bg-surface border border-border focus:border-accent focus:outline-none text-text-body font-ui"
          />
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-3 rounded-md bg-accent text-surface font-ui font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            Continue
          </button>
        </form>
      )}

      <div className="flex items-start justify-between gap-4">
        <div>
          {question.why && (
            <div className="space-y-1">
              <button
                type="button"
                onClick={() => setWhyOpen((v) => !v)}
                aria-label="Why do we ask?"
                className="text-xs font-ui text-text-faint hover:text-text-muted transition-colors"
              >
                Why do we ask?
              </button>
              {whyOpen && (
                <p className="text-sm font-body text-text-muted">{question.why}</p>
              )}
            </div>
          )}
        </div>
        {!question.required && (
          <button
            type="button"
            onClick={() => onSkip(question.id)}
            disabled={isSubmitting}
            aria-label="Skip for now"
            className="text-sm font-ui text-text-faint hover:text-text-muted transition-colors whitespace-nowrap disabled:opacity-50"
          >
            Skip for now →
          </button>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4.4: Run test to verify it passes**

```bash
docker compose exec frontend npm test -- --testPathPattern="QuestionCard" --no-coverage
```

Expected: PASS (9 tests)

- [ ] **Step 4.5: Commit**

```bash
git add frontend/components/interview/QuestionCard.tsx frontend/__tests__/QuestionCard.test.tsx
git commit -m "feat: implement QuestionCard — options, back, skip, why tooltip"
```

---

## Task 5: ProgressDots component

**Files:**
- Create: `frontend/components/interview/ProgressDots.tsx`
- Create: `frontend/__tests__/ProgressDots.test.tsx`

- [ ] **Step 5.1: Write the failing tests**

Create `frontend/__tests__/ProgressDots.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import ProgressDots from '@/components/interview/ProgressDots'

test('renders correct total number of dots', () => {
  const { container } = render(<ProgressDots completed={2} total={5} />)
  expect(container.querySelectorAll('[data-testid="dot"]')).toHaveLength(5)
})

test('completed dots have bg-ready class', () => {
  const { container } = render(<ProgressDots completed={2} total={5} />)
  const dots = container.querySelectorAll('[data-testid="dot"]')
  expect(dots[0].className).toContain('bg-ready')
  expect(dots[1].className).toContain('bg-ready')
})

test('current dot (index = completed) has bg-accent class', () => {
  const { container } = render(<ProgressDots completed={2} total={5} />)
  const dots = container.querySelectorAll('[data-testid="dot"]')
  expect(dots[2].className).toContain('bg-accent')
})

test('upcoming dots have bg-border class', () => {
  const { container } = render(<ProgressDots completed={2} total={5} />)
  const dots = container.querySelectorAll('[data-testid="dot"]')
  expect(dots[3].className).toContain('bg-border')
  expect(dots[4].className).toContain('bg-border')
})

test('has accessible aria-label', () => {
  render(<ProgressDots completed={2} total={5} />)
  expect(screen.getByLabelText('2 of 5 questions answered')).toBeInTheDocument()
})
```

- [ ] **Step 5.2: Run test to verify it fails**

```bash
docker compose exec frontend npm test -- --testPathPattern="ProgressDots" --no-coverage
```

Expected: FAIL — `Cannot find module '@/components/interview/ProgressDots'`

- [ ] **Step 5.3: Create the component**

Create `frontend/components/interview/ProgressDots.tsx`:

```tsx
interface Props {
  completed: number
  total: number
}

export default function ProgressDots({ completed, total }: Props) {
  return (
    <div
      className="flex items-center gap-2"
      aria-label={`${completed} of ${total} questions answered`}
    >
      {Array.from({ length: total }).map((_, i) => {
        const isDone = i < completed
        const isCurrent = i === completed
        return (
          <div
            key={i}
            data-testid="dot"
            className={[
              'rounded-full transition-all',
              isDone    ? 'w-2 h-2 bg-ready'  : '',
              isCurrent ? 'w-3 h-3 bg-accent' : '',
              !isDone && !isCurrent ? 'w-2 h-2 bg-border' : '',
            ].filter(Boolean).join(' ')}
          />
        )
      })}
    </div>
  )
}
```

- [ ] **Step 5.4: Run test to verify it passes**

```bash
docker compose exec frontend npm test -- --testPathPattern="ProgressDots" --no-coverage
```

Expected: PASS (5 tests)

- [ ] **Step 5.5: Commit**

```bash
git add frontend/components/interview/ProgressDots.tsx frontend/__tests__/ProgressDots.test.tsx
git commit -m "feat: implement ProgressDots — dot indicator for interview progress"
```

---

## Task 6: YoYSuggestionCard component

**Files:**
- Create: `frontend/components/interview/YoYSuggestionCard.tsx`
- Create: `frontend/__tests__/YoYSuggestionCard.test.tsx`

- [ ] **Step 6.1: Write the failing tests**

Create `frontend/__tests__/YoYSuggestionCard.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import YoYSuggestionCard from '@/components/interview/YoYSuggestionCard'
import type { YoYSuggestion } from '@/lib/api/types'

const suggestion: YoYSuggestion = {
  id: 'sug-1',
  category: 'work_expense',
  description: 'Home internet (work portion)',
  amount_last_year: 180.00,
  frequency: 'annual',
  status: 'pending',
}

test('renders description', () => {
  render(<YoYSuggestionCard suggestion={suggestion} onAction={jest.fn()} />)
  expect(screen.getByText('Home internet (work portion)')).toBeInTheDocument()
})

test('renders three action buttons', () => {
  render(<YoYSuggestionCard suggestion={suggestion} onAction={jest.fn()} />)
  expect(screen.getByRole('button', { name: /yes, still use it/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /no longer/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /already added/i })).toBeInTheDocument()
})

test('calls onAction with "confirmed" on first button', () => {
  const onAction = jest.fn()
  render(<YoYSuggestionCard suggestion={suggestion} onAction={onAction} />)
  fireEvent.click(screen.getByRole('button', { name: /yes, still use it/i }))
  expect(onAction).toHaveBeenCalledWith('sug-1', 'confirmed')
})

test('calls onAction with "dismissed" on second button', () => {
  const onAction = jest.fn()
  render(<YoYSuggestionCard suggestion={suggestion} onAction={onAction} />)
  fireEvent.click(screen.getByRole('button', { name: /no longer/i }))
  expect(onAction).toHaveBeenCalledWith('sug-1', 'dismissed')
})

test('calls onAction with "not_applicable" on third button', () => {
  const onAction = jest.fn()
  render(<YoYSuggestionCard suggestion={suggestion} onAction={onAction} />)
  fireEvent.click(screen.getByRole('button', { name: /already added/i }))
  expect(onAction).toHaveBeenCalledWith('sug-1', 'not_applicable')
})
```

- [ ] **Step 6.2: Run test to verify it fails**

```bash
docker compose exec frontend npm test -- --testPathPattern="YoYSuggestionCard" --no-coverage
```

Expected: FAIL — `Cannot find module '@/components/interview/YoYSuggestionCard'`

- [ ] **Step 6.3: Create the component**

Create `frontend/components/interview/YoYSuggestionCard.tsx`:

```tsx
import type { YoYSuggestion } from '@/lib/api/types'

interface Props {
  suggestion: YoYSuggestion
  onAction: (id: string, action: 'confirmed' | 'dismissed' | 'not_applicable') => void
}

export default function YoYSuggestionCard({ suggestion, onAction }: Props) {
  return (
    <div className="bg-surface border border-border rounded-md p-4 space-y-3">
      <p className="font-ui text-text-body">{suggestion.description}</p>
      {suggestion.amount_last_year != null && (
        <p className="font-mono text-sm text-text-muted">
          ${suggestion.amount_last_year.toFixed(2)} last year
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onAction(suggestion.id, 'confirmed')}
          className="px-4 py-2 rounded-sm bg-ready-bg text-ready text-sm font-ui hover:opacity-80 transition-opacity"
        >
          Yes, still use it
        </button>
        <button
          type="button"
          onClick={() => onAction(suggestion.id, 'dismissed')}
          className="px-4 py-2 rounded-sm bg-surface border border-border text-text-muted text-sm font-ui hover:border-border-strong transition-colors"
        >
          No longer
        </button>
        <button
          type="button"
          onClick={() => onAction(suggestion.id, 'not_applicable')}
          className="px-4 py-2 rounded-sm bg-surface border border-border text-text-muted text-sm font-ui hover:border-border-strong transition-colors"
        >
          Already added
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 6.4: Run test to verify it passes**

```bash
docker compose exec frontend npm test -- --testPathPattern="YoYSuggestionCard" --no-coverage
```

Expected: PASS (5 tests)

- [ ] **Step 6.5: Commit**

```bash
git add frontend/components/interview/YoYSuggestionCard.tsx frontend/__tests__/YoYSuggestionCard.test.tsx
git commit -m "feat: implement YoYSuggestionCard — year-over-year suggestion with three actions"
```

---

## Task 7: Journey page

**Files:**
- Create: `frontend/lib/hooks/useInterview.ts`
- Modify: `frontend/app/(dashboard)/journey/page.tsx`
- Create: `frontend/__tests__/journey-page.test.tsx`

- [ ] **Step 7.1: Write the failing tests**

Create `frontend/__tests__/journey-page.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import JourneyPage from '@/app/(dashboard)/journey/page'
import * as interviewApi from '@/lib/api/interview'

jest.mock('@/lib/api/interview')

const mockNewSkillPending = { value: null as string | null }
const mockSetNewSkillPending = jest.fn((v: string | null) => { mockNewSkillPending.value = v })
jest.mock('@/lib/stores/interview.store', () => ({
  default: () => ({ newSkillPending: mockNewSkillPending.value, setNewSkillPending: mockSetNewSkillPending }),
}))

const mockGetSession = interviewApi.getSession as jest.Mock
const mockGetYoySuggestions = interviewApi.getYoySuggestions as jest.Mock

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const SESSION = (state: string, question?: object) => ({
  data: {
    data: {
      state,
      current_question: question ?? null,
      activated_skills: ['employee_tax_au'],
      progress: { completed: 1, total: 5 },
    },
  },
})

const QUESTION = {
  id: 'wfh', ask: 'Did you work from home?', type: 'single_choice',
  options: ['yes', 'no'], branches: null, required: false, why: null, hint: null,
}

beforeEach(() => {
  jest.clearAllMocks()
  mockNewSkillPending.value = null
  mockGetYoySuggestions.mockResolvedValue({ data: { data: [] } })
})

test('shows loading state initially', () => {
  mockGetSession.mockReturnValue(new Promise(() => {}))
  wrap(<JourneyPage />)
  expect(screen.getByText(/loading/i)).toBeInTheDocument()
})

test('shows start CTA when state is not_started', async () => {
  mockGetSession.mockResolvedValue(SESSION('not_started'))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByRole('button', { name: /get started/i })).toBeInTheDocument())
})

test('shows QuestionCard when state is in_progress', async () => {
  mockGetSession.mockResolvedValue(SESSION('in_progress', QUESTION))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText('Did you work from home?')).toBeInTheDocument())
})

test('shows completion screen when state is awaiting_evidence', async () => {
  mockGetSession.mockResolvedValue(SESSION('awaiting_evidence'))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(/you're all set up/i)).toBeInTheDocument())
})

test('shows link to readiness when state is complete', async () => {
  mockGetSession.mockResolvedValue(SESSION('complete'))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByRole('link', { name: /readiness/i })).toBeInTheDocument())
})

test('shows error state on API failure', async () => {
  mockGetSession.mockRejectedValue(new Error('Network error'))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(/unable to load/i)).toBeInTheDocument())
})

test('new skill banner renders when newSkillPending is set', async () => {
  mockNewSkillPending.value = 'wfh_skill'
  mockGetSession.mockResolvedValue(SESSION('in_progress', QUESTION))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(/we found something new/i)).toBeInTheDocument())
})

test('shows personalised next step for active skill on awaiting_evidence', async () => {
  mockGetSession.mockResolvedValue(SESSION('awaiting_evidence'))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(/PAYG Payment Summary/i)).toBeInTheDocument())
})
```

- [ ] **Step 7.2: Run test to verify it fails**

```bash
docker compose exec frontend npm test -- --testPathPattern="journey-page" --no-coverage
```

Expected: FAIL — page renders "Journey — coming soon" not the expected content

- [ ] **Step 7.3: Create useInterview hook**

Create `frontend/lib/hooks/useInterview.ts`:

```typescript
'use client'
import { useQuery } from '@tanstack/react-query'
import { getSession } from '@/lib/api/interview'
import type { InterviewSessionData } from '@/lib/api/types'

export function useInterview() {
  const { data, isLoading, isError } = useQuery<InterviewSessionData>({
    queryKey: ['interview', 'session'],
    queryFn: () => getSession().then((r) => r.data.data),
  })
  return { data, isLoading, isError }
}
```

- [ ] **Step 7.4: Implement the journey page**

Replace `frontend/app/(dashboard)/journey/page.tsx`:

```tsx
'use client'
import Link from 'next/link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getSession, startInterview, answerQuestion,
  goBack, skipQuestion, getYoySuggestions, actOnSuggestion,
} from '@/lib/api/interview'
import type { InterviewSessionData, YoYSuggestion } from '@/lib/api/types'
import QuestionCard from '@/components/interview/QuestionCard'
import ProgressDots from '@/components/interview/ProgressDots'
import YoYSuggestionCard from '@/components/interview/YoYSuggestionCard'
import useInterviewStore from '@/lib/stores/interview.store'

const NEXT_STEPS: Record<string, { label: string; hint: string }> = {
  employee_tax_au: {
    label: 'Upload your PAYG Payment Summary',
    hint: 'Download from myGov → ATO online services',
  },
  wfh_skill: {
    label: 'Gather your WFH records',
    hint: 'Timesheets, diary, or ATO app records',
  },
  investment_skill: {
    label: 'Export your investment statement',
    hint: 'Download from your broker or share registry',
  },
  crypto_skill_au: {
    label: 'Export your crypto transaction history',
    hint: 'Download CSV from CoinSpot or your exchange',
  },
}

export default function JourneyPage() {
  const queryClient = useQueryClient()
  const { newSkillPending, setNewSkillPending } = useInterviewStore()

  const { data, isLoading, isError } = useQuery<InterviewSessionData>({
    queryKey: ['interview', 'session'],
    queryFn: () => getSession().then((r) => r.data.data),
  })

  const { data: yoy } = useQuery<YoYSuggestion[]>({
    queryKey: ['yoy', 'suggestions'],
    queryFn: () => getYoySuggestions().then((r) => r.data.data),
    enabled: data?.state === 'awaiting_evidence' || data?.state === 'complete',
  })

  const patch = (p: Partial<InterviewSessionData>) =>
    queryClient.setQueryData<InterviewSessionData>(['interview', 'session'], (old) =>
      old ? { ...old, ...p } : old
    )

  const startMutation = useMutation({
    mutationFn: startInterview,
    onSuccess: (res) => patch(res.data.data),
  })

  const answerMutation = useMutation({
    mutationFn: ({ question_id, answer }: { question_id: string; answer: string }) =>
      answerQuestion(question_id, answer),
    onSuccess: (res) => {
      const d = res.data.data
      const prev = data?.activated_skills ?? []
      const newSkill = d.activated_skills.find((s) => !prev.includes(s))
      if (newSkill) setNewSkillPending(newSkill)
      patch({ state: d.state, current_question: d.next_question, activated_skills: d.activated_skills, progress: d.progress })
    },
  })

  const backMutation = useMutation({
    mutationFn: goBack,
    onSuccess: (res) => patch(res.data.data),
  })

  const skipMutation = useMutation({
    mutationFn: ({ question_id, reason }: { question_id: string; reason: string }) =>
      skipQuestion(question_id, reason),
    onSuccess: (res) => {
      const d = res.data.data
      patch({ state: d.state, current_question: d.next_question, progress: d.progress })
    },
  })

  const yoyMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) => actOnSuggestion(id, action),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['yoy', 'suggestions'] }),
  })

  const isBusy = answerMutation.isPending || backMutation.isPending || skipMutation.isPending

  if (isLoading) return <div className="p-8 font-ui text-text-muted">Loading...</div>
  if (isError || !data) return <div className="p-8 font-ui text-risk-high">Unable to load your tax journey.</div>

  return (
    <div className="max-w-xl mx-auto px-4 py-8 space-y-6">

      {newSkillPending && (
        <div className="bg-accent-soft border border-accent rounded-md p-4 flex items-start justify-between gap-4">
          <div>
            <p className="font-ui font-medium text-text-primary">We found something new in your tax profile</p>
            <p className="text-sm font-body text-text-muted">A few more questions needed.</p>
          </div>
          <button
            type="button"
            onClick={() => setNewSkillPending(null)}
            className="text-sm font-ui font-medium text-accent hover:text-accent-hover whitespace-nowrap transition-colors"
          >
            Continue →
          </button>
        </div>
      )}

      {data.state === 'not_started' && (
        <div className="space-y-6 pt-8">
          <div className="space-y-3">
            <h1 className="font-display text-3xl text-text-primary">Start your tax journey</h1>
            <p className="font-body text-text-muted">
              We'll ask you a few questions to personalise your tax preparation experience.
            </p>
          </div>
          <button
            type="button"
            onClick={() => startMutation.mutate()}
            disabled={startMutation.isPending}
            className="px-6 py-3 rounded-md bg-accent text-surface font-ui font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            {startMutation.isPending ? 'Starting...' : 'Get started →'}
          </button>
        </div>
      )}

      {(data.state === 'in_progress' || data.state === 'paused') && data.current_question && (
        <div className="space-y-6">
          <ProgressDots completed={data.progress.completed} total={data.progress.total} />
          <QuestionCard
            question={data.current_question}
            onAnswer={(qid, ans) => answerMutation.mutate({ question_id: qid, answer: ans })}
            onBack={() => backMutation.mutate()}
            onSkip={(qid) => skipMutation.mutate({ question_id: qid, reason: 'user_skipped' })}
            isSubmitting={isBusy}
          />
        </div>
      )}

      {data.state === 'awaiting_evidence' && (
        <div className="space-y-8">
          <div className="space-y-3">
            <h1 className="font-display text-3xl text-text-primary">You're all set up</h1>
            <p className="font-body text-text-muted">Here's what to gather next based on your profile:</p>
          </div>
          <ul className="space-y-3">
            {(data.activated_skills ?? []).slice(0, 3).map((skillId) => {
              const step = NEXT_STEPS[skillId]
              if (!step) return null
              return (
                <li key={skillId} className="bg-surface border border-border rounded-md p-4 space-y-1">
                  <p className="font-ui font-medium text-text-body">{step.label}</p>
                  <p className="text-sm font-body text-text-muted">{step.hint}</p>
                </li>
              )
            })}
          </ul>
          {yoy && yoy.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-ui font-medium text-text-muted uppercase tracking-wide">From last year</h2>
              {yoy.slice(0, 3).map((s) => (
                <YoYSuggestionCard
                  key={s.id}
                  suggestion={s}
                  onAction={(id, action) => yoyMutation.mutate({ id, action })}
                />
              ))}
            </div>
          )}
          <Link
            href="/readiness"
            className="inline-block px-6 py-3 rounded-md bg-ready text-surface font-ui font-medium hover:opacity-90 transition-opacity"
          >
            View your readiness →
          </Link>
        </div>
      )}

      {data.state === 'complete' && (
        <div className="space-y-6 pt-8">
          <div className="space-y-3">
            <h1 className="font-display text-3xl text-text-primary">Interview complete</h1>
            <p className="font-body text-text-muted">
              Your tax profile is set up. Check your readiness score to see what's next.
            </p>
          </div>
          <Link
            href="/readiness"
            className="inline-block text-accent font-ui font-medium hover:text-accent-hover transition-colors"
            aria-label="View your tax readiness"
          >
            View your tax readiness →
          </Link>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 7.5: Run tests to verify they pass**

```bash
docker compose exec frontend npm test -- --testPathPattern="journey-page" --no-coverage
```

Expected: PASS (8 tests)

- [ ] **Step 7.6: Commit**

```bash
git add frontend/lib/hooks/useInterview.ts \
        frontend/app/(dashboard)/journey/page.tsx \
        frontend/__tests__/journey-page.test.tsx
git commit -m "feat: implement Journey page — interview hub with QuestionCard, ProgressDots, YoY suggestions"
```

---

## Task 8: Full test suite verification

- [ ] **Step 8.1: Run full backend test suite**

```bash
make test
```

Expected: all 123 backend tests pass (no regressions from Question dataclass extension).

- [ ] **Step 8.2: Run full frontend test suite**

```bash
docker compose exec frontend npm test -- --no-coverage
```

Expected: all test suites pass. New total: ~119 tests (83 existing + 7 api + 3 store + 9 QuestionCard + 5 ProgressDots + 5 YoYSuggestionCard + 8 journey-page = 120; minor count variance is fine).

- [ ] **Step 8.3: Commit any fixes if needed**

```bash
git add <changed files>
git commit -m "fix: <describe fix>"
```

---

## Self-Review

**Spec coverage:**
- ✅ `journey/page.tsx` — not_started CTA, in_progress QuestionCard, awaiting_evidence completion + next steps, complete readiness link, error state, new skill banner
- ✅ `QuestionCard.tsx` — question text, hint, options, back always visible, skip for non-required, why tooltip toggle
- ✅ `ProgressDots.tsx` — dots only (not percentage bar), ready/accent/border states
- ✅ `YoYSuggestionCard.tsx` — description, three action buttons, correct action IDs
- ✅ `lib/api/interview.ts` — all 9 functions including pause/complete/yoy
- ✅ `interview.store.ts` — newSkillPending only (server state stays in React Query)
- ✅ New skill banner — non-blocking, shown when `newSkillPending` is set
- ✅ Personalised next steps — derived from `activated_skills`, max 3, NEXT_STEPS map
- ✅ Design tokens — `font-display`, `text-xl`, `bg-accent`, `rounded-md`, no hex/arbitrary values

**Placeholder scan:** No TBD/TODO/placeholder in any code block.

**Type consistency:**
- `InterviewQuestion.required` (Task 2 types) → used in `QuestionCard` (Task 4) ✓
- `InterviewQuestion.why` (Task 2 types) → used in `QuestionCard` (Task 4) ✓
- `AnswerResponseData.next_question` → patched as `current_question` in session cache (Task 7) ✓
- `YoYSuggestion.id` → passed to `actOnSuggestion` in journey page (Task 7) ✓
- `actOnSuggestion` action strings (`'confirmed'`, `'dismissed'`, `'not_applicable'`) match `YoYSuggestionCard` and `yoy.py` route ✓
