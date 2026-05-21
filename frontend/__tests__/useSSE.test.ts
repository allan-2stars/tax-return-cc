import { renderHook, act } from '@testing-library/react'
import { useSSE } from '@/lib/hooks/useSSE'

class MockEventSource {
  static instance: MockEventSource | null = null
  url: string
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  close = jest.fn()

  constructor(url: string) {
    this.url = url
    MockEventSource.instance = this
  }
}

beforeAll(() => {
  Object.defineProperty(global, 'EventSource', {
    value: MockEventSource,
    writable: true,
  })
})

beforeEach(() => {
  MockEventSource.instance = null
  jest.useFakeTimers()
})

afterEach(() => {
  jest.useRealTimers()
})

describe('useSSE', () => {
  it('closes EventSource on terminal status "ready"', () => {
    const { result } = renderHook(() => useSSE('/stream/doc-1'))
    const es = MockEventSource.instance!
    expect(es).not.toBeNull()

    act(() => {
      es.onmessage?.({
        data: JSON.stringify({ document_id: 'doc-1', status: 'ready', events_created: 1 }),
      })
    })

    expect(es.close).toHaveBeenCalled()
    expect(result.current.data?.status).toBe('ready')
  })

  it('closes EventSource after 5-minute timeout', () => {
    const { result } = renderHook(() => useSSE('/stream/doc-1'))
    const es = MockEventSource.instance!
    expect(result.current.status).toBe('connecting')

    act(() => {
      jest.advanceTimersByTime(5 * 60 * 1000 + 1)
    })

    expect(es.close).toHaveBeenCalled()
    expect(result.current.status).toBe('closed')
  })
})
