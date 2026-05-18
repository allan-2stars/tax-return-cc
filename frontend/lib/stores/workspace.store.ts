import { create } from 'zustand'

interface WorkspaceStore {
  workspaceId: string | null
  setWorkspaceId: (id: string | null) => void
}

const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  workspaceId: null,
  setWorkspaceId: (id) => set({ workspaceId: id }),
}))

export default useWorkspaceStore
