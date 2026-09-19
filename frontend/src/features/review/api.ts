import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

export function useDue(sessionId: string | null) {
  return useQuery({
    queryKey: ['due', sessionId],
    queryFn: () => api.due(sessionId!),
    enabled: !!sessionId,
  })
}

export function useRate() {
  return useMutation({
    mutationFn: ({
      itemId,
      body,
    }: {
      itemId: string
      body: { session_id: string; rating: number; latency_ms?: number }
    }) => api.rate(itemId, body),
  })
}
