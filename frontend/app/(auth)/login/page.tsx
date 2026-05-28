'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import axios from 'axios'
import { Eye, EyeOff } from 'lucide-react'
import { getSession, login } from '@/lib/api/auth'
import useWorkspaceStore from '@/lib/stores/workspace.store'

interface LoginForm {
  password: string
}

export default function LoginPage() {
  const router = useRouter()
  const { setWorkspace, setAuthenticated } = useWorkspaceStore()
  const [showPassword, setShowPassword] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  useEffect(() => {
    getSession()
      .then((res) => {
        const data = res.data.data
        if (data.setup_confirmed === false || data.setup_required) {
          router.push('/setup')
          return
        }
        if (data.setup_confirmed === true) {
          router.push('/journey')
        }
      })
      .catch(() => {
        // Not authenticated — stay on login page
      })
  }, [router])

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, errors },
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
      console.error(err)
      const detail = (
        err as { response?: { data?: { detail?: { error_code?: string; message?: string } } } }
      )?.response?.data?.detail
      if (detail?.error_code === 'setup_not_confirmed') {
        router.push('/setup')
        return
      }
      if (axios.isAxiosError(err) && err.response && err.response.status >= 500) {
        setServerError('Something went wrong. Please try again.')
      } else if (detail?.error_code === 'invalid_password') {
        setServerError('Incorrect password. Please try again.')
      } else if (detail) {
        setServerError(detail.message ?? 'Login failed. Check your password.')
      } else {
        setServerError('Connection error. Please check your network and try again.')
      }
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
                {...register('password', { required: 'Password is required' })}
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
            {errors.password && (
              <p role="alert" className="font-ui text-sm text-risk-high mt-1">
                {errors.password.message}
              </p>
            )}
          </div>

          {serverError && (
            <p role="alert" className="font-ui text-sm text-risk-high">
              {serverError}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 rounded-md bg-accent hover:bg-accent-hover text-white font-ui font-medium text-base disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <svg
                  className="animate-spin h-4 w-4 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 22 6.477 22 12h-4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.384 3 6.846l3-2.647z"
                  />
                </svg>
                Logging in…
              </>
            ) : (
              'Log in'
            )}
          </button>

          <div className="text-center">
            <Link
              href="/recover"
              className="font-ui text-sm text-text-muted hover:text-text-body"
            >
              Forgot password?
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
