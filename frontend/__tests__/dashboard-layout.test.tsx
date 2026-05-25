// frontend/__tests__/dashboard-layout.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import DashboardLayout from '@/app/(dashboard)/layout'

jest.mock('@/lib/api/client', () => ({
  get: jest.fn().mockResolvedValue({ status: 200 }),
}))

jest.mock('next/navigation', () => ({
  usePathname: () => '/readiness',
  useRouter: () => ({ replace: jest.fn(), push: jest.fn() }),
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
    setWorkspace: jest.fn(),
    setAuthenticated: jest.fn(),
    setUnlocked: jest.fn(),
  }),
  __esModule: true,
}))

describe('DashboardLayout', () => {
  it('renders the sidebar nav with core navigation items', () => {
    render(<DashboardLayout><div>content</div></DashboardLayout>)
    expect(screen.getByText('Tax Journey')).toBeInTheDocument()
    expect(screen.getByText('Tax Readiness')).toBeInTheDocument()
    expect(screen.getAllByText('Review').length).toBeGreaterThan(0)
    expect(screen.getByText('Export Review Pack')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
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
})
