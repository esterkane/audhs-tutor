import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

export function useDue(sessionId: string | null, all = false) {
  return useQuery({
    queryKey: ['due', sessionId, all],
    queryFn: () => api.due(sessionId!, all),
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
      body: {
        session_id: string
        rating: number
        latency_ms?: number
        confidence_pre?: number
        hint_count?: number
      }
    }) => api.rate(itemId, body),
  })
}
