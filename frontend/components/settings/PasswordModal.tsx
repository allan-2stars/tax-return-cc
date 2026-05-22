'use client'
import { useState } from 'react'

interface Props {
  title: string
  description?: string
  confirmLabel?: string
  pending?: boolean
  error?: string | null
  onConfirm: (password: string) => void
  onCancel: () => void
}

export default function PasswordModal({
  title,
  description,
  confirmLabel = 'Confirm',
  pending,
  error,
  onConfirm,
  onCancel,
}: Props) {
  const [password, setPassword] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onConfirm(password)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm mx-4 bg-surface rounded-xl border border-border p-6 space-y-4">
        <h2 className="font-display text-lg font-semibold text-text-primary">{title}</h2>
        {description && (
          <p className="text-sm font-ui text-text-muted">{description}</p>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="modal-password"
              className="text-sm font-ui text-text-body block mb-1"
            >
              Password
            </label>
            <input
              id="modal-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-border bg-canvas px-3 py-2 text-sm font-ui"
              aria-label="Password"
              autoFocus
              required
            />
          </div>
          {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={pending}
              className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
            >
              {pending ? 'Working…' : confirmLabel}
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="min-h-11 px-4 text-sm font-ui text-text-muted"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
