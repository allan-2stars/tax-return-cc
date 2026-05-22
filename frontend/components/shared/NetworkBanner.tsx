'use client'
import { useEffect, useState, useRef } from 'react'
import client from '@/lib/api/client'

export default function NetworkBanner() {
  const [offline, setOffline] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function checkHealth() {
    try {
      await client.get('/api/v1/health')
      setOffline(false)
    } catch {
      setOffline(true)
    }
  }

  useEffect(() => {
    checkHealth()
    intervalRef.current = setInterval(checkHealth, 5000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [])

  if (!offline) return null

  return (
    <div role="alert" className="bg-risk-high text-white px-4 py-2 flex items-center">
      <p className="text-sm font-ui">Offline — checking connection…</p>
    </div>
  )
}
