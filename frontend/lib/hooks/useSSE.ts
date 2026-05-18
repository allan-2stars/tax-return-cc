import { useEffect } from 'react'

export function useSSE(url: string | null, onMessage: (data: string) => void) {
  useEffect(() => {
    if (!url) return
    const es = new EventSource(url)
    es.onmessage = (e) => onMessage(e.data as string)
    return () => es.close()
  }, [url, onMessage])
}
