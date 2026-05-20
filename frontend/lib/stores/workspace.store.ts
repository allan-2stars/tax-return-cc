import { create } from 'zustand'

interface WorkspaceStore {
  workspaceId: string | null
  financialYear: string | null
  isAuthenticated: boolean
  isUnlocked: boolean
  setWorkspace: (id: string, fy: string) => void
  setAuthenticated: (value: boolean) => void
  setUnlocked: (value: boolean) => void
}

const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  workspaceId: null,
  financialYear: null,
  isAuthenticated: false,
  isUnlocked: false,
  setWorkspace: (id, fy) => set({ workspaceId: id, financialYear: fy }),
  setAuthenticated: (value) => set({ isAuthenticated: value }),
  setUnlocked: (value) => set({ isUnlocked: value }),
}))

export default useWorkspaceStore
