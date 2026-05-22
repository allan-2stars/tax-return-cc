'use client'
import { useState } from 'react'
import { changePassword, regenerateRecoveryKey } from '@/lib/api/settings'
import PasswordModal from './PasswordModal'

type AutoLock = '15' | '30' | '60' | 'never'

const AUTO_LOCK_OPTIONS: { value: AutoLock; label: string }[] = [
  { value: '15', label: '15 min' },
  { value: '30', label: '30 min' },
  { value: '60', label: '1 hour' },
  { value: 'never', label: 'Never' },
]

export default function SecurityTab() {
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwPending, setPwPending] = useState(false)
  const [pwSuccess, setPwSuccess] = useState(false)

  const [autoLock, setAutoLock] = useState<AutoLock>('15')
  const [showRegenModal, setShowRegenModal] = useState(false)
  const [regenKey, setRegenKey] = useState<string | null>(null)
  const [regenError, setRegenError] = useState<string | null>(null)
  const [regenPending, setRegenPending] = useState(false)

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault()
    setPwError(null)
    if (newPw !== confirmPw) {
      setPwError('New passwords do not match.')
      return
    }
    setPwPending(true)
    try {
      await changePassword(currentPw, newPw)
      setPwSuccess(true)
      setCurrentPw('')
      setNewPw('')
      setConfirmPw('')
      setTimeout(() => setPwSuccess(false), 3000)
    } catch {
      setPwError('Incorrect current password.')
    } finally {
      setPwPending(false)
    }
  }

  async function handleRegenConfirm(password: string) {
    setRegenError(null)
    setRegenPending(true)
    try {
      const res = await regenerateRecoveryKey(password)
      setRegenKey(res.data.data.recovery_key)
      setShowRegenModal(false)
    } catch {
      setRegenError('Incorrect password.')
    } finally {
      setRegenPending(false)
    }
  }

  return (
    <div className="space-y-8">
      <section className="space-y-4 max-w-sm">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Change password
        </h2>
        <form onSubmit={handleChangePassword} className="space-y-3">
          <div>
            <label htmlFor="current-pw" className="text-sm font-ui text-text-body block mb-1">
              Current password
            </label>
            <input
              id="current-pw"
              type="password"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="Current password"
              required
            />
          </div>
          <div>
            <label htmlFor="new-pw" className="text-sm font-ui text-text-body block mb-1">
              New password
            </label>
            <input
              id="new-pw"
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="New password"
              required
            />
          </div>
          <div>
            <label htmlFor="confirm-pw" className="text-sm font-ui text-text-body block mb-1">
              Confirm new password
            </label>
            <input
              id="confirm-pw"
              type="password"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="Confirm new password"
              required
            />
          </div>
          {pwError && <p className="text-sm font-ui text-risk-high">{pwError}</p>}
          {pwSuccess && <p className="text-sm font-ui text-ready">Password changed.</p>}
          <button
            type="submit"
            disabled={pwPending}
            className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
          >
            {pwPending ? 'Changing…' : 'Change password'}
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
            <p className="text-xs font-ui text-text-muted">
              New recovery key — store this somewhere safe:
            </p>
            <p className="font-mono text-sm text-text-primary break-all">{regenKey}</p>
            <button
              type="button"
              className="text-xs font-ui text-text-muted underline"
              onClick={() => setRegenKey(null)}
            >
              I&apos;ve saved it
            </button>
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
