// frontend/lib/hooks/useAuth.ts
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getSession } from '@/lib/api/auth'
import useWorkspaceStore from '@/lib/stores/workspace.store'

export function useAuth() {
  const router = useRouter()
  const { setWorkspace, setAuthenticated, setUnlocked, isAuthenticated } =
    useWorkspaceStore()

  useEffect(() => {
    getSession()
      .then((res) => {
        const { workspace_id, financial_year, is_unlocked } = res.data.data
        setWorkspace(workspace_id, financial_year)
        setAuthenticated(true)
        setUnlocked(is_unlocked)
      })
      .catch((err: unknown) => {
        const errorCode = (
          err as {
            response?: { data?: { error_code?: string } }
          }
        )?.response?.data?.error_code
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
