import { useQuery } from '@tanstack/react-query'
import client from '@/lib/api/client'
import type { ApiResponse } from '@/lib/api/types'

interface ReadinessData {
  score: number
}

export function useReadiness(workspaceId: string | null) {
  return useQuery<ApiResponse<ReadinessData>>({
    queryKey: ['readiness', workspaceId],
    queryFn: () =>
      client
        .get<ApiResponse<ReadinessData>>(`/api/v1/readiness?workspace_id=${workspaceId}`)
        .then((r) => r.data),
    enabled: workspaceId !== null,
  })
}
