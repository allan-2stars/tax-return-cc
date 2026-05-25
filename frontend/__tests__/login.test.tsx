import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginPage from '@/app/(auth)/login/page'

const mockPush = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

jest.mock('@/lib/api/auth', () => ({
  __esModule: true,
  login: jest.fn(),
  getSession: jest.fn(),
}))

jest.mock('@/lib/stores/workspace.store', () => ({
  __esModule: true,
  default: () => ({
    setWorkspace: jest.fn(),
    setAuthenticated: jest.fn(),
  }),
}))

import { login as mockLogin, getSession as mockGetSession } from '@/lib/api/auth'

beforeEach(() => {
  jest.clearAllMocks()
  // Default: session endpoint returns 401 — show login form
  ;(mockGetSession as jest.Mock).mockRejectedValue({ response: { data: { error_code: 'not_authenticated' } } })
})

describe('LoginPage', () => {
  it('renders password input and submit button', () => {
    render(<LoginPage />)
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument()
  })

  it('disables submit button while submitting', async () => {
    const user = userEvent.setup()
    let resolveLogin!: (v: unknown) => void
    ;(mockLogin as jest.Mock).mockReturnValue(
      new Promise((r) => { resolveLogin = r })
    )
    render(<LoginPage />)
    await user.type(screen.getByLabelText('Password'), 'anypass')
    await user.click(screen.getByRole('button', { name: /log in/i }))
    expect(screen.getByRole('button', { name: /logging in/i })).toBeDisabled()
    resolveLogin({ data: { data: { workspace_id: 'w', financial_year: '2024-25', is_unlocked: false } } })
  })

  it('shows error message on wrong password', async () => {
    const user = userEvent.setup()
    ;(mockLogin as jest.Mock).mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 401,
        data: { detail: { message: 'Wrong password.', error_code: 'invalid_password' } },
      },
    })
    render(<LoginPage />)
    await user.type(screen.getByLabelText('Password'), 'wrongpass')
    await user.click(screen.getByRole('button', { name: /log in/i }))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Incorrect password. Please try again.')
    })
  })

  it('redirects to /readiness on successful login', async () => {
    const user = userEvent.setup()
    ;(mockLogin as jest.Mock).mockResolvedValue({
      data: {
        data: {
          workspace_id: 'ws-1',
          financial_year: '2024-25',
          is_unlocked: false,
        },
      },
    })
    render(<LoginPage />)
    await user.type(screen.getByLabelText('Password'), 'correctpass')
    await user.click(screen.getByRole('button', { name: /log in/i }))
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/readiness')
    })
  })

  it('redirects to /setup on mount when setup_required is true', async () => {
    ;(mockGetSession as jest.Mock).mockResolvedValue({
      data: { data: { setup_required: true, authenticated: false } },
    })
    render(<LoginPage />)
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/setup')
    })
  })

  it('redirects to /setup on setup_not_confirmed error', async () => {
    const user = userEvent.setup()
    ;(mockLogin as jest.Mock).mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 403,
        data: { detail: { error_code: 'setup_not_confirmed' } },
      },
    })
    render(<LoginPage />)
    await user.type(screen.getByLabelText('Password'), 'anypass')
    await user.click(screen.getByRole('button', { name: /log in/i }))
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/setup')
    })
  })

  it('toggles password visibility', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    const input = screen.getByLabelText('Password')
    expect(input).toHaveAttribute('type', 'password')
    await user.click(screen.getByRole('button', { name: /show password/i }))
    expect(input).toHaveAttribute('type', 'text')
    await user.click(screen.getByRole('button', { name: /hide password/i }))
    expect(input).toHaveAttribute('type', 'password')
  })
})
