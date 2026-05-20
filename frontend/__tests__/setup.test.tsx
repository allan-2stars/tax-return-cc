import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SetupPage from '@/app/(auth)/setup/page'

const mockPush = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

jest.mock('@/lib/api/auth', () => ({
  __esModule: true,
  setup: jest.fn(),
  setupConfirm: jest.fn(),
}))

import { setup as mockSetup, setupConfirm as mockSetupConfirm } from '@/lib/api/auth'

const RECOVERY_KEY = 'ABCD-EFGH-1234-5678-WXYZ-ABCD-1234-5678'

beforeEach(() => {
  jest.clearAllMocks()
})

describe('SetupPage', () => {
  it('renders step 1 — set password heading and inputs', () => {
    render(<SetupPage />)
    expect(screen.getByRole('heading', { name: /set your password/i })).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByLabelText('Confirm password')).toBeInTheDocument()
  })

  it('step 1 shows strength indicator as password is typed', async () => {
    const user = userEvent.setup()
    render(<SetupPage />)
    await user.type(screen.getByLabelText('Password'), 'weak')
    expect(screen.getByTestId('strength-indicator')).toBeInTheDocument()
  })

  it('shows step 2 — recovery key after step 1 completes', async () => {
    const user = userEvent.setup()
    ;(mockSetup as jest.Mock).mockResolvedValue({
      data: { data: { recovery_key: RECOVERY_KEY } },
    })
    render(<SetupPage />)
    await user.type(screen.getByLabelText('Password'), 'StrongPass1!')
    await user.type(screen.getByLabelText('Confirm password'), 'StrongPass1!')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => {
      expect(screen.getByText(RECOVERY_KEY)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /copy/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument()
  })

  it('step 1 shows password mismatch error when passwords do not match', async () => {
    const user = userEvent.setup()
    render(<SetupPage />)
    await user.type(screen.getByLabelText('Password'), 'StrongPass1!')
    await user.type(screen.getByLabelText('Confirm password'), 'DifferentPass1!')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Passwords do not match.')
    })
  })

  it("shows step 3 — confirmation input after \"I've saved it\" click", async () => {
    const user = userEvent.setup()
    ;(mockSetup as jest.Mock).mockResolvedValue({
      data: { data: { recovery_key: RECOVERY_KEY } },
    })
    render(<SetupPage />)
    await user.type(screen.getByLabelText('Password'), 'StrongPass1!')
    await user.type(screen.getByLabelText('Confirm password'), 'StrongPass1!')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(screen.getByText(RECOVERY_KEY)).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /i've saved it/i }))
    await waitFor(() => {
      expect(screen.getByLabelText(/last key segment/i)).toBeInTheDocument()
    })
  })

  it('step 3 confirms and redirects to /journey on success', async () => {
    const user = userEvent.setup()
    ;(mockSetup as jest.Mock).mockResolvedValue({
      data: { data: { recovery_key: RECOVERY_KEY } },
    })
    ;(mockSetupConfirm as jest.Mock).mockResolvedValue({})
    render(<SetupPage />)
    // Step 1
    await user.type(screen.getByLabelText('Password'), 'StrongPass1!')
    await user.type(screen.getByLabelText('Confirm password'), 'StrongPass1!')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(screen.getByText(RECOVERY_KEY)).toBeInTheDocument())
    // Step 2
    await user.click(screen.getByRole('button', { name: /i've saved it/i }))
    await waitFor(() => expect(screen.getByLabelText(/last key segment/i)).toBeInTheDocument())
    // Step 3 — last segment of RECOVERY_KEY is "1234-5678"
    await user.type(screen.getByLabelText(/last key segment/i), '1234-5678')
    await user.click(screen.getByRole('button', { name: /^confirm$/i }))
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/journey')
    })
  })
})
