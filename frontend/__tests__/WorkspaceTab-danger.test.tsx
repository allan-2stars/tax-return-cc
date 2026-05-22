import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import WorkspaceTab from '@/components/settings/WorkspaceTab'
import NewFYModal from '@/components/settings/NewFYModal'
import * as settingsApi from '@/lib/api/settings'

jest.mock('@/lib/api/settings')
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace: jest.fn(), push: jest.fn() }) }))

const mockWs = {
  id: 'ws-1',
  name: 'My Return',
  financial_year: '2024-25',
  status: 'active',
  readiness_pct: 45,
}

function QueryWrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  jest.clearAllMocks()
  ;(settingsApi.listWorkspaces as jest.Mock).mockResolvedValue({
    data: { data: { items: [mockWs] } },
  })
  ;(settingsApi.updateWorkspaceName as jest.Mock).mockResolvedValue({
    data: { data: mockWs },
  })
})

describe('WorkspaceTab danger zone', () => {
  it('archive button is enabled and calls archiveWorkspace on click', async () => {
    ;(settingsApi.archiveWorkspace as jest.Mock).mockResolvedValue({
      data: { data: { ...mockWs, status: 'archived' } },
    })
    render(
      <QueryWrapper>
        <WorkspaceTab />
      </QueryWrapper>
    )
    const btn = await screen.findByRole('button', { name: /^archive$/i })
    expect(btn).not.toBeDisabled()
    fireEvent.click(btn)
    await waitFor(() =>
      expect(settingsApi.archiveWorkspace).toHaveBeenCalledWith('ws-1')
    )
  })

  it('delete button opens password modal', async () => {
    render(
      <QueryWrapper>
        <WorkspaceTab />
      </QueryWrapper>
    )
    const btn = await screen.findByRole('button', { name: /delete workspace/i })
    fireEvent.click(btn)
    expect(await screen.findByLabelText(/password/i)).toBeInTheDocument()
  })

  it('delete with password calls deleteWorkspace', async () => {
    ;(settingsApi.deleteWorkspace as jest.Mock).mockResolvedValue({
      data: { data: { redirect_to: '/setup' } },
    })
    render(
      <QueryWrapper>
        <WorkspaceTab />
      </QueryWrapper>
    )
    fireEvent.click(await screen.findByRole('button', { name: /delete workspace/i }))
    const pwInput = await screen.findByLabelText(/password/i)
    fireEvent.change(pwInput, { target: { value: 'mypassword' } })
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }))
    await waitFor(() =>
      expect(settingsApi.deleteWorkspace).toHaveBeenCalledWith('ws-1', 'mypassword')
    )
  })
})

describe('NewFYModal', () => {
  it('renders with next FY pre-filled from currentFY prop', () => {
    render(<NewFYModal currentFY="2024-25" onSuccess={jest.fn()} onCancel={jest.fn()} />)
    const fyInput = screen.getByDisplayValue('2025-26')
    expect(fyInput).toBeInTheDocument()
  })

  it('calls createWorkspace and onSuccess on submit', async () => {
    ;(settingsApi.createWorkspace as jest.Mock).mockResolvedValue({
      data: {
        data: {
          id: 'ws-2',
          name: 'My Tax Return',
          financial_year: '2025-26',
          status: 'active',
          readiness_pct: 0,
          yoy_count: 0,
        },
      },
    })
    const onSuccess = jest.fn()
    render(<NewFYModal currentFY="2024-25" onSuccess={onSuccess} onCancel={jest.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /create/i }))
    await waitFor(() => expect(onSuccess).toHaveBeenCalled())
  })

  it('shows error when name is empty', async () => {
    render(<NewFYModal currentFY="2024-25" onSuccess={jest.fn()} onCancel={jest.fn()} />)
    const nameInput = screen.getByLabelText(/workspace name/i)
    fireEvent.change(nameInput, { target: { value: '' } })
    // fireEvent.submit bypasses browser constraint validation so our JS guard runs
    const form = nameInput.closest('form')!
    fireEvent.submit(form)
    expect(await screen.findByText(/name is required/i)).toBeInTheDocument()
  })
})
