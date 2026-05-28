import { render, waitFor } from '@testing-library/react'
import Home from '@/app/page'

const mockReplace = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace }),
}))

jest.mock('@/lib/api/auth', () => ({
  __esModule: true,
  getSession: jest.fn(),
}))

import { getSession as mockGetSession } from '@/lib/api/auth'

beforeEach(() => {
  jest.clearAllMocks()
})

describe('Home', () => {
  it('redirects to /journey when authenticated and setup_confirmed is true', async () => {
    ;(mockGetSession as jest.Mock).mockResolvedValue({
      data: { data: { setup_confirmed: true } },
    })
    render(<Home />)
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/journey')
    })
  })

  it('redirects to /setup when authenticated but setup_confirmed is false', async () => {
    ;(mockGetSession as jest.Mock).mockResolvedValue({
      data: { data: { setup_confirmed: false } },
    })
    render(<Home />)
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/setup')
    })
  })

  it('redirects to /login when unauthenticated', async () => {
    ;(mockGetSession as jest.Mock).mockRejectedValue({
      response: { data: { detail: { error_code: 'not_authenticated' } } },
    })
    render(<Home />)
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/login')
    })
  })
})

