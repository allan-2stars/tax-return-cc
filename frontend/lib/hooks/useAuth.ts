// frontend/lib/hooks/useAuth.ts
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getSession } from '@/lib/api/auth'
import useWorkspaceStore from '@/lib/stores/workspace.store'

const SESSION_SEEN_KEY = 'tax-return-session-seen'

export function useAuth() {
  const router = useRouter()
  const [sessionRestored, setSessionRestored] = useState(false)
  const { setWorkspace, setAuthenticated, setUnlocked, setUserLodgerType, isAuthenticated } =
    useWorkspaceStore()

  useEffect(() => {
    getSession()
      .then((res) => {
        const data = res.data.data
        if (data.setup_required) {
          router.replace('/setup')
          return
        }
        if (data.setup_confirmed === false) {
          setAuthenticated(false)
          router.replace('/setup')
          return
        }
        const { workspace_id, financial_year, is_unlocked, user_lodger_type } = data
        if (!workspace_id || !financial_year || financial_year === 'unknown') {
          setAuthenticated(false)
          router.replace('/login')
          return
        }
        setWorkspace(workspace_id, financial_year)
        setAuthenticated(true)
        setUnlocked(is_unlocked)
        setUserLodgerType(user_lodger_type ?? null)
        const seen = sessionStorage.getItem(SESSION_SEEN_KEY) === '1'
        sessionStorage.setItem(SESSION_SEEN_KEY, '1')
        if (seen) {
          setSessionRestored(true)
        }
      })
      .catch((err: unknown) => {
        const data = (
          err as {
            response?: { data?: { error_code?: string; detail?: { error_code?: string } } }
          }
        )?.response?.data
        const errorCode = data?.error_code ?? data?.detail?.error_code
        if (errorCode === 'setup_not_confirmed') {
          router.replace('/setup')
        } else {
          router.replace('/login')
        }
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    isAuthenticated,
    sessionRestored,
    clearSessionRestored: () => setSessionRestored(false),
  }
}
