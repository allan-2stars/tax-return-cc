'use client'
import { useState } from 'react'
import { createWorkspace } from '@/lib/api/settings'
import type { CreateWorkspaceResult } from '@/lib/api/types'
import { computeNextFY } from '@/lib/utils/fy'

interface Props {
  currentFY: string
  onSuccess: (ws: CreateWorkspaceResult) => void
  onCancel: () => void
}

export default function NewFYModal({ currentFY, onSuccess, onCancel }: Props) {
  const [name, setName] = useState('My Tax Return')
  const [fy, setFy] = useState(() => computeNextFY(currentFY))
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setError('Name is required.')
      return
    }
    setPending(true)
    setError(null)
    try {
      const res = await createWorkspace(name.trim(), fy)
      onSuccess(res.data.data)
    } catch {
      setError('Could not create workspace. Please try again.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center px-4"
    >
      <div className="w-full max-w-sm bg-canvas rounded-lg shadow-lg p-6 space-y-4">
        <h2 className="font-display text-xl font-semibold text-text-primary">
          New financial year
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="new-fy-name" className="text-sm font-ui text-text-body block mb-1">
              Workspace name
            </label>
            <input
              id="new-fy-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="Workspace name"
              required
            />
          </div>

          <div>
            <label htmlFor="new-fy-year" className="text-sm font-ui text-text-body block mb-1">
              Financial year
            </label>
            <input
              id="new-fy-year"
              type="text"
              value={fy}
              onChange={(e) => setFy(e.target.value)}
              pattern="\d{4}-\d{2}"
              placeholder="YYYY-YY"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
              aria-label="Financial year"
              required
            />
          </div>

          {error && <p className="text-sm font-ui text-risk-high">{error}</p>}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={pending}
              className="flex-1 min-h-11 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
            >
              {pending ? 'Creating…' : 'Create'}
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
