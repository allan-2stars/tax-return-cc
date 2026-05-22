import { create } from 'zustand'

interface WorkspaceStore {
  workspaceId: string | null
  financialYear: string | null
  userLodgerType: string | null
  isAuthenticated: boolean
  isUnlocked: boolean
  setWorkspace: (id: string, fy: string) => void
  setUserLodgerType: (type: string | null) => void
  setAuthenticated: (value: boolean) => void
  setUnlocked: (value: boolean) => void
}

const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  workspaceId: null,
  financialYear: null,
  userLodgerType: null,
  isAuthenticated: false,
  isUnlocked: false,
  setWorkspace: (id, fy) => set({ workspaceId: id, financialYear: fy }),
  setUserLodgerType: (type) => set({ userLodgerType: type }),
  setAuthenticated: (value) => set({ isAuthenticated: value }),
  setUnlocked: (value) => set({ isUnlocked: value }),
}))

export default useWorkspaceStore
