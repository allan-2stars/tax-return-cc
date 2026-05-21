'use client'
import { useEffect, useState } from 'react'
import type { SSEEvent } from '@/lib/api/types'

// 'processing' is intentionally excluded — stream stays open while processing
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

    let closed = false
    const closeConnection = (reason?: string) => {
      if (closed) return
      closed = true
      clearTimeout(timer)
      es.close()
      setStatus('closed')
      if (reason) setError(reason)
    }

    const timer = setTimeout(() => {
      closeConnection('timeout')
    }, TIMEOUT_MS)

    es.onopen = () => setStatus('open')

    es.onmessage = (e) => {
      try {
        const evt: SSEEvent = JSON.parse(e.data as string)
        setData(evt)
        if (TERMINAL.has(evt.status)) {
          closeConnection()
        }
      } catch {
        // ignore malformed events
      }
    }

    es.onerror = () => {
      closeConnection('connection_error')
    }

    return () => {
      closeConnection()
    }
  }, [url])

  return { data, status, error }
}
