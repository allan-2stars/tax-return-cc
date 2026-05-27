import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RecoverPage from '@/app/(auth)/recover/page'

const mockReplace = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace }),
}))

jest.mock('@/lib/api/auth', () => ({
  __esModule: true,
  recover: jest.fn(),
}))

import { recover as mockRecover } from '@/lib/api/auth'

beforeEach(() => {
  jest.clearAllMocks()
})

describe('RecoverPage', () => {
  it('submits recovery key + new password and redirects to /login on success', async () => {
    const user = userEvent.setup()
    ;(mockRecover as jest.Mock).mockResolvedValue({})

    render(<RecoverPage />)

    await user.type(screen.getByLabelText(/recovery key/i), 'RECOVERY-KEY')
    await user.type(screen.getByLabelText(/new password/i), 'newpassword123')
    await user.click(screen.getByRole('button', { name: /reset password/i }))

    await waitFor(() => {
      expect(mockRecover).toHaveBeenCalledWith('RECOVERY-KEY', 'newpassword123')
      expect(mockReplace).toHaveBeenCalledWith('/login')
    })
  })
})

