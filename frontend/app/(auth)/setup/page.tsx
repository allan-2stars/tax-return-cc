'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import axios from 'axios'
import { Eye, EyeOff, Copy, Download, Check } from 'lucide-react'
import { setup, setupConfirm } from '@/lib/api/auth'
import useWorkspaceStore from '@/lib/stores/workspace.store'

type Step = 0 | 1 | 2 | 3

interface PasswordForm {
  password: string
  confirmPassword: string
}

interface ConfirmForm {
  confirmation: string
}

type StrengthLevel = 0 | 1 | 2 | 3 | 4

function passwordStrength(pw: string): { label: string; level: StrengthLevel } {
  if (!pw) return { label: '', level: 0 }
  const hasLetter = /[A-Za-z]/.test(pw)
  const hasNumber = /[0-9]/.test(pw)
  const isMixed = hasLetter && hasNumber
  if (pw.length >= 16 && isMixed) return { label: 'Strong', level: 4 }
  if (pw.length >= 12 && isMixed) return { label: 'Good', level: 3 }
  if (pw.length >= 8) return { label: 'Fair', level: 2 }
  return { label: 'Weak', level: 1 }
}

const strengthBarColor: Record<number, string> = {
  1: 'bg-risk-high',
  2: 'bg-review',
  3: 'bg-ready',
  4: 'bg-ready',
}

const strengthTextColor: Record<number, string> = {
  1: 'text-risk-high',
  2: 'text-review',
  3: 'text-ready',
  4: 'text-ready',
}

const CONFIRM_FORMAT_RE = /^[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}$/i

function getCurrentFY(): string {
  const now = new Date()
  const year = now.getFullYear()
  return now.getMonth() >= 6
    ? `${year}-${String(year + 1).slice(-2)}`
    : `${year - 1}-${String(year).slice(-2)}`
}

function shiftFY(fy: string, delta: number): string {
  const start = parseInt(fy.split('-')[0]) + delta
  return `${start}-${String(start + 1).slice(-2)}`
}

export default function SetupPage() {
  const router = useRouter()
  const { setWorkspace } = useWorkspaceStore()
  const [step, setStep] = useState<Step>(0)
  const [selectedFY, setSelectedFY] = useState(getCurrentFY())
  const [setupWorkspaceId, setSetupWorkspaceId] = useState('')
  const [recoveryKey, setRecoveryKey] = useState('')
  const [copied, setCopied] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const currentFY = getCurrentFY()
  const fyOptions = [currentFY, shiftFY(currentFY, -1), shiftFY(currentFY, -2)]

  const {
    register: registerPw,
    handleSubmit: handlePwSubmit,
    watch,
    formState: {
      isSubmitting: isPwSubmitting,
      errors: pwErrors,
      touchedFields: pwTouched,
      isSubmitted: pwIsSubmitted,
    },
  } = useForm<PasswordForm>({ mode: 'onTouched' })

  const {
    register: registerConfirm,
    handleSubmit: handleConfirmSubmit,
    watch: watchConfirm,
    formState: { isSubmitting: isConfirmSubmitting, errors: confirmErrors },
  } = useForm<ConfirmForm>({ mode: 'onTouched' })

  const passwordValue = watch('password', '')
  const confirmValue = watchConfirm('confirmation', '')
  const strength = passwordStrength(passwordValue)

  const hasInteracted =
    (pwTouched.password ?? false) ||
    (pwTouched.confirmPassword ?? false) ||
    pwIsSubmitted
  const continueDisabled =
    isPwSubmitting ||
    (hasInteracted && (!!pwErrors.password || !!pwErrors.confirmPassword))

  async function onPasswordSubmit({ password }: PasswordForm) {
    setServerError(null)
    try {
      const res = await setup(password, selectedFY)
      setSetupWorkspaceId(res.data.data.workspace_id ?? '')
      setRecoveryKey(res.data.data.recovery_key)
      setStep(2)
    } catch (err: unknown) {
      console.error(err)
      if (axios.isAxiosError(err)) {
        const errorCode = err.response?.data?.detail?.error_code
        const message = err.response?.data?.detail?.message
        if (errorCode === 'already_setup') {
          router.push('/login')
          return
        }
        setServerError(message ?? 'Setup failed. Please try again.')
      } else {
        setServerError('Connection error. Please check your network.')
      }
    }
  }

  async function onConfirmSubmit({ confirmation }: ConfirmForm) {
    setServerError(null)
    try {
      await setupConfirm(confirmation)
      setWorkspace(setupWorkspaceId, selectedFY)
      router.push('/journey')
    } catch (err: unknown) {
      console.error(err)
      if (axios.isAxiosError(err)) {
        const message = err.response?.data?.detail?.message
        setServerError(message ?? 'Confirmation failed. Check the last key segment.')
      } else {
        setServerError('Connection error. Please check your network.')
      }
    }
  }

  function copyKey() {
    navigator.clipboard
      .writeText(recoveryKey)
      .then(() => {
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      })
      .catch(() => {
        setServerError('Failed to copy to clipboard. Please copy the key manually.')
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

        {step > 0 && (
          <div className="flex gap-2 mb-8">
            {([1, 2, 3] as const).map((s) => (
              <div
                key={s}
                className={`h-1 flex-1 rounded-full ${s <= step ? 'bg-accent' : 'bg-border'}`}
              />
            ))}
          </div>
        )}

        {/* ── Step 0: Select financial year ── */}
        {step === 0 && (
          <div className="space-y-4">
            <h2 className="font-ui text-xl font-semibold text-text-primary">
              Which financial year are you preparing?
            </h2>
            <div className="space-y-2">
              {fyOptions.map((fy) => (
                <button
                  key={fy}
                  type="button"
                  onClick={() => {
                    setSelectedFY(fy)
                    setStep(1)
                  }}
                  className={`w-full text-left px-4 py-3 rounded-md border font-ui text-sm font-medium transition-colors ${
                    selectedFY === fy
                      ? 'border-accent text-accent'
                      : 'border-border text-text-body hover:border-accent'
                  }`}
                >
                  FY {fy}
                </button>
              ))}
            </div>
          </div>
        )}

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
                  autoComplete="new-password"
                  className="w-full px-4 py-3 rounded-md border border-border bg-surface font-ui text-base text-text-primary focus:outline-none focus:shadow-focus"
                  {...registerPw('password', {
                    required: 'Password is required',
                    minLength: {
                      value: 12,
                      message: 'Password must be at least 12 characters',
                    },
                    validate: {
                      hasLetter: (v) =>
                        /[A-Za-z]/.test(v) || 'Password must contain at least one letter',
                      hasNumber: (v) =>
                        /[0-9]/.test(v) || 'Password must contain at least one number',
                    },
                  })}
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
                            ? strengthBarColor[strength.level]
                            : 'bg-border'
                        }`}
                      />
                    ))}
                  </div>
                  <p
                    className={`font-ui text-xs ${
                      strengthTextColor[strength.level] ?? 'text-text-muted'
                    }`}
                  >
                    {strength.label}
                  </p>
                </div>
              )}
              {pwErrors.password && (
                <p role="alert" className="font-ui text-sm text-risk-high mt-1">
                  {pwErrors.password.message}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="confirmPassword"
                className="block font-ui text-sm font-medium text-text-body mb-1"
              >
                Confirm password
              </label>
              <input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                className="w-full px-4 py-3 rounded-md border border-border bg-surface font-ui text-base text-text-primary focus:outline-none focus:shadow-focus"
                {...registerPw('confirmPassword', {
                  required: 'Please confirm your password',
                  validate: (v) =>
                    v === watch('password') || 'Passwords do not match.',
                })}
              />
              {pwErrors.confirmPassword && (
                <p role="alert" className="font-ui text-sm text-risk-high mt-1">
                  {pwErrors.confirmPassword.message}
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
              disabled={continueDisabled}
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
              If you forget your password, this key is the only way to recover
              your workspace. Save it somewhere safe — we cannot show it again.
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

            {serverError && (
              <p role="alert" className="font-ui text-sm text-risk-high">
                {serverError}
              </p>
            )}

            <button
              type="button"
              onClick={() => {
                setServerError(null)
                setStep(3)
              }}
              className="w-full py-3 rounded-md bg-accent hover:bg-accent-hover text-white font-ui font-medium text-base transition-colors"
            >
              I&apos;ve saved it
            </button>
          </div>
        )}

        {/* ── Step 3: Confirm last key segment ── */}
        {step === 3 && (
          <form onSubmit={handleConfirmSubmit(onConfirmSubmit)} className="space-y-4">
            <h2 className="font-ui text-xl font-semibold text-text-primary">
              Confirm your recovery key
            </h2>
            <p className="font-ui text-sm text-text-muted">
              Enter the last segment of your recovery key to confirm you&apos;ve saved it
              correctly.
            </p>

            <div>
              <label
                htmlFor="confirmation"
                className="block font-ui text-sm font-medium text-text-body mb-1"
              >
                Last key segment (XXXX-XXXX)
              </label>
              <input
                id="confirmation"
                type="text"
                autoFocus
                placeholder="XXXX-XXXX"
                className="w-full px-4 py-3 rounded-md border border-border bg-surface font-mono text-base text-text-primary focus:outline-none focus:shadow-focus"
                {...registerConfirm('confirmation', {
                  required:
                    'Please enter the last 8 characters of your recovery key',
                  pattern: {
                    value: CONFIRM_FORMAT_RE,
                    message: 'Format should be XXXX-XXXX',
                  },
                })}
              />
              {confirmErrors.confirmation && (
                <p role="alert" className="font-ui text-sm text-risk-high mt-1">
                  {confirmErrors.confirmation.message}
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
              disabled={isConfirmSubmitting || !CONFIRM_FORMAT_RE.test(confirmValue)}
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
