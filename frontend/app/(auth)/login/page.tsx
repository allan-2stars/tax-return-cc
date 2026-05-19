'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const router = useRouter()
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
        credentials: 'include',
      })
      if (res.ok) {
        router.push('/readiness')
      } else {
        const body = await res.json().catch(() => ({}))
        setError(body?.detail?.message ?? 'Login failed. Check your password.')
      }
    } catch {
      setError('Cannot reach server. Is it running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ padding: '2rem', maxWidth: '400px', margin: '0 auto' }}>
      <h1>Tax Return AI</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="password">Password</label>
          <br />
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoFocus
            style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem' }}
          />
        </div>
        {error && (
          <p role="alert" style={{ color: 'red', marginTop: '0.5rem' }}>
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading}
          style={{ marginTop: '1rem', padding: '0.5rem 1.5rem' }}
        >
          {loading ? 'Logging in…' : 'Log in'}
        </button>
      </form>
    </main>
  )
}
