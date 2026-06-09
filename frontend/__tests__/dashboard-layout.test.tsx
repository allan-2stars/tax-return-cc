// frontend/__tests__/dashboard-layout.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import DashboardLayout from '@/app/(dashboard)/layout'
import * as settingsApi from '@/lib/api/settings'

jest.mock('@/lib/api/settings')

jest.mock('@/lib/api/client', () => ({
  get: jest.fn().mockResolvedValue({ status: 200 }),
}))

const mockRouterPush = jest.fn()
const mockRouterRefresh = jest.fn()
const mockSetWorkspace = jest.fn()

jest.mock('next/navigation', () => ({
  usePathname: () => '/readiness',
  useRouter: () => ({ replace: jest.fn(), push: mockRouterPush, refresh: mockRouterRefresh }),
}))

jest.mock('@/lib/hooks/useReadiness', () => ({
  useReadiness: () => ({ data: undefined, isLoading: false, isError: false }),
  __esModule: true,
}))

jest.mock('@/lib/hooks/useAuth', () => ({
  useAuth: jest.fn().mockReturnValue({ isAuthenticated: true }),
  __esModule: true,
}))

jest.mock('@/lib/stores/workspace.store', () => ({
  default: () => ({
    workspaceId: 'ws-1',
    financialYear: '2024-25',
    isAuthenticated: true,
    isUnlocked: true,
    setWorkspace: mockSetWorkspace,
    setAuthenticated: jest.fn(),
    setUnlocked: jest.fn(),
  }),
  __esModule: true,
}))

const mockListWorkspaces = settingsApi.listWorkspaces as jest.Mock
const mockSelectWorkspace = settingsApi.selectWorkspace as jest.Mock

describe('DashboardLayout', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockListWorkspaces.mockResolvedValue({
      data: {
        data: {
          items: [
            { id: 'ws-1', name: 'FY 2024-25', financial_year: '2024-25', status: 'active', readiness_pct: 10 },
            { id: 'ws-2', name: 'FY 2025-26', financial_year: '2025-26', status: 'active', readiness_pct: 0 },
          ],
        },
      },
    })
    mockSelectWorkspace.mockResolvedValue({
      data: {
        data: { id: 'ws-2', name: 'FY 2025-26', financial_year: '2025-26', status: 'active', readiness_pct: 0 },
      },
    })
  })

  it('does not render children when not authenticated', () => {
    const { useAuth } = require('@/lib/hooks/useAuth')
    useAuth.mockReturnValue({ isAuthenticated: false })
    render(<DashboardLayout><div>secret</div></DashboardLayout>)
    expect(screen.queryByText('secret')).not.toBeInTheDocument()
  })

  afterEach(() => {
    const { useAuth } = require('@/lib/hooks/useAuth')
    useAuth.mockReturnValue({ isAuthenticated: true })
  })

  it('renders the sidebar nav with core navigation items', () => {
    render(<DashboardLayout><div>content</div></DashboardLayout>)
    expect(screen.getByText('Tax Journey')).toBeInTheDocument()
    expect(screen.getByText('Tax Readiness')).toBeInTheDocument()
    expect(screen.getAllByText('Review').length).toBeGreaterThan(0)
    expect(screen.getByText('Export Review Pack')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText(/suggested order/i)).toBeInTheDocument()
    expect(screen.getByText(/journey → evidence → review → readiness → export/i)).toBeInTheDocument()
  })

  it('marks the active nav item based on pathname', () => {
    render(<DashboardLayout><div>content</div></DashboardLayout>)
    const readinessLink = screen.getByRole('link', { name: /tax readiness/i })
    expect(readinessLink).toHaveAttribute('data-active', 'true')
  })

  it('renders children in the content area', () => {
    render(<DashboardLayout><div>hello content</div></DashboardLayout>)
    expect(screen.getByText('hello content')).toBeInTheDocument()
  })

  it('shows FY indicator in the sidebar', () => {
    render(<DashboardLayout><div>x</div></DashboardLayout>)
    expect(screen.getByText(/2024-25/)).toBeInTheDocument()
  })

  it('opens a tax-year switcher instead of the create modal when FY is clicked', async () => {
    render(<DashboardLayout><div>x</div></DashboardLayout>)
    fireEvent.click(screen.getByRole('button', { name: /fy 2024-25/i }))
    expect(await screen.findByText(/tax years/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /2024-25 current/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /2025-26/i })).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('switches workspace context when selecting an existing financial year', async () => {
    render(<DashboardLayout><div>x</div></DashboardLayout>)
    fireEvent.click(screen.getByRole('button', { name: /fy 2024-25/i }))
    fireEvent.click(await screen.findByRole('button', { name: /^2025-26$/i }))

    await waitFor(() => expect(mockSelectWorkspace).toHaveBeenCalledWith('ws-2'))
    expect(mockSetWorkspace).toHaveBeenCalledWith('ws-2', '2025-26')
    expect(mockRouterPush).toHaveBeenCalledWith('/journey')
    expect(mockRouterRefresh).toHaveBeenCalled()
  })

  it('keeps starting a new tax year as a separate action', async () => {
    render(<DashboardLayout><div>x</div></DashboardLayout>)
    fireEvent.click(screen.getByRole('button', { name: /fy 2024-25/i }))
    fireEvent.click(await screen.findByRole('button', { name: /start new tax year return/i }))
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
  })

  it('renders mobile bottom tab bar with primary 5 items', () => {
    render(<DashboardLayout><div>x</div></DashboardLayout>)
    const bottomTabNav = screen.getByRole('navigation', { name: /mobile/i })
    expect(bottomTabNav).toBeInTheDocument()
  })

  it('does not show Income, Deductions, or Investments in sidebar nav', () => {
    render(<DashboardLayout><div>content</div></DashboardLayout>)
    expect(screen.queryByRole('link', { name: /^income$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /^deductions$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /^investments$/i })).not.toBeInTheDocument()
  })

  it('opens the More sheet when the More button is clicked', () => {
    render(<DashboardLayout><div>content</div></DashboardLayout>)
    fireEvent.click(screen.getByRole('button', { name: /more/i }))
    expect(screen.getByRole('dialog', { name: /more options/i })).toBeInTheDocument()
  })

  it('renders dismissible session restored banner when auth hook reports restored session', () => {
    const { useAuth } = require('@/lib/hooks/useAuth')
    useAuth.mockReturnValue({ isAuthenticated: true, sessionRestored: true, clearSessionRestored: jest.fn() })

    render(<DashboardLayout><div>content</div></DashboardLayout>)

    expect(screen.getByText(/session restored/i)).toBeInTheDocument()
    expect(screen.getByText(/workspace data is up to date/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /dismiss session restored message/i }))
    expect(useAuth().clearSessionRestored).toHaveBeenCalled()
  })
})
