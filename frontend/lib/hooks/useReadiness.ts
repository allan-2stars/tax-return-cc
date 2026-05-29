'use client'

import { useEffect, useRef } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { getReadiness, getMissing, triggerRecalculate } from '@/lib/api/readiness'
import type { ReadinessData, MissingData } from '@/lib/api/types'

export function useReadiness() {
  const staleCycleTriggered = useRef(false)

  const { data, isLoading, isError } = useQuery<ReadinessData>({
    queryKey: ['readiness'],
    queryFn: () => getReadiness().then((r) => r.data.data),
    refetchInterval: (query) =>
      query.state.data?.is_stale ? 3_000 : 30_000,
  })

  const recalcMutation = useMutation({
    mutationFn: triggerRecalculate,
  })

  useEffect(() => {
    if (!data) return

    if (!data.is_stale) {
      staleCycleTriggered.current = false
      return
    }

    if (staleCycleTriggered.current) return
    staleCycleTriggered.current = true
    recalcMutation.mutate()
  }, [data, recalcMutation])

  const recalcError = recalcMutation.isError
    ? 'Unable to refresh readiness right now.'
    : null

  return { data, isLoading, isError, recalcError }
}

export function useMissing() {
  const { data, isLoading, isError } = useQuery<MissingData>({
    queryKey: ['readiness', 'missing'],
    queryFn: () => getMissing().then((r) => r.data.data),
  })
  return { data, isLoading, isError }
}
