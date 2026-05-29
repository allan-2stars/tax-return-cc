import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'

jest.mock('@/lib/api/readiness', () => ({
  getReadiness: jest.fn(),
  getMissing: jest.fn(),
  triggerRecalculate: jest.fn(),
  __esModule: true,
}))

import {
  getReadiness as mockGetReadiness,
  getMissing as mockGetMissing,
  triggerRecalculate as mockTriggerRecalculate,
} from '@/lib/api/readiness'
import { useReadiness, useMissing } from '@/lib/hooks/useReadiness'

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
  return { qc, Wrapper }
}

const MOCK_READINESS = {
  percentage: 72,
  breakdown: [{ skill_id: 'employee_tax_au', percentage: 80, achieved_weight: 4, total_weight: 5 }],
  missing_items_count: 2,
  review_items_count: 3,
  agent_items_count: 1,
  is_stale: false,
  calculated_at: '2026-05-20T10:00:00+00:00',
}

const MOCK_MISSING = {
  available_now: [{ requirement_id: 'receipt', display: 'Work receipt', weight: 1, skill_id: 'employee_tax_au' }],
  available_after_fy: [],
}

beforeEach(() => jest.clearAllMocks())

describe('useReadiness', () => {
  it('returns readiness data when query resolves', async () => {
    ;(mockGetReadiness as jest.Mock).mockResolvedValue({ data: { data: MOCK_READINESS } })
    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useReadiness(), { wrapper: Wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data?.percentage).toBe(72)
  })

  it('isLoading is true while fetching', () => {
    ;(mockGetReadiness as jest.Mock).mockReturnValue(new Promise(() => {}))
    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useReadiness(), { wrapper: Wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it('isError is true when query rejects', async () => {
    ;(mockGetReadiness as jest.Mock).mockRejectedValue(new Error('network error'))
    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useReadiness(), { wrapper: Wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })

  it('triggers recalculate once when readiness becomes stale', async () => {
    ;(mockGetReadiness as jest.Mock).mockResolvedValue({
      data: { data: { ...MOCK_READINESS, is_stale: true } },
    })
    ;(mockTriggerRecalculate as jest.Mock).mockResolvedValue({
      data: { data: { status: 'recalculating' } },
    })

    const { Wrapper } = createWrapper()
    renderHook(() => useReadiness(), { wrapper: Wrapper })

    await waitFor(() => expect(mockTriggerRecalculate).toHaveBeenCalledTimes(1))
  })

  it('does not repeatedly trigger recalculate during the same stale cycle', async () => {
    ;(mockGetReadiness as jest.Mock).mockResolvedValue({
      data: { data: { ...MOCK_READINESS, is_stale: true } },
    })
    ;(mockTriggerRecalculate as jest.Mock).mockResolvedValue({
      data: { data: { status: 'recalculating' } },
    })

    const { qc, Wrapper } = createWrapper()
    renderHook(() => useReadiness(), { wrapper: Wrapper })
    await waitFor(() => expect(mockTriggerRecalculate).toHaveBeenCalledTimes(1))

    await act(async () => {
      await qc.invalidateQueries({ queryKey: ['readiness'] })
      await qc.invalidateQueries({ queryKey: ['readiness'] })
      await qc.invalidateQueries({ queryKey: ['readiness'] })
    })
    await waitFor(() => expect(mockGetReadiness).toHaveBeenCalledTimes(4))
    expect(mockTriggerRecalculate).toHaveBeenCalledTimes(1)
  })

  it('can trigger recalculate again after becoming fresh then stale again', async () => {
    ;(mockGetReadiness as jest.Mock)
      .mockResolvedValueOnce({ data: { data: { ...MOCK_READINESS, is_stale: true } } })
      .mockResolvedValueOnce({ data: { data: { ...MOCK_READINESS, is_stale: false } } })
      .mockResolvedValue({ data: { data: { ...MOCK_READINESS, is_stale: true } } })
    ;(mockTriggerRecalculate as jest.Mock).mockResolvedValue({
      data: { data: { status: 'recalculating' } },
    })

    const { qc, Wrapper } = createWrapper()
    renderHook(() => useReadiness(), { wrapper: Wrapper })
    await waitFor(() => expect(mockTriggerRecalculate).toHaveBeenCalledTimes(1))

    await act(async () => {
      await qc.invalidateQueries({ queryKey: ['readiness'] })
    })
    await waitFor(() => expect(mockGetReadiness).toHaveBeenCalledTimes(2))

    await act(async () => {
      await qc.invalidateQueries({ queryKey: ['readiness'] })
    })
    await waitFor(() => expect(mockGetReadiness).toHaveBeenCalledTimes(3))
    await waitFor(() => expect(mockTriggerRecalculate).toHaveBeenCalledTimes(2))
  })
})

describe('useMissing', () => {
  it('returns missing data when query resolves', async () => {
    ;(mockGetMissing as jest.Mock).mockResolvedValue({ data: { data: MOCK_MISSING } })
    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useMissing(), { wrapper: Wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data?.available_now).toHaveLength(1)
  })
})
