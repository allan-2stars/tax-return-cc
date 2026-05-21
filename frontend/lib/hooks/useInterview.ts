'use client'
import { useQuery } from '@tanstack/react-query'
import { getSession } from '@/lib/api/interview'
import type { InterviewSessionData } from '@/lib/api/types'

export function useInterview() {
  const { data, isLoading, isError } = useQuery<InterviewSessionData>({
    queryKey: ['interview', 'session'],
    queryFn: () => getSession().then((r) => r.data.data),
  })
  return { data, isLoading, isError }
}
