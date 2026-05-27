// frontend/lib/hooks/useAuth.ts
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getSession } from '@/lib/api/auth'
import useWorkspaceStore from '@/lib/stores/workspace.store'

export function useAuth() {
  const router = useRouter()
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
        const { workspace_id, financial_year, is_unlocked, user_lodger_type } = data
        setWorkspace(workspace_id, financial_year)
        setAuthenticated(true)
        setUnlocked(is_unlocked)
        setUserLodgerType(user_lodger_type ?? null)
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

  return { isAuthenticated }
}
