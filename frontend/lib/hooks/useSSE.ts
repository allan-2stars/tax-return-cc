'use client'
import { useEffect, useState } from 'react'
import type { SSEEvent } from '@/lib/api/types'

const TERMINAL = new Set(['ready', 'failed', 'archived'])
const TIMEOUT_MS = 5 * 60 * 1000

type SSEStatus = 'connecting' | 'open' | 'closed'

export function useSSE(url: string | null): {
  data: SSEEvent | null
  status: SSEStatus
  error: string | null
} {
  const [data, setData] = useState<SSEEvent | null>(null)
  const [status, setStatus] = useState<SSEStatus>('closed')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!url) return
    setStatus('connecting')
    setData(null)
    setError(null)

    const es = new EventSource(url)

    const timer = setTimeout(() => {
      es.close()
      setStatus('closed')
      setError('timeout')
    }, TIMEOUT_MS)

    es.onopen = () => setStatus('open')

    es.onmessage = (e) => {
      try {
        const evt: SSEEvent = JSON.parse(e.data as string)
        setData(evt)
        if (TERMINAL.has(evt.status)) {
          clearTimeout(timer)
          es.close()
          setStatus('closed')
        }
      } catch {
        // ignore malformed events
      }
    }

    es.onerror = () => {
      clearTimeout(timer)
      es.close()
      setStatus('closed')
      setError('connection_error')
    }

    return () => {
      clearTimeout(timer)
      es.close()
    }
  }, [url])

  return { data, status, error }
}
