import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SetupPage from '@/app/(auth)/setup/page'

const mockPush = jest.fn()
const mockSetWorkspace = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

jest.mock('@/lib/api/auth', () => ({
  __esModule: true,
  setup: jest.fn(),
  setupConfirm: jest.fn(),
}))

jest.mock('@/lib/stores/workspace.store', () => {
  const mock = jest.fn(() => ({ setWorkspace: mockSetWorkspace, workspaceId: null, financialYear: null }))
  return { __esModule: true, default: mock }
})

import { setup as mockSetup, setupConfirm as mockSetupConfirm } from '@/lib/api/auth'

const RECOVERY_KEY = 'ABCD-EFGH-1234-5678-WXYZ-ABCD-1234-5678'

beforeEach(() => {
  jest.clearAllMocks()
})

function mockClipboard() {
  const writeText = jest.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText },
  })
  return writeText
}

describe('SetupPage', () => {
  it('renders step 1 — set password heading and inputs', async () => {
    const user = userEvent.setup()
    render(<SetupPage />)
    // Navigate past step 0 FY selection
    await user.click(screen.getByRole('button', { name: /2024-25/i }))
    expect(screen.getByRole('heading', { name: /set your password/i })).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByLabelText('Confirm password')).toBeInTheDocument()
  })

  it('step 1 shows strength indicator as password is typed', async () => {
    const user = userEvent.setup()
    render(<SetupPage />)
    // Navigate past step 0 FY selection
    await user.click(screen.getByRole('button', { name: /2024-25/i }))
    await user.type(screen.getByLabelText('Password'), 'weak')
    expect(screen.getByTestId('strength-indicator')).toBeInTheDocument()
  })

  it('shows step 2 — recovery key after step 1 completes', async () => {
    const user = userEvent.setup()
    ;(mockSetup as jest.Mock).mockResolvedValue({
      data: { data: { recovery_key: RECOVERY_KEY, workspace_id: 'ws-1' } },
    })
    render(<SetupPage />)
    // Navigate past step 0 FY selection
    await user.click(screen.getByRole('button', { name: /2024-25/i }))
    await user.type(screen.getByLabelText('Password'), 'StrongPass1!')
    await user.type(screen.getByLabelText('Confirm password'), 'StrongPass1!')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => {
      expect(screen.getByText(RECOVERY_KEY)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /copy/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument()
  })

  it('renders exactly one recovery key value from the backend response', async () => {
    const user = userEvent.setup()
    ;(mockSetup as jest.Mock).mockResolvedValue({
      data: { data: { recovery_key: RECOVERY_KEY, workspace_id: 'ws-1' } },
    })

    render(<SetupPage />)
    await user.click(screen.getByRole('button', { name: /2024-25/i }))
    await user.type(screen.getByLabelText('Password'), 'StrongPass1!')
    await user.type(screen.getByLabelText('Confirm password'), 'StrongPass1!')
    await user.click(screen.getByRole('button', { name: /continue/i }))

    await waitFor(() => expect(screen.getByText(RECOVERY_KEY)).toBeInTheDocument())
    expect(screen.getAllByText(RECOVERY_KEY)).toHaveLength(1)
  })

  it('copy and download use the same displayed backend recovery key', async () => {
    const user = userEvent.setup()
    const writeText = mockClipboard()
    const createObjectURL = jest.fn().mockReturnValue('blob:recovery-key')
    const revokeObjectURL = jest.fn()
    const click = jest.fn()
    const originalBlob = global.Blob
    const blobMock = jest.fn().mockImplementation((parts, options) => ({ parts, options }))
    const originalCreateElement = document.createElement.bind(document)
    const createElementSpy = jest.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      if (tagName === 'a') {
        return {
          click,
          set href(_value: string) {},
          set download(_value: string) {},
        } as HTMLAnchorElement
      }
      return originalCreateElement(tagName)
    })
    Object.defineProperty(global, 'Blob', {
      configurable: true,
      value: blobMock,
    })

    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectURL,
    })
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectURL,
    })

    ;(mockSetup as jest.Mock).mockResolvedValue({
      data: { data: { recovery_key: RECOVERY_KEY, workspace_id: 'ws-1' } },
    })

    render(<SetupPage />)
    await user.click(screen.getByRole('button', { name: /2024-25/i }))
    await user.type(screen.getByLabelText('Password'), 'StrongPass1!')
    await user.type(screen.getByLabelText('Confirm password'), 'StrongPass1!')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(screen.getByText(RECOVERY_KEY)).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /copy/i }))
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(RECOVERY_KEY))

    await user.click(screen.getByRole('button', { name: /download/i }))
    expect(blobMock).toHaveBeenCalledWith([RECOVERY_KEY], { type: 'text/plain' })
    expect(createObjectURL).toHaveBeenCalled()
    expect(click).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:recovery-key')

    createElementSpy.mockRestore()
    Object.defineProperty(global, 'Blob', {
      configurable: true,
      value: originalBlob,
    })
  })

  it('does not generate a client-side recovery key during setup flow', async () => {
    const user = userEvent.setup()
    const originalCrypto = globalThis.crypto
    const getRandomValues = jest.fn()
    const randomUUID = jest.fn()
    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: { getRandomValues, randomUUID },
    })
    ;(mockSetup as jest.Mock).mockResolvedValue({
      data: { data: { recovery_key: RECOVERY_KEY, workspace_id: 'ws-1' } },
    })

    render(<SetupPage />)
    await user.click(screen.getByRole('button', { name: /2024-25/i }))
    await user.type(screen.getByLabelText('Password'), 'StrongPass1!')
    await user.type(screen.getByLabelText('Confirm password'), 'StrongPass1!')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(screen.getByText(RECOVERY_KEY)).toBeInTheDocument())

    expect(getRandomValues).not.toHaveBeenCalled()
    expect(randomUUID).not.toHaveBeenCalled()
    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: originalCrypto,
    })
  })

  it('step 1 shows password mismatch error when passwords do not match', async () => {
    const user = userEvent.setup()
    render(<SetupPage />)
    // Navigate past step 0 FY selection
    await user.click(screen.getByRole('button', { name: /2024-25/i }))
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
      data: { data: { recovery_key: RECOVERY_KEY, workspace_id: 'ws-1' } },
    })
    render(<SetupPage />)
    // Navigate past step 0 FY selection
    await user.click(screen.getByRole('button', { name: /2024-25/i }))
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
      data: { data: { recovery_key: RECOVERY_KEY, workspace_id: 'ws-1' } },
    })
    ;(mockSetupConfirm as jest.Mock).mockResolvedValue({})
    render(<SetupPage />)
    // Step 0: select FY
    await user.click(screen.getByRole('button', { name: /2024-25/i }))
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

describe('SetupPage FY selection', () => {
  it('renders FY selection as first step', () => {
    render(<SetupPage />)
    expect(screen.getByText(/which financial year/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /2024-25/i })).toBeInTheDocument()
  })

  it('calls setWorkspace with workspace data after confirm', async () => {
    const user = userEvent.setup()
    ;(mockSetup as jest.Mock).mockResolvedValue({
      data: { data: { recovery_key: RECOVERY_KEY, workspace_id: 'ws-1' } },
    })
    ;(mockSetupConfirm as jest.Mock).mockResolvedValue({})

    render(<SetupPage />)

    // Step 0: select FY 2024-25
    await user.click(screen.getByRole('button', { name: /2024-25/i }))

    // Step 1: fill password
    await user.type(screen.getByLabelText('Password'), 'StrongPass1!')
    await user.type(screen.getByLabelText('Confirm password'), 'StrongPass1!')
    await user.click(screen.getByRole('button', { name: /continue/i }))

    await waitFor(() =>
      expect(mockSetup).toHaveBeenCalledWith('StrongPass1!', '2024-25')
    )

    // Step 2: recovery key shown — click "I've saved it"
    await waitFor(() => expect(screen.getByText(RECOVERY_KEY)).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /i've saved it/i }))

    // Step 3: enter confirmation
    await waitFor(() => expect(screen.getByLabelText(/last key segment/i)).toBeInTheDocument())
    await user.type(screen.getByLabelText(/last key segment/i), '1234-5678')
    await user.click(screen.getByRole('button', { name: /^confirm$/i }))

    await waitFor(() =>
      expect(mockSetWorkspace).toHaveBeenCalledWith('ws-1', '2024-25')
    )
  })
})
