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
