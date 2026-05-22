import { render, screen, act } from '@testing-library/react'
import NetworkBanner from '@/components/shared/NetworkBanner'
import client from '@/lib/api/client'

jest.mock('@/lib/api/client', () => ({
  get: jest.fn(),
}))

const mockGet = client.get as jest.Mock

beforeEach(() => {
  jest.clearAllMocks()
  jest.useFakeTimers()
})

afterEach(() => {
  jest.useRealTimers()
})

describe('NetworkBanner', () => {
  it('renders nothing when API is reachable', async () => {
    mockGet.mockResolvedValue({ status: 200 })
    const { container } = render(<NetworkBanner />)
    await act(async () => {
      await Promise.resolve()
    })
    expect(container).toBeEmptyDOMElement()
  })

  it('shows offline banner when API call throws', async () => {
    mockGet.mockRejectedValue(new Error('Network Error'))
    render(<NetworkBanner />)
    await act(async () => {
      await Promise.resolve()
    })
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/offline/i)).toBeInTheDocument()
  })

  it('auto-hides banner when API comes back online', async () => {
    mockGet
      .mockRejectedValueOnce(new Error('Network Error'))
      .mockResolvedValue({ status: 200 })
    render(<NetworkBanner />)
    // First poll fails
    await act(async () => { await Promise.resolve() })
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    // Advance timer by 5s to trigger next poll
    await act(async () => {
      jest.advanceTimersByTime(5000)
      await Promise.resolve()
    })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows "checking connection" message when offline', async () => {
    mockGet.mockRejectedValue(new Error('Network Error'))
    render(<NetworkBanner />)
    await act(async () => { await Promise.resolve() })
    expect(await screen.findByText(/checking connection/i)).toBeInTheDocument()
  })
})
