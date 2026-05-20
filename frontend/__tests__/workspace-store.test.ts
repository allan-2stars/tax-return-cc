import useWorkspaceStore from '@/lib/stores/workspace.store'

describe('WorkspaceStore', () => {
  beforeEach(() => {
    useWorkspaceStore.setState({
      workspaceId: null,
      financialYear: null,
      isAuthenticated: false,
      isUnlocked: false,
    })
  })

  it('initial state is unauthenticated with no workspace', () => {
    const state = useWorkspaceStore.getState()
    expect(state.workspaceId).toBeNull()
    expect(state.financialYear).toBeNull()
    expect(state.isAuthenticated).toBe(false)
    expect(state.isUnlocked).toBe(false)
  })

  it('setWorkspace sets workspaceId and financialYear together', () => {
    useWorkspaceStore.getState().setWorkspace('ws-123', '2024-25')
    const state = useWorkspaceStore.getState()
    expect(state.workspaceId).toBe('ws-123')
    expect(state.financialYear).toBe('2024-25')
  })

  it('setAuthenticated updates isAuthenticated', () => {
    useWorkspaceStore.getState().setAuthenticated(true)
    expect(useWorkspaceStore.getState().isAuthenticated).toBe(true)
  })

  it('setUnlocked updates isUnlocked', () => {
    useWorkspaceStore.getState().setUnlocked(true)
    expect(useWorkspaceStore.getState().isUnlocked).toBe(true)
  })
})
