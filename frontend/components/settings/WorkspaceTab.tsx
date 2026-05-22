'use client'
import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import {
  listWorkspaces,
  updateWorkspaceName,
  archiveWorkspace,
  deleteWorkspace,
} from '@/lib/api/settings'
import type { WorkspaceInfo } from '@/lib/api/types'
import PasswordModal from './PasswordModal'

export default function WorkspaceTab() {
  const queryClient = useQueryClient()
  const router = useRouter()
  const [nameInput, setNameInput] = useState('')
  const [nameInitialized, setNameInitialized] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data: wsData } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () =>
      listWorkspaces().then((r) => r.data.data.items[0] as WorkspaceInfo | undefined),
  })

  useEffect(() => {
    if (wsData && !nameInitialized) {
      setNameInput(wsData.name)
      setNameInitialized(true)
    }
  }, [wsData, nameInitialized])

  const renameMutation = useMutation({
    mutationFn: (name: string) => updateWorkspaceName(wsData!.id, name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workspaces'] }),
  })

  const archiveMutation = useMutation({
    mutationFn: () => archiveWorkspace(wsData!.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workspaces'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (password: string) => deleteWorkspace(wsData!.id, password),
    onSuccess: (res) => {
      router.replace(res.data.data.redirect_to)
    },
  })

  async function handleDelete(password: string) {
    setDeleteError(null)
    try {
      await deleteMutation.mutateAsync(password)
      setShowDeleteModal(false)
    } catch {
      setDeleteError('Incorrect password or delete failed. Please try again.')
    }
  }

  if (!wsData) return null

  return (
    <div className="space-y-6">
      <div>
        <label htmlFor="ws-name" className="text-sm font-ui text-text-body block mb-1">
          Workspace name
        </label>
        <div className="flex gap-3">
          <input
            id="ws-name"
            type="text"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            className="flex-1 rounded-md border border-border bg-surface px-3 py-2 text-sm font-ui"
            aria-label="Workspace name"
          />
          <button
            type="button"
            disabled={renameMutation.isPending || nameInput === wsData.name}
            onClick={() => renameMutation.mutate(nameInput)}
            className="px-4 py-2 rounded-md bg-accent text-white text-sm font-ui disabled:opacity-50"
          >
            {renameMutation.isPending ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>

      <div>
        <p className="text-sm font-ui text-text-body mb-1">Financial year</p>
        <p aria-label="Financial year (read only)" className="text-sm font-mono text-text-primary">
          FY {wsData.financial_year}
        </p>
      </div>

      <div className="border border-risk-high rounded-lg p-4 space-y-3">
        <h3 className="font-ui text-sm font-semibold text-risk-high">Danger Zone</h3>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-ui text-text-primary">Archive workspace</p>
            <p className="text-xs font-ui text-text-muted">
              Mark this FY as complete. Data is preserved.
            </p>
          </div>
          <button
            type="button"
            onClick={() => archiveMutation.mutate()}
            disabled={archiveMutation.isPending || wsData.status === 'archived'}
            className="px-4 py-2 rounded-md border border-risk-high text-risk-high text-sm font-ui disabled:opacity-50"
          >
            {archiveMutation.isPending ? 'Archiving…' : 'Archive'}
          </button>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-ui text-text-primary">Delete workspace</p>
            <p className="text-xs font-ui text-text-muted">
              Permanently removes all data. Requires your password.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowDeleteModal(true)}
            className="px-4 py-2 rounded-md bg-risk-high text-white text-sm font-ui"
          >
            Delete workspace
          </button>
        </div>
      </div>

      {showDeleteModal && (
        <PasswordModal
          title="Delete workspace"
          description="Enter your password to permanently delete this workspace. This cannot be undone."
          confirmLabel="Confirm"
          pending={deleteMutation.isPending}
          error={deleteError}
          onConfirm={handleDelete}
          onCancel={() => {
            setShowDeleteModal(false)
            setDeleteError(null)
          }}
        />
      )}
    </div>
  )
}
