'use client'

import { useEffect, useState } from 'react'
import type { HealthResponse } from '@/lib/api/types'

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; data: HealthResponse }
  | { kind: 'error'; message: string }

export default function HealthPage() {
  const [state, setState] = useState<State>({ kind: 'loading' })

  useEffect(() => {
    fetch('/api/v1/health')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<HealthResponse>
      })
      .then((data) => setState({ kind: 'ok', data }))
      .catch((err: unknown) =>
        setState({
          kind: 'error',
          message: err instanceof Error ? err.message : 'Unknown error',
        }),
      )
  }, [])

  return (
    <main
      style={{
        padding: 'var(--space-8)',
        fontFamily: 'var(--font-mono)',
        color: 'var(--color-text-primary)',
        background: 'var(--color-canvas)',
        minHeight: '100vh',
      }}
    >
      <h1
        style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'var(--text-2xl)',
          marginBottom: 'var(--space-6)',
        }}
      >
        System Health
      </h1>

      {state.kind === 'loading' && <p>Checking connection…</p>}

      {state.kind === 'error' && (
        <p style={{ color: 'var(--color-error)' }}>
          Cannot reach backend — is the server running?
          <br />
          <span style={{ fontSize: 'var(--text-xs)' }}>{state.message}</span>
        </p>
      )}

      {state.kind === 'ok' && (
        <pre
          style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-4)',
            fontSize: 'var(--text-sm)',
            overflowX: 'auto',
          }}
        >
          {JSON.stringify(state.data, null, 2)}
        </pre>
      )}
    </main>
  )
}
