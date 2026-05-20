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

        {/* Step progress bar */}
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
              If you forget your password, this key is the only way to recover
              your workspace. Save it somewhere safe — we cannot show it again.
            </p>

            <div className="bg-surface-raised border border-border rounded-md p-4">
              <p className="font-mono text-sm text-text-primary break-all">
                {recoveryKey}
              </p>
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
              Enter the last 8 characters of your recovery key to confirm
              you&apos;ve saved it correctly.
            </p>

            <div>
              <label
                htmlFor="confirmation"
                className="block font-ui text-sm font-medium text-text-body mb-1"
              >
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
