# M10 Phase 1: Layout Shell + Auth Pages — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the M1 frontend stubs with a real root layout (React Query + fonts), real auth pages (login, setup), and a real dashboard shell (sidebar + mobile bottom tabs) — all styled with DESIGN.md tokens, all with passing tests.

**Architecture:** Next.js 14 App Router with `'use client'` boundaries at the layout/page level. Zustand (`workspace.store.ts`) holds auth/workspace state globally. React Query wraps the whole app via a `Providers` client component. All API calls go through `lib/api/auth.ts`, never raw fetch. Dashboard layout uses CSS-driven responsive switching: `hidden md:flex` sidebar + `flex md:hidden` bottom tab bar.

**Tech Stack:** Next.js 14, TypeScript strict, Tailwind CSS (CSS-var tokens only), Zustand 4, React Query 5, React Hook Form 7, Lucide React, next-pwa, Jest + React Testing Library + `@testing-library/user-event`

---

## Current State (what the stubs have now)

| File | State |
|------|-------|
| `jest.config.js` | No TypeScript transform — tests fail on any `.tsx` file |
| `package.json` | Missing: `lucide-react`, `react-hook-form`, `@testing-library/user-event`, `next-pwa` |
| `workspace.store.ts` | Stub — only `workspaceId` + `setWorkspaceId`, missing `financialYear`, `isAuthenticated`, `isUnlocked` |
| `lib/api/auth.ts` | Does not exist |
| `lib/hooks/useAuth.ts` | Does not exist |
| `app/layout.tsx` | No QueryProvider, no font class |
| `app/(auth)/login/page.tsx` | Uses raw `fetch()` directly, no design tokens |
| `app/(auth)/setup/page.tsx` | Does not exist |
| `app/(dashboard)/layout.tsx` | Pass-through only |
| `Disclaimer.tsx` | Text doesn't match ARCHITECTURE.md §0 exactly |

---

## File Map

**Create:**
```
frontend/jest.setup.ts
frontend/__tests__/workspace-store.test.ts
frontend/__tests__/auth-api.test.ts
frontend/__tests__/useAuth.test.tsx
frontend/__tests__/login.test.tsx
frontend/__tests__/setup.test.tsx
frontend/__tests__/dashboard-layout.test.tsx
frontend/lib/api/auth.ts
frontend/lib/hooks/useAuth.ts
frontend/app/(auth)/setup/page.tsx
frontend/components/shared/Providers.tsx
```

**Modify:**
```
frontend/package.json         — add 4 packages
frontend/jest.config.js       — use next/jest (SWC transform, no extra deps)
frontend/next.config.js       — wrap with withPWA
frontend/lib/api/types.ts     — add SessionData, SetupResponse
frontend/lib/stores/workspace.store.ts — full WorkspaceStore interface
frontend/components/shared/Disclaimer.tsx — fix text to ARCHITECTURE.md §0
frontend/app/layout.tsx       — add Providers, font class
frontend/app/(auth)/login/page.tsx — rewrite with real logic + design tokens
frontend/app/(dashboard)/layout.tsx — real sidebar + mobile tabs
```

---

## Task 1: Dependency install + Jest/TypeScript setup

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/jest.config.js`
- Create: `frontend/jest.setup.ts`
- Modify: `frontend/next.config.js`

- [ ] **Step 1: Update package.json — add missing deps**

```json
// frontend/package.json — add to "dependencies":
"lucide-react": "^0.400.0",
"react-hook-form": "^7.52.0",
"next-pwa": "^5.6.0",

// add to "devDependencies":
"@testing-library/user-event": "^14.5.2"
```

Full updated package.json:
```json
{
  "name": "tax-return-ai-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "jest"
  },
  "dependencies": {
    "next": "^14.2.29",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@tanstack/react-query": "^5.51.1",
    "axios": "^1.7.2",
    "zustand": "^4.5.4",
    "lucide-react": "^0.400.0",
    "react-hook-form": "^7.52.0",
    "next-pwa": "^5.6.0"
  },
  "devDependencies": {
    "typescript": "^5.5.3",
    "@types/node": "^20.14.10",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "tailwindcss": "^3.4.6",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.39",
    "eslint": "^8.57.0",
    "eslint-config-next": "^14.2.29",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.4.6",
    "@testing-library/user-event": "^14.5.2",
    "jest": "^29.7.0",
    "jest-environment-jsdom": "^29.7.0"
  }
}
```

- [ ] **Step 2: Rewrite jest.config.js — use next/jest (SWC transform, no extra packages)**

```js
// frontend/jest.config.js
const nextJest = require('next/jest')
const createJestConfig = nextJest({ dir: './' })

/** @type {import('jest').Config} */
module.exports = createJestConfig({
  testEnvironment: 'jsdom',
  setupFilesAfterFramework: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
})
```

Wait — it's `setupFilesAfterFramework` → must be `setupFilesAfterEnv`:

```js
// frontend/jest.config.js
const nextJest = require('next/jest')
const createJestConfig = nextJest({ dir: './' })

/** @type {import('jest').Config} */
module.exports = createJestConfig({
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
})
```

- [ ] **Step 3: Create jest.setup.ts**

```ts
// frontend/jest.setup.ts
import '@testing-library/jest-dom'
```

- [ ] **Step 4: Wrap next.config.js with withPWA**

```js
// frontend/next.config.js
const withPWA = require('next-pwa')({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  register: true,
  skipWaiting: true,
})

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',

  async rewrites() {
    if (process.env.ENVIRONMENT === 'production') return []
    return [
      {
        source: '/api/:path*',
        destination: 'http://backend:8000/api/:path*',
      },
    ]
  },
}

module.exports = withPWA(nextConfig)
```

- [ ] **Step 5: Install packages in the running container**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend npm install
```

Expected: packages installed, no peer dep errors.

- [ ] **Step 6: Write a smoke test to verify the test runner works**

```ts
// frontend/__tests__/smoke.test.ts
describe('smoke', () => {
  it('test runner works', () => {
    expect(1 + 1).toBe(2)
  })
})
```

- [ ] **Step 7: Run and verify GREEN**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=smoke --watchAll=false
```

Expected: `PASS __tests__/smoke.test.ts`

- [ ] **Step 8: Delete the smoke test and commit**

```bash
# delete frontend/__tests__/smoke.test.ts
git add frontend/package.json frontend/jest.config.js frontend/jest.setup.ts frontend/next.config.js
git commit -m "chore: add lucide-react, react-hook-form, next-pwa; fix jest TypeScript setup"
```

---

## Task 2: WorkspaceStore — full interface (TDD)

**Files:**
- Create: `frontend/__tests__/workspace-store.test.ts`
- Modify: `frontend/lib/stores/workspace.store.ts`

- [ ] **Step 1: Write failing test**

```ts
// frontend/__tests__/workspace-store.test.ts
import useWorkspaceStore from '@/lib/stores/workspace.store'

describe('WorkspaceStore', () => {
  beforeEach(() => {
    useWorkspaceStore.setState({
      workspaceId: null,
      financialYear: null,
      isAuthenticated: false,
      isUnlocked: false,
    })
  })

  it('initial state is unauthenticated with no workspace', () => {
    const state = useWorkspaceStore.getState()
    expect(state.workspaceId).toBeNull()
    expect(state.financialYear).toBeNull()
    expect(state.isAuthenticated).toBe(false)
    expect(state.isUnlocked).toBe(false)
  })

  it('setWorkspace sets workspaceId and financialYear together', () => {
    useWorkspaceStore.getState().setWorkspace('ws-123', '2024-25')
    const state = useWorkspaceStore.getState()
    expect(state.workspaceId).toBe('ws-123')
    expect(state.financialYear).toBe('2024-25')
  })

  it('setAuthenticated updates isAuthenticated', () => {
    useWorkspaceStore.getState().setAuthenticated(true)
    expect(useWorkspaceStore.getState().isAuthenticated).toBe(true)
  })

  it('setUnlocked updates isUnlocked', () => {
    useWorkspaceStore.getState().setUnlocked(true)
    expect(useWorkspaceStore.getState().isUnlocked).toBe(true)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL (store missing fields)**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=workspace-store --watchAll=false
```

Expected: FAIL — `setWorkspace is not a function` or type errors.

- [ ] **Step 3: Rewrite workspace.store.ts with full interface**

```ts
// frontend/lib/stores/workspace.store.ts
import { create } from 'zustand'

interface WorkspaceStore {
  workspaceId: string | null
  financialYear: string | null
  isAuthenticated: boolean
  isUnlocked: boolean
  setWorkspace: (id: string, fy: string) => void
  setAuthenticated: (value: boolean) => void
  setUnlocked: (value: boolean) => void
}

const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  workspaceId: null,
  financialYear: null,
  isAuthenticated: false,
  isUnlocked: false,
  setWorkspace: (id, fy) => set({ workspaceId: id, financialYear: fy }),
  setAuthenticated: (value) => set({ isAuthenticated: value }),
  setUnlocked: (value) => set({ isUnlocked: value }),
}))

export default useWorkspaceStore
```

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=workspace-store --watchAll=false
```

Expected: `PASS __tests__/workspace-store.test.ts` — 4 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/__tests__/workspace-store.test.ts frontend/lib/stores/workspace.store.ts
git commit -m "feat: implement WorkspaceStore — workspace, auth, unlock state"
```

---

## Task 3: lib/api/types.ts + lib/api/auth.ts (TDD)

**Files:**
- Modify: `frontend/lib/api/types.ts`
- Create: `frontend/__tests__/auth-api.test.ts`
- Create: `frontend/lib/api/auth.ts`

- [ ] **Step 1: Add auth types to lib/api/types.ts**

```ts
// frontend/lib/api/types.ts
export interface ApiResponse<T> {
  data: T
  status: 'ok'
}

export interface ApiError {
  error_code: string
  message: string
  action: string | null
  retryable: boolean
}

export interface HealthResponse {
  status: 'ok'
  db: 'ok' | 'error'
  storage: 'ok' | 'error'
}

export interface SessionData {
  workspace_id: string
  financial_year: string
  is_unlocked: boolean
}

export interface LoginData extends SessionData {
  setup_not_confirmed?: boolean
}

export interface SetupData {
  recovery_key: string
}
```

- [ ] **Step 2: Write failing test for auth API**

```ts
// frontend/__tests__/auth-api.test.ts
jest.mock('@/lib/api/client', () => ({
  default: {
    post: jest.fn(),
    get: jest.fn(),
  },
}))

import client from '@/lib/api/client'
import * as authApi from '@/lib/api/auth'

const mockPost = client.post as jest.Mock
const mockGet = client.get as jest.Mock

beforeEach(() => {
  jest.clearAllMocks()
})

describe('auth API', () => {
  it('login POSTs to /api/v1/auth/login with password', async () => {
    mockPost.mockResolvedValue({ data: { data: { workspace_id: 'ws1' } } })
    await authApi.login('secret')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/login', { password: 'secret' })
  })

  it('logout POSTs to /api/v1/auth/logout', async () => {
    mockPost.mockResolvedValue({})
    await authApi.logout()
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/logout')
  })

  it('getSession GETs /api/v1/auth/session', async () => {
    mockGet.mockResolvedValue({ data: { data: {} } })
    await authApi.getSession()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/auth/session')
  })

  it('setup POSTs to /api/v1/auth/setup with password', async () => {
    mockPost.mockResolvedValue({ data: { data: { recovery_key: 'key' } } })
    await authApi.setup('mypassword')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/setup', { password: 'mypassword' })
  })

  it('setupConfirm POSTs to /api/v1/auth/setup/confirm with confirmation', async () => {
    mockPost.mockResolvedValue({})
    await authApi.setupConfirm('1234-5678')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/setup/confirm', { confirmation: '1234-5678' })
  })

  it('unlock POSTs to /api/v1/auth/unlock with password', async () => {
    mockPost.mockResolvedValue({})
    await authApi.unlock('mypassword')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/unlock', { password: 'mypassword' })
  })

  it('recover POSTs to /api/v1/auth/recover with recovery_key and new_password', async () => {
    mockPost.mockResolvedValue({})
    await authApi.recover('RECOVERY-KEY', 'newpassword')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/recover', {
      recovery_key: 'RECOVERY-KEY',
      new_password: 'newpassword',
    })
  })
})
```

- [ ] **Step 3: Run test — expect FAIL (module not found)**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=auth-api --watchAll=false
```

Expected: FAIL — `Cannot find module '@/lib/api/auth'`

- [ ] **Step 4: Create lib/api/auth.ts**

```ts
// frontend/lib/api/auth.ts
import client from './client'
import type { ApiResponse, LoginData, SessionData, SetupData } from './types'

export const login = (password: string) =>
  client.post<ApiResponse<LoginData>>('/api/v1/auth/login', { password })

export const logout = () =>
  client.post('/api/v1/auth/logout')

export const getSession = () =>
  client.get<ApiResponse<SessionData>>('/api/v1/auth/session')

export const setup = (password: string) =>
  client.post<ApiResponse<SetupData>>('/api/v1/auth/setup', { password })

export const setupConfirm = (confirmation: string) =>
  client.post('/api/v1/auth/setup/confirm', { confirmation })

export const unlock = (password: string) =>
  client.post('/api/v1/auth/unlock', { password })

export const recover = (recoveryKey: string, newPassword: string) =>
  client.post('/api/v1/auth/recover', { recovery_key: recoveryKey, new_password: newPassword })
```

- [ ] **Step 5: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=auth-api --watchAll=false
```

Expected: `PASS __tests__/auth-api.test.ts` — 7 tests passing.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/api/types.ts frontend/lib/api/auth.ts frontend/__tests__/auth-api.test.ts
git commit -m "feat: add auth API functions and SessionData/SetupData types"
```

---

## Task 4: Fix Disclaimer.tsx + create Providers component

**Files:**
- Modify: `frontend/components/shared/Disclaimer.tsx`
- Create: `frontend/components/shared/Providers.tsx`

- [ ] **Step 1: Update Disclaimer.tsx to match ARCHITECTURE.md §0 exact text**

```tsx
// frontend/components/shared/Disclaimer.tsx
export default function Disclaimer() {
  return (
    <p className="text-xs text-text-muted border-t border-border pt-3 mt-3 font-ui">
      This tool helps organise your tax information and prepare a review package.
      It does not provide final tax advice and does not replace review by
      a registered tax agent.
    </p>
  )
}
```

- [ ] **Step 2: Create Providers.tsx — React Query client wrapper**

```tsx
// frontend/components/shared/Providers.tsx
'use client'

import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            staleTime: 30_000,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/shared/Disclaimer.tsx frontend/components/shared/Providers.tsx
git commit -m "feat: fix Disclaimer text to ARCHITECTURE.md spec; add QueryClient Providers"
```

---

## Task 5: Root layout.tsx — add Providers + font class

**Files:**
- Modify: `frontend/app/layout.tsx`

No unit test for the root server layout (it's a Server Component with no testable logic). The Providers wrapping is verified transitively by the component tests that use React Query hooks.

- [ ] **Step 1: Update app/layout.tsx**

```tsx
// frontend/app/layout.tsx
import type { Metadata } from 'next'
import Providers from '@/components/shared/Providers'
import '../styles/globals.css'

export const metadata: Metadata = {
  title: 'Tax Return AI',
  description: 'AI-guided tax preparation workspace for Australian taxpayers',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="font-body">
      <body className="bg-canvas text-text-body min-h-screen">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/layout.tsx
git commit -m "feat: wire React Query Providers and design tokens into root layout"
```

---

## Task 6: useAuth hook (TDD)

**Files:**
- Create: `frontend/__tests__/useAuth.test.tsx`
- Create: `frontend/lib/hooks/useAuth.ts`

- [ ] **Step 1: Write failing tests**

```tsx
// frontend/__tests__/useAuth.test.tsx
import { renderHook, waitFor } from '@testing-library/react'
import { useAuth } from '@/lib/hooks/useAuth'

const mockReplace = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace, push: jest.fn() }),
}))

jest.mock('@/lib/api/auth', () => ({
  getSession: jest.fn(),
}))

import { getSession } from '@/lib/api/auth'

const mockGetSession = getSession as jest.Mock

beforeEach(() => {
  jest.clearAllMocks()
})

describe('useAuth', () => {
  it('redirects to /login when session request fails with generic error', async () => {
    mockGetSession.mockRejectedValue({
      response: { data: { error_code: 'not_authenticated' } },
    })
    renderHook(() => useAuth())
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/login')
    })
  })

  it('redirects to /setup when error_code is setup_not_confirmed', async () => {
    mockGetSession.mockRejectedValue({
      response: { data: { error_code: 'setup_not_confirmed' } },
    })
    renderHook(() => useAuth())
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/setup')
    })
  })

  it('does not redirect when session exists', async () => {
    mockGetSession.mockResolvedValue({
      data: {
        data: {
          workspace_id: 'ws-1',
          financial_year: '2024-25',
          is_unlocked: true,
        },
      },
    })
    renderHook(() => useAuth())
    await waitFor(() => {
      expect(mockReplace).not.toHaveBeenCalled()
    })
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=useAuth --watchAll=false
```

Expected: FAIL — `Cannot find module '@/lib/hooks/useAuth'`

- [ ] **Step 3: Create lib/hooks/useAuth.ts**

```ts
// frontend/lib/hooks/useAuth.ts
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getSession } from '@/lib/api/auth'
import useWorkspaceStore from '@/lib/stores/workspace.store'

export function useAuth() {
  const router = useRouter()
  const { setWorkspace, setAuthenticated, setUnlocked, isAuthenticated } =
    useWorkspaceStore()

  useEffect(() => {
    getSession()
      .then((res) => {
        const { workspace_id, financial_year, is_unlocked } = res.data.data
        setWorkspace(workspace_id, financial_year)
        setAuthenticated(true)
        setUnlocked(is_unlocked)
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

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=useAuth --watchAll=false
```

Expected: `PASS __tests__/useAuth.test.tsx` — 3 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/__tests__/useAuth.test.tsx frontend/lib/hooks/useAuth.ts
git commit -m "feat: implement useAuth hook — session check, redirect to login/setup"
```

---

## Task 7: Login page — real implementation (TDD)

**Files:**
- Create: `frontend/__tests__/login.test.tsx`
- Modify: `frontend/app/(auth)/login/page.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
// frontend/__tests__/login.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginPage from '@/app/(auth)/login/page'

const mockPush = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

jest.mock('@/lib/api/auth', () => ({
  login: jest.fn(),
}))

import { login as mockLogin } from '@/lib/api/auth'

beforeEach(() => {
  jest.clearAllMocks()
})

describe('LoginPage', () => {
  it('renders password input and submit button', () => {
    render(<LoginPage />)
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument()
  })

  it('disables submit button while submitting', async () => {
    const user = userEvent.setup()
    let resolveLogin!: (v: unknown) => void
    ;(mockLogin as jest.Mock).mockReturnValue(
      new Promise((r) => { resolveLogin = r })
    )
    render(<LoginPage />)
    await user.type(screen.getByLabelText(/password/i), 'anypass')
    await user.click(screen.getByRole('button', { name: /log in/i }))
    expect(screen.getByRole('button', { name: /logging in/i })).toBeDisabled()
    resolveLogin({ data: { data: { workspace_id: 'w', financial_year: '2024-25', is_unlocked: false } } })
  })

  it('shows error message on wrong password', async () => {
    const user = userEvent.setup()
    ;(mockLogin as jest.Mock).mockRejectedValue({
      response: {
        data: { detail: { message: 'Wrong password.', error_code: 'invalid_password' } },
      },
    })
    render(<LoginPage />)
    await user.type(screen.getByLabelText(/password/i), 'wrongpass')
    await user.click(screen.getByRole('button', { name: /log in/i }))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Wrong password.')
    })
  })

  it('redirects to /readiness on successful login', async () => {
    const user = userEvent.setup()
    ;(mockLogin as jest.Mock).mockResolvedValue({
      data: {
        data: {
          workspace_id: 'ws-1',
          financial_year: '2024-25',
          is_unlocked: false,
        },
      },
    })
    render(<LoginPage />)
    await user.type(screen.getByLabelText(/password/i), 'correctpass')
    await user.click(screen.getByRole('button', { name: /log in/i }))
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/readiness')
    })
  })

  it('redirects to /setup on setup_not_confirmed error', async () => {
    const user = userEvent.setup()
    ;(mockLogin as jest.Mock).mockRejectedValue({
      response: {
        data: { detail: { error_code: 'setup_not_confirmed' } },
      },
    })
    render(<LoginPage />)
    await user.type(screen.getByLabelText(/password/i), 'anypass')
    await user.click(screen.getByRole('button', { name: /log in/i }))
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/setup')
    })
  })

  it('toggles password visibility', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    const input = screen.getByLabelText(/password/i)
    expect(input).toHaveAttribute('type', 'password')
    await user.click(screen.getByLabelText(/show password/i))
    expect(input).toHaveAttribute('type', 'text')
    await user.click(screen.getByLabelText(/hide password/i))
    expect(input).toHaveAttribute('type', 'password')
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=login --watchAll=false
```

Expected: FAIL — multiple failures because the stub login page doesn't use `lib/api/auth.ts` or match the test expectations.

- [ ] **Step 3: Rewrite app/(auth)/login/page.tsx**

```tsx
// frontend/app/(auth)/login/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { Eye, EyeOff } from 'lucide-react'
import { login } from '@/lib/api/auth'
import useWorkspaceStore from '@/lib/stores/workspace.store'

interface LoginForm {
  password: string
}

export default function LoginPage() {
  const router = useRouter()
  const { setWorkspace, setAuthenticated } = useWorkspaceStore()
  const [showPassword, setShowPassword] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<LoginForm>()

  async function onSubmit({ password }: LoginForm) {
    setServerError(null)
    try {
      const res = await login(password)
      const { workspace_id, financial_year } = res.data.data
      setWorkspace(workspace_id, financial_year)
      setAuthenticated(true)
      router.push('/readiness')
    } catch (err: unknown) {
      const detail = (
        err as {
          response?: {
            data?: { detail?: { error_code?: string; message?: string } }
          }
        }
      )?.response?.data?.detail
      if (detail?.error_code === 'setup_not_confirmed') {
        router.push('/setup')
        return
      }
      setServerError(detail?.message ?? 'Login failed. Check your password.')
    }
  }

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="font-display text-3xl font-semibold text-text-primary mb-2">
          Tax Return AI
        </h1>
        <p className="font-ui text-sm text-text-muted mb-8">
          Pre-tax-agent preparation tool
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label
              htmlFor="password"
              className="block font-ui text-sm font-medium text-text-body mb-1"
            >
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoFocus
                autoComplete="current-password"
                className="w-full px-4 py-3 rounded-md border border-border bg-surface font-ui text-base text-text-primary focus:outline-none focus:shadow-focus"
                {...register('password', { required: true })}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-body"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {serverError && (
            <p role="alert" className="font-ui text-sm text-risk-high">
              {serverError}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 rounded-md bg-accent hover:bg-accent-hover text-white font-ui font-medium text-base disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? 'Logging in…' : 'Log in'}
          </button>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=login --watchAll=false
```

Expected: `PASS __tests__/login.test.tsx` — 6 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/__tests__/login.test.tsx frontend/app/'(auth)'/login/page.tsx
git commit -m "feat: implement real login page — design tokens, show/hide, API via lib/api/auth"
```

---

## Task 8: Setup page — 3-step onboarding (TDD)

**Files:**
- Create: `frontend/__tests__/setup.test.tsx`
- Create: `frontend/app/(auth)/setup/page.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
// frontend/__tests__/setup.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SetupPage from '@/app/(auth)/setup/page'

const mockPush = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

jest.mock('@/lib/api/auth', () => ({
  setup: jest.fn(),
  setupConfirm: jest.fn(),
}))

import { setup as mockSetup, setupConfirm as mockSetupConfirm } from '@/lib/api/auth'

const RECOVERY_KEY = 'ABCD-EFGH-1234-5678-WXYZ-ABCD-1234-5678'

beforeEach(() => {
  jest.clearAllMocks()
})

describe('SetupPage', () => {
  it('renders step 1 — set password heading and inputs', () => {
    render(<SetupPage />)
    expect(screen.getByRole('heading', { name: /set your password/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
  })

  it('step 1 shows strength indicator as password is typed', async () => {
    const user = userEvent.setup()
    render(<SetupPage />)
    await user.type(screen.getByLabelText(/^password$/i), 'weak')
    expect(screen.getByTestId('strength-indicator')).toBeInTheDocument()
  })

  it('shows step 2 — recovery key after step 1 completes', async () => {
    const user = userEvent.setup()
    ;(mockSetup as jest.Mock).mockResolvedValue({
      data: { data: { recovery_key: RECOVERY_KEY } },
    })
    render(<SetupPage />)
    await user.type(screen.getByLabelText(/^password$/i), 'StrongPass1!')
    await user.type(screen.getByLabelText(/confirm password/i), 'StrongPass1!')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => {
      expect(screen.getByText(RECOVERY_KEY)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /copy/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument()
  })

  it('shows step 3 — confirmation input after "I\'ve saved it" click', async () => {
    const user = userEvent.setup()
    ;(mockSetup as jest.Mock).mockResolvedValue({
      data: { data: { recovery_key: RECOVERY_KEY } },
    })
    render(<SetupPage />)
    await user.type(screen.getByLabelText(/^password$/i), 'StrongPass1!')
    await user.type(screen.getByLabelText(/confirm password/i), 'StrongPass1!')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(screen.getByText(RECOVERY_KEY)).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /i've saved it/i }))
    await waitFor(() => {
      expect(screen.getByLabelText(/last 8 characters/i)).toBeInTheDocument()
    })
  })

  it('step 3 confirms and redirects to /journey on success', async () => {
    const user = userEvent.setup()
    ;(mockSetup as jest.Mock).mockResolvedValue({
      data: { data: { recovery_key: RECOVERY_KEY } },
    })
    ;(mockSetupConfirm as jest.Mock).mockResolvedValue({})
    render(<SetupPage />)
    // Step 1
    await user.type(screen.getByLabelText(/^password$/i), 'StrongPass1!')
    await user.type(screen.getByLabelText(/confirm password/i), 'StrongPass1!')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(screen.getByText(RECOVERY_KEY)).toBeInTheDocument())
    // Step 2
    await user.click(screen.getByRole('button', { name: /i've saved it/i }))
    await waitFor(() => expect(screen.getByLabelText(/last 8 characters/i)).toBeInTheDocument())
    // Step 3 — last 8 chars of RECOVERY_KEY are "1234-5678"
    await user.type(screen.getByLabelText(/last 8 characters/i), '1234-5678')
    await user.click(screen.getByRole('button', { name: /confirm/i }))
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/journey')
    })
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=setup --watchAll=false
```

Expected: FAIL — `Cannot find module '@/app/(auth)/setup/page'`

- [ ] **Step 3: Create app/(auth)/setup/page.tsx**

```tsx
// frontend/app/(auth)/setup/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { Eye, EyeOff, Copy, Download, Check } from 'lucide-react'
import { setup, setupConfirm } from '@/lib/api/auth'

type Step = 1 | 2 | 3

interface PasswordForm {
  password: string
  confirmPassword: string
}

interface ConfirmForm {
  confirmation: string
}

function passwordStrength(pw: string): { label: string; level: 0 | 1 | 2 | 3 } {
  if (!pw) return { label: '', level: 0 }
  let score = 0
  if (pw.length >= 8) score++
  if (/[A-Z]/.test(pw)) score++
  if (/[0-9]/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++
  if (score <= 1) return { label: 'Weak', level: 1 }
  if (score <= 2) return { label: 'Fair', level: 2 }
  return { label: 'Strong', level: 3 }
}

const strengthColor: Record<number, string> = {
  1: 'bg-risk-high',
  2: 'bg-review',
  3: 'bg-ready',
}

export default function SetupPage() {
  const router = useRouter()
  const [step, setStep] = useState<Step>(1)
  const [recoveryKey, setRecoveryKey] = useState('')
  const [copied, setCopied] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register: registerPw,
    handleSubmit: handlePwSubmit,
    watch,
    formState: { isSubmitting: isPwSubmitting },
  } = useForm<PasswordForm>()

  const {
    register: registerConfirm,
    handleSubmit: handleConfirmSubmit,
    formState: { isSubmitting: isConfirmSubmitting },
  } = useForm<ConfirmForm>()

  const passwordValue = watch('password', '')
  const strength = passwordStrength(passwordValue)

  async function onPasswordSubmit({ password, confirmPassword }: PasswordForm) {
    if (password !== confirmPassword) {
      setServerError('Passwords do not match.')
      return
    }
    setServerError(null)
    try {
      const res = await setup(password)
      setRecoveryKey(res.data.data.recovery_key)
      setStep(2)
    } catch (err: unknown) {
      const msg = (
        err as { response?: { data?: { detail?: { message?: string } } } }
      )?.response?.data?.detail?.message
      setServerError(msg ?? 'Setup failed. Please try again.')
    }
  }

  async function onConfirmSubmit({ confirmation }: ConfirmForm) {
    setServerError(null)
    try {
      await setupConfirm(confirmation)
      router.push('/journey')
    } catch (err: unknown) {
      const msg = (
        err as { response?: { data?: { detail?: { message?: string } } } }
      )?.response?.data?.detail?.message
      setServerError(msg ?? 'Confirmation failed. Check the last 8 characters.')
    }
  }

  function copyKey() {
    navigator.clipboard.writeText(recoveryKey).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  function downloadKey() {
    const blob = new Blob([recoveryKey], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'tax-return-ai-recovery-key.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="font-display text-3xl font-semibold text-text-primary mb-2">
          Tax Return AI
        </h1>

        {/* Step indicators */}
        <div className="flex gap-2 mb-8">
          {([1, 2, 3] as Step[]).map((s) => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full ${
                s <= step ? 'bg-accent' : 'bg-border'
              }`}
            />
          ))}
        </div>

        {/* ── Step 1: Set password ── */}
        {step === 1 && (
          <form onSubmit={handlePwSubmit(onPasswordSubmit)} className="space-y-4">
            <h2 className="font-ui text-xl font-semibold text-text-primary">
              Set your password
            </h2>
            <p className="font-ui text-sm text-text-muted">
              This password protects your workspace. Choose something strong.
            </p>

            <div>
              <label htmlFor="password" className="block font-ui text-sm font-medium text-text-body mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoFocus
                  autoComplete="new-password"
                  className="w-full px-4 py-3 rounded-md border border-border bg-surface font-ui text-base text-text-primary focus:outline-none focus:shadow-focus"
                  {...registerPw('password', { required: true })}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-body"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {passwordValue && (
                <div className="mt-2" data-testid="strength-indicator">
                  <div className="flex gap-1 mb-1">
                    {[1, 2, 3].map((level) => (
                      <div
                        key={level}
                        className={`h-1 flex-1 rounded-full ${
                          strength.level >= level
                            ? strengthColor[strength.level]
                            : 'bg-border'
                        }`}
                      />
                    ))}
                  </div>
                  <p className="font-ui text-xs text-text-muted">{strength.label}</p>
                </div>
              )}
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block font-ui text-sm font-medium text-text-body mb-1">
                Confirm password
              </label>
              <input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                className="w-full px-4 py-3 rounded-md border border-border bg-surface font-ui text-base text-text-primary focus:outline-none focus:shadow-focus"
                {...registerPw('confirmPassword', { required: true })}
              />
            </div>

            {serverError && (
              <p role="alert" className="font-ui text-sm text-risk-high">
                {serverError}
              </p>
            )}

            <button
              type="submit"
              disabled={isPwSubmitting}
              className="w-full py-3 rounded-md bg-accent hover:bg-accent-hover text-white font-ui font-medium text-base disabled:opacity-50 transition-colors"
            >
              {isPwSubmitting ? 'Setting up…' : 'Continue'}
            </button>
          </form>
        )}

        {/* ── Step 2: Show recovery key ── */}
        {step === 2 && (
          <div className="space-y-4">
            <h2 className="font-ui text-xl font-semibold text-text-primary">
              Save your recovery key
            </h2>
            <p className="font-ui text-sm text-text-muted">
              If you forget your password, this key is the only way to recover your
              workspace. Save it somewhere safe — we cannot show it again.
            </p>

            <div className="bg-surface-raised border border-border rounded-md p-4">
              <p className="font-mono text-sm text-text-primary break-all">{recoveryKey}</p>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={copyKey}
                className="flex-1 flex items-center justify-center gap-2 py-2 rounded-md border border-border font-ui text-sm text-text-body hover:bg-accent-soft transition-colors"
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
              <button
                type="button"
                onClick={downloadKey}
                className="flex-1 flex items-center justify-center gap-2 py-2 rounded-md border border-border font-ui text-sm text-text-body hover:bg-accent-soft transition-colors"
              >
                <Download size={16} />
                Download
              </button>
            </div>

            <button
              type="button"
              onClick={() => setStep(3)}
              className="w-full py-3 rounded-md bg-accent hover:bg-accent-hover text-white font-ui font-medium text-base transition-colors"
            >
              I&apos;ve saved it
            </button>
          </div>
        )}

        {/* ── Step 3: Confirm last 8 chars ── */}
        {step === 3 && (
          <form onSubmit={handleConfirmSubmit(onConfirmSubmit)} className="space-y-4">
            <h2 className="font-ui text-xl font-semibold text-text-primary">
              Confirm your recovery key
            </h2>
            <p className="font-ui text-sm text-text-muted">
              Enter the last 8 characters of your recovery key to confirm you&apos;ve
              saved it correctly.
            </p>

            <div>
              <label htmlFor="confirmation" className="block font-ui text-sm font-medium text-text-body mb-1">
                Last 8 characters
              </label>
              <input
                id="confirmation"
                type="text"
                autoFocus
                placeholder="XXXX-XXXX"
                className="w-full px-4 py-3 rounded-md border border-border bg-surface font-mono text-base text-text-primary focus:outline-none focus:shadow-focus"
                {...registerConfirm('confirmation', { required: true })}
              />
            </div>

            {serverError && (
              <p role="alert" className="font-ui text-sm text-risk-high">
                {serverError}
              </p>
            )}

            <button
              type="submit"
              disabled={isConfirmSubmitting}
              className="w-full py-3 rounded-md bg-accent hover:bg-accent-hover text-white font-ui font-medium text-base disabled:opacity-50 transition-colors"
            >
              {isConfirmSubmitting ? 'Confirming…' : 'Confirm'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=setup --watchAll=false
```

Expected: `PASS __tests__/setup.test.tsx` — 5 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/__tests__/setup.test.tsx "frontend/app/(auth)/setup/page.tsx"
git commit -m "feat: implement 3-step setup page — password, recovery key, confirmation"
```

---

## Task 9: Dashboard layout — real sidebar + mobile tabs (TDD)

**Files:**
- Create: `frontend/__tests__/dashboard-layout.test.tsx`
- Modify: `frontend/app/(dashboard)/layout.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
// frontend/__tests__/dashboard-layout.test.tsx
import { render, screen } from '@testing-library/react'
import DashboardLayout from '@/app/(dashboard)/layout'

jest.mock('next/navigation', () => ({
  usePathname: () => '/readiness',
  useRouter: () => ({ replace: jest.fn(), push: jest.fn() }),
}))

jest.mock('@/lib/hooks/useAuth', () => ({
  useAuth: jest.fn().mockReturnValue({ isAuthenticated: true }),
}))

jest.mock('@/lib/stores/workspace.store', () => ({
  default: () => ({
    workspaceId: 'ws-1',
    financialYear: '2024-25',
    isAuthenticated: true,
    isUnlocked: true,
    setWorkspace: jest.fn(),
    setAuthenticated: jest.fn(),
    setUnlocked: jest.fn(),
  }),
}))

describe('DashboardLayout', () => {
  it('renders the sidebar nav with core navigation items', () => {
    render(<DashboardLayout><div>content</div></DashboardLayout>)
    expect(screen.getByText('Tax Journey')).toBeInTheDocument()
    expect(screen.getByText('Tax Readiness')).toBeInTheDocument()
    expect(screen.getByText('Review')).toBeInTheDocument()
    expect(screen.getByText('Export Review Pack')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('marks the active nav item based on pathname', () => {
    render(<DashboardLayout><div>content</div></DashboardLayout>)
    const readinessLink = screen.getByRole('link', { name: /tax readiness/i })
    expect(readinessLink).toHaveAttribute('data-active', 'true')
  })

  it('renders children in the content area', () => {
    render(<DashboardLayout><div>hello content</div></DashboardLayout>)
    expect(screen.getByText('hello content')).toBeInTheDocument()
  })

  it('shows FY indicator in the sidebar', () => {
    render(<DashboardLayout><div>x</div></DashboardLayout>)
    expect(screen.getByText(/2024-25/)).toBeInTheDocument()
  })

  it('renders mobile bottom tab bar with primary 5 items', () => {
    render(<DashboardLayout><div>x</div></DashboardLayout>)
    // Bottom tab bar is in DOM (hidden via CSS on desktop — still present for screen readers)
    const bottomTabNav = screen.getByRole('navigation', { name: /mobile/i })
    expect(bottomTabNav).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=dashboard-layout --watchAll=false
```

Expected: FAIL — layout is just a pass-through, none of the assertions pass.

- [ ] **Step 3: Rewrite app/(dashboard)/layout.tsx**

```tsx
// frontend/app/(dashboard)/layout.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Map,
  BarChart2,
  SearchX,
  Briefcase,
  Scissors,
  TrendingUp,
  FolderOpen,
  CheckSquare,
  Package,
  Settings,
  MoreHorizontal,
} from 'lucide-react'
import { useAuth } from '@/lib/hooks/useAuth'
import useWorkspaceStore from '@/lib/stores/workspace.store'

interface NavItem {
  label: string
  href: string
  icon: React.ComponentType<{ size?: number; className?: string }>
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Tax Journey', href: '/journey', icon: Map },
  { label: 'Tax Readiness', href: '/readiness', icon: BarChart2 },
  { label: 'Missing Evidence', href: '/readiness/missing', icon: SearchX },
  { label: 'Income', href: '/review?filter=income', icon: Briefcase },
  { label: 'Deductions', href: '/review?filter=deductions', icon: Scissors },
  { label: 'Investments', href: '/review?filter=investments', icon: TrendingUp },
  { label: 'Supporting Evidence', href: '/evidence', icon: FolderOpen },
  { label: 'Review', href: '/review', icon: CheckSquare },
  { label: 'Export Review Pack', href: '/export', icon: Package },
  { label: 'Settings', href: '/settings', icon: Settings },
]

const MOBILE_TABS: NavItem[] = [
  { label: 'Tax Journey', href: '/journey', icon: Map },
  { label: 'Readiness', href: '/readiness', icon: BarChart2 },
  { label: 'Review', href: '/review', icon: CheckSquare },
  { label: 'Evidence', href: '/evidence', icon: FolderOpen },
  { label: 'More', href: '#more', icon: MoreHorizontal },
]

function SidebarNavItem({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon
  return (
    <Link
      href={item.href}
      data-active={active ? 'true' : undefined}
      className={`
        flex items-center gap-3 px-4 py-2 rounded-sm font-ui text-sm font-medium transition-colors
        ${
          active
            ? 'border-l-[3px] border-accent bg-accent-soft text-accent'
            : 'text-text-muted hover:bg-accent-soft hover:text-text-body'
        }
      `}
    >
      <Icon size={16} className="shrink-0" />
      {item.label}
    </Link>
  )
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const { financialYear } = useWorkspaceStore()

  // Triggers session check + redirects to /login or /setup if needed
  useAuth()

  return (
    <div className="flex min-h-screen bg-canvas">
      {/* ── Desktop sidebar ─────────────────────────────────────── */}
      <aside className="hidden md:flex flex-col w-60 shrink-0 bg-surface border-r border-border">
        {/* Logo */}
        <div className="px-4 py-5 border-b border-border">
          <span className="font-display text-xl font-semibold text-text-primary">
            Tax Return AI
          </span>
        </div>

        {/* FY switcher */}
        {financialYear && (
          <div className="px-4 py-3 border-b border-border">
            <button
              type="button"
              className="font-ui text-xs text-text-muted hover:text-text-body flex items-center gap-1"
            >
              FY {financialYear} ▾
            </button>
          </div>
        )}

        {/* Nav items */}
        <nav className="flex-1 py-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map((item) => (
            <SidebarNavItem
              key={item.href}
              item={item}
              active={pathname === item.href || pathname.startsWith(item.href + '?')}
            />
          ))}
        </nav>
      </aside>

      {/* ── Main content ─────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0 pb-16 md:pb-0">
        <div className="flex-1 max-w-[880px] w-full mx-auto px-4 py-6">
          {children}
        </div>
      </main>

      {/* ── Mobile bottom tab bar ────────────────────────────────── */}
      <nav
        aria-label="Mobile navigation"
        className="md:hidden fixed bottom-0 inset-x-0 bg-surface border-t border-border flex"
      >
        {MOBILE_TABS.map((item) => {
          const Icon = item.icon
          const active = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex-1 flex flex-col items-center justify-center py-2 gap-0.5 font-ui text-xs transition-colors ${
                active ? 'text-accent' : 'text-text-muted'
              }`}
            >
              <Icon size={20} />
              {item.label}
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --testPathPattern=dashboard-layout --watchAll=false
```

Expected: `PASS __tests__/dashboard-layout.test.tsx` — 5 tests passing.

- [ ] **Step 5: Commit**

```bash
git add frontend/__tests__/dashboard-layout.test.tsx "frontend/app/(dashboard)/layout.tsx"
git commit -m "feat: implement dashboard layout — sidebar nav, FY switcher, mobile bottom tabs"
```

---

## Task 10: Full test suite — verify all Phase 1 tests pass

- [ ] **Step 1: Run all frontend tests**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -e CI=true frontend npm test -- --watchAll=false
```

Expected: All tests pass. Test files:
- `__tests__/workspace-store.test.ts` — 4 tests
- `__tests__/auth-api.test.ts` — 7 tests
- `__tests__/useAuth.test.tsx` — 3 tests
- `__tests__/login.test.tsx` — 6 tests
- `__tests__/setup.test.tsx` — 5 tests
- `__tests__/dashboard-layout.test.tsx` — 5 tests

Total: **30 frontend tests passing**

- [ ] **Step 2: Final commit if any loose files remain**

```bash
git status
# If any untracked changes:
git add -p
git commit -m "chore: m10 phase 1 — layout shell and auth pages complete"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Task |
|-------------|------|
| app/layout.tsx — React Query provider | Task 5 |
| app/layout.tsx — font loading | Task 5 (globals.css already imports Google Fonts) |
| app/(auth)/login/page.tsx — real implementation | Task 7 |
| login: password show/hide | Task 7 |
| login: error on wrong password | Task 7 |
| login: redirect /readiness on success | Task 7 |
| login: redirect /setup on 403 setup_not_confirmed | Task 7 |
| app/(auth)/setup/page.tsx | Task 8 |
| setup: 3 steps (password, recovery key, confirm) | Task 8 |
| setup: password strength indicator | Task 8 |
| setup: copy + download recovery key | Task 8 |
| setup: redirect /journey on complete | Task 8 |
| app/(dashboard)/layout.tsx — sidebar 240px | Task 9 |
| sidebar: active state terracotta border | Task 9 |
| sidebar: FY switcher | Task 9 |
| mobile: bottom tab bar | Task 9 |
| lib/stores/workspace.store.ts — full interface | Task 2 |
| lib/api/auth.ts — all 7 functions | Task 3 |
| lib/hooks/useAuth.ts | Task 6 |
| next-pwa configured | Task 1 |
| Disclaimer text correct | Task 4 |

**Placeholder scan:** None found. Every step has exact code.

**Type consistency:** `SessionData` defined in Task 3 (types.ts), used in `useAuth.ts` (Task 6) and `login/page.tsx` (Task 7) — consistent.

**Explicit DO NOT build (confirmed absent from this plan):**
- No readiness numbers, review cards, or dashboard page content
- No Interview UI
- No document upload
- No data fetching beyond auth session check
