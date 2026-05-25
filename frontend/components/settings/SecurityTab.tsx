'use client'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import axios from 'axios'
import { Copy, Check } from 'lucide-react'
import { changePassword, regenerateRecoveryKey } from '@/lib/api/settings'
import PasswordModal from './PasswordModal'

type AutoLock = '15' | '30' | '60' | 'never'

interface ChangePasswordForm {
  currentPassword: string
  newPassword: string
  confirmPassword: string
}

const AUTO_LOCK_OPTIONS: { value: AutoLock; label: string }[] = [
  { value: '15', label: '15 min' },
  { value: '30', label: '30 min' },
  { value: '60', label: '1 hour' },
  { value: 'never', label: 'Never' },
]

export default function SecurityTab() {
  const [autoLock, setAutoLock] = useState<AutoLock>('15')
  const [pwSuccess, setPwSuccess] = useState(false)
  const [pwFormError, setPwFormError] = useState<string | null>(null)

  const [showRegenModal, setShowRegenModal] = useState(false)
  const [regenKey, setRegenKey] = useState<string | null>(null)
  const [regenError, setRegenError] = useState<string | null>(null)
  const [regenPending, setRegenPending] = useState(false)
  const [regenCopied, setRegenCopied] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: {
      errors,
      isSubmitting,
      touchedFields,
      isSubmitted,
    },
  } = useForm<ChangePasswordForm>({ mode: 'onTouched' })

  const newPasswordValue = watch('newPassword', '')
  const currentPasswordValue = watch('currentPassword', '')

  const hasInteracted =
    Object.keys(touchedFields).length > 0 || isSubmitted
  const submitDisabled =
    isSubmitting ||
    (hasInteracted && (!!errors.currentPassword || !!errors.newPassword || !!errors.confirmPassword))

  async function onChangePassword(data: ChangePasswordForm) {
    setPwFormError(null)
    try {
      await changePassword(data.currentPassword, data.newPassword)
      setPwSuccess(true)
      reset()
    } catch (err: unknown) {
      console.error(err)
      const detail = (
        err as { response?: { data?: { detail?: { error_code?: string; message?: string } } } }
      )?.response?.data?.detail
      if (detail?.error_code === 'invalid_password') {
        setPwFormError('Current password is incorrect.')
      } else if (detail?.message) {
        setPwFormError(detail.message)
      } else {
        setPwFormError('Something went wrong. Please try again.')
      }
    }
  }

  async function handleRegenConfirm(password: string) {
    setRegenError(null)
    setRegenPending(true)
    try {
      const res = await regenerateRecoveryKey(password)
      setRegenKey(res.data.data.recovery_key)
      setShowRegenModal(false)
    } catch (err: unknown) {
      console.error(err)
      const detail = (
        err as { response?: { data?: { detail?: { error_code?: string; message?: string } } } }
      )?.response?.data?.detail
      if (detail?.error_code === 'invalid_password') {
        setRegenError('Incorrect password.')
      } else {
        setRegenError('Something went wrong. Please try again.')
      }
    } finally {
      setRegenPending(false)
    }
  }

  function copyRegenKey() {
    if (!regenKey) return
    navigator.clipboard.writeText(regenKey).then(() => {
      setRegenCopied(true)
      setTimeout(() => setRegenCopied(false), 2000)
    })
  }

  return (
    <div className="space-y-8">
      <section className="space-y-4 max-w-sm">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Change password
        </h2>
        <form onSubmit={handleSubmit(onChangePassword)} className="space-y-3">
          <div>
            <label htmlFor="current-pw" className="text-sm font-ui text-text-body block mb-1">
              Current password
            </label>
            <input
              id="current-pw"
              type="password"
              autoComplete="current-password"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="Current password"
              {...register('currentPassword', {
                required: 'Current password is required',
              })}
            />
            {errors.currentPassword && (
              <p className="text-sm font-ui text-risk-high mt-1">
                {errors.currentPassword.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="new-pw" className="text-sm font-ui text-text-body block mb-1">
              New password
            </label>
            <input
              id="new-pw"
              type="password"
              autoComplete="new-password"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="New password"
              {...register('newPassword', {
                required: 'New password is required',
                minLength: {
                  value: 12,
                  message: 'Password must be at least 12 characters',
                },
                validate: (v) =>
                  v !== currentPasswordValue ||
                  'New password must be different from current password',
              })}
            />
            {errors.newPassword && (
              <p className="text-sm font-ui text-risk-high mt-1">
                {errors.newPassword.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="confirm-pw" className="text-sm font-ui text-text-body block mb-1">
              Confirm new password
            </label>
            <input
              id="confirm-pw"
              type="password"
              autoComplete="new-password"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="Confirm new password"
              {...register('confirmPassword', {
                required: 'Please confirm your new password',
                validate: (v) =>
                  v === newPasswordValue || 'Passwords do not match.',
              })}
            />
            {errors.confirmPassword && (
              <p className="text-sm font-ui text-risk-high mt-1">
                {errors.confirmPassword.message}
              </p>
            )}
          </div>

          {pwFormError && (
            <p className="text-sm font-ui text-risk-high">{pwFormError}</p>
          )}
          {pwSuccess && (
            <p className="text-sm font-ui text-ready">Password changed successfully.</p>
          )}

          <button
            type="submit"
            disabled={submitDisabled}
            className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50 flex items-center gap-2"
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
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 22 6.477 22 12h-4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.384 3 6.846l3-2.647z" />
                </svg>
                Changing…
              </>
            ) : (
              'Change password'
            )}
          </button>
        </form>
      </section>

      <section className="space-y-3 max-w-sm">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Recovery key
        </h2>
        <p className="text-sm font-ui text-text-muted">
          Recovery keys cannot be retrieved after creation.
          Generate a new one if you&apos;ve lost yours.
        </p>
        {regenKey && (
          <div className="rounded-md border border-border bg-surface p-3 space-y-2">
            <p className="text-xs font-ui text-risk-high font-medium">
              Save this now — it cannot be retrieved again.
            </p>
            <p className="font-mono text-sm text-text-primary break-all">{regenKey}</p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={copyRegenKey}
                className="flex items-center gap-1 text-xs font-ui text-text-body border border-border rounded px-2 py-1 hover:bg-accent-soft transition-colors"
              >
                {regenCopied ? <Check size={12} /> : <Copy size={12} />}
                {regenCopied ? 'Copied' : 'Copy'}
              </button>
              <button
                type="button"
                className="text-xs font-ui text-text-muted underline"
                onClick={() => setRegenKey(null)}
              >
                I&apos;ve saved it
              </button>
            </div>
          </div>
        )}
        <button
          type="button"
          onClick={() => setShowRegenModal(true)}
          className="min-h-11 px-5 rounded-md border border-border text-sm font-ui text-text-body hover:border-accent transition-colors"
        >
          Generate new recovery key
        </button>
      </section>

      <section className="space-y-3 max-w-sm">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Session
        </h2>
        <div>
          <p className="text-sm font-ui text-text-body mb-2">Auto-lock after</p>
          <div className="flex gap-2 flex-wrap">
            {AUTO_LOCK_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setAutoLock(opt.value)}
                className={`px-3 py-1 rounded-full text-sm font-ui border transition-colors ${
                  autoLock === opt.value
                    ? 'border-accent text-accent bg-accent-soft'
                    : 'border-border text-text-muted'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {autoLock === 'never' && (
            <p className="mt-2 text-sm font-ui text-agent bg-review/20 rounded px-3 py-2">
              Not recommended for sensitive tax data
            </p>
          )}
        </div>
      </section>

      {showRegenModal && (
        <PasswordModal
          title="Generate new recovery key"
          description="Enter your password to confirm. Your current recovery key will be invalidated immediately."
          confirmLabel="Generate"
          emptyMessage="Password is required to regenerate recovery key"
          pending={regenPending}
          error={regenError}
          onConfirm={handleRegenConfirm}
          onCancel={() => {
            setShowRegenModal(false)
            setRegenError(null)
          }}
        />
      )}
    </div>
  )
}
