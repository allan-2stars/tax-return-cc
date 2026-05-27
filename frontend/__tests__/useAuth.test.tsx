import { renderHook, waitFor } from '@testing-library/react'
import { useAuth } from '@/lib/hooks/useAuth'

const mockReplace = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace, push: jest.fn() }),
}))

jest.mock('@/lib/api/auth', () => ({
  __esModule: true,
  getSession: jest.fn(),
}))

import { getSession } from '@/lib/api/auth'

const mockGetSession = getSession as jest.Mock

beforeEach(() => {
  jest.clearAllMocks()
})

describe('useAuth', () => {
  it('redirects to /login when session request fails with generic error', async () => {
    mockGetSession.mockRejectedValue({
      response: { data: { error_code: 'not_authenticated' } },
    })
    renderHook(() => useAuth())
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/login')
    })
  })

  it('redirects to /setup when error_code is setup_not_confirmed', async () => {
    mockGetSession.mockRejectedValue({
      response: { data: { error_code: 'setup_not_confirmed' } },
    })
    renderHook(() => useAuth())
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/setup')
    })
  })

  it('redirects to /setup when detail.error_code is setup_not_confirmed', async () => {
    mockGetSession.mockRejectedValue({
      response: { data: { detail: { error_code: 'setup_not_confirmed' } } },
    })
    renderHook(() => useAuth())
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/setup')
    })
  })

  it('redirects to /setup when setup_required is true in response data', async () => {
    mockGetSession.mockResolvedValue({
      data: { data: { setup_required: true, authenticated: false } },
    })
    renderHook(() => useAuth())
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/setup')
    })
  })

  it('redirects to /setup when setup_confirmed is false in response data', async () => {
    mockGetSession.mockResolvedValue({
      data: {
        data: {
          workspace_id: 'ws-1',
          financial_year: '2024-25',
          is_unlocked: false,
          user_lodger_type: 'self',
          setup_confirmed: false,
        },
      },
    })
    renderHook(() => useAuth())
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/setup')
    })
  })

  it('redirects to /login when financial_year is unknown in response data', async () => {
    mockGetSession.mockResolvedValue({
      data: {
        data: {
          workspace_id: 'ws-bad',
          financial_year: 'unknown',
          is_unlocked: false,
          user_lodger_type: 'self',
          setup_confirmed: true,
        },
      },
    })
    renderHook(() => useAuth())
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/login')
    })
  })

  it('does not redirect when session exists', async () => {
    mockGetSession.mockResolvedValue({
      data: {
        data: {
          workspace_id: 'ws-1',
          financial_year: '2024-25',
          is_unlocked: true,
        },
      },
    })
    renderHook(() => useAuth())
    await waitFor(() => {
      expect(mockReplace).not.toHaveBeenCalled()
    })
  })
})
