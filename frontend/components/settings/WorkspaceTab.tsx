'use client'
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listWorkspaces, updateWorkspaceName } from '@/lib/api/settings'
import type { WorkspaceInfo } from '@/lib/api/types'
import useWorkspaceStore from '@/lib/stores/workspace.store'

export default function WorkspaceTab() {
  const qc = useQueryClient()
  const { workspaceId, financialYear } = useWorkspaceStore()
  const [nameInput, setNameInput] = useState('')
  const [nameSaved, setNameSaved] = useState(false)
  const [nameInitialized, setNameInitialized] = useState(false)

  const { data: wsData, isLoading } = useQuery({
    queryKey: ['workspaces-list'],
    queryFn: () => listWorkspaces().then((r) => r.data.data),
  })

  useEffect(() => {
    if (wsData && !nameInitialized) {
      const current = wsData.items.find((w: WorkspaceInfo) => w.id === workspaceId)
      if (current) {
        setNameInput(current.name)
        setNameInitialized(true)
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsData])

  const nameMutation = useMutation({
    mutationFn: (name: string) => updateWorkspaceName(workspaceId!, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workspaces-list'] })
      setNameSaved(true)
      setTimeout(() => setNameSaved(false), 2000)
    },
  })

  function handleSaveName(e: React.FormEvent) {
    e.preventDefault()
    nameMutation.mutate(nameInput)
  }

  return (
    <div className="space-y-8">
      <section className="space-y-4">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Workspace details
        </h2>
        <form onSubmit={handleSaveName} className="space-y-3 max-w-sm">
          <div>
            <label
              htmlFor="ws-name"
              className="text-sm font-ui text-text-body block mb-1"
            >
              Workspace name
            </label>
            <input
              id="ws-name"
              type="text"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
              aria-label="Workspace name"
              required
            />
          </div>
          <div>
            <p className="text-sm font-ui text-text-body mb-1">Financial year</p>
            <p
              className="text-sm font-mono text-text-muted"
              aria-label="Financial year (read only)"
            >
              {financialYear ?? '—'}
            </p>
          </div>
          <button
            type="submit"
            disabled={nameMutation.isPending}
            className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
          >
            {nameSaved ? 'Saved' : nameMutation.isPending ? 'Saving…' : 'Save'}
          </button>
          {nameMutation.isError && (
            <p className="text-sm font-ui text-risk-high">Failed to save name.</p>
          )}
        </form>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          All workspaces
        </h2>
        {isLoading ? (
          <p className="text-sm font-ui text-text-muted">Loading…</p>
        ) : (
          <div className="space-y-2">
            {wsData?.items.map((ws: WorkspaceInfo) => (
              <div
                key={ws.id}
                className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3"
              >
                <div>
                  <p className="font-ui font-semibold text-text-primary text-sm">
                    FY {ws.financial_year}
                  </p>
                  <p className="text-xs font-ui text-text-muted">
                    {Math.round(ws.readiness_pct)}% ready
                  </p>
                </div>
                <span
                  className={`text-xs font-ui px-2 py-0.5 rounded-full ${
                    ws.status === 'active'
                      ? 'bg-ready/10 text-ready'
                      : 'bg-surface text-text-muted border border-border'
                  }`}
                >
                  {ws.status === 'active' ? 'Active' : 'Complete'}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3 border border-risk-high/30 rounded-lg p-4">
        <h2 className="font-display text-base font-semibold text-risk-high">
          Danger zone
        </h2>
        <div className="flex flex-col gap-2">
          <button
            type="button"
            disabled
            title="Coming soon"
            className="w-full max-w-xs text-left rounded-md border border-border px-4 py-2 text-sm font-ui text-text-muted opacity-50 cursor-not-allowed"
          >
            Archive this workspace
          </button>
          <button
            type="button"
            disabled
            title="Coming soon"
            className="w-full max-w-xs text-left rounded-md border border-risk-high/40 px-4 py-2 text-sm font-ui text-risk-high/50 opacity-50 cursor-not-allowed"
          >
            Delete this workspace
          </button>
        </div>
        <p className="text-xs font-ui text-text-muted">
          Archive and delete actions are coming soon.
        </p>
      </section>
    </div>
  )
}
