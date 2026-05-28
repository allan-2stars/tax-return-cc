'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getSession } from '@/lib/api/auth'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    getSession()
      .then((res) => {
        const data = res.data.data
        if (data.setup_confirmed === false || data.setup_required) {
          router.replace('/setup')
          return
        }
        if (data.setup_confirmed === true) {
          router.replace('/journey')
          return
        }
        router.replace('/login')
      })
      .catch(() => {
        router.replace('/login')
      })
  }, [router])

  return null
}
