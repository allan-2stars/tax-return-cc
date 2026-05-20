'use client'

import { useQuery } from '@tanstack/react-query'
import { getReadiness, getMissing } from '@/lib/api/readiness'
import type { ReadinessData, MissingData } from '@/lib/api/types'

export function useReadiness() {
  const { data, isLoading, isError } = useQuery<ReadinessData>({
    queryKey: ['readiness'],
    queryFn: () => getReadiness().then((r) => r.data.data),
    refetchInterval: (query) =>
      query.state.data?.is_stale ? 3_000 : 30_000,
  })
  return { data, isLoading, isError }
}

export function useMissing() {
  const { data, isLoading, isError } = useQuery<MissingData>({
    queryKey: ['readiness', 'missing'],
    queryFn: () => getMissing().then((r) => r.data.data),
  })
  return { data, isLoading, isError }
}
