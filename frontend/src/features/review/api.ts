import { useMutation, useQuery, useQueryClient, useIsMutating } from '@tanstack/react-query'
import { api } from '../../lib/api'

export function useDue(sessionId: string | null, all = false) {
  return useQuery({
    queryKey: ['due', sessionId, all],
    queryFn: () => api.due(sessionId!, all),
    enabled: !!sessionId,
  })
}

export function useRatingPending() {
  return useIsMutating({ mutationKey: ['review-rating'] }) > 0
}

export function useRate(reconcileQueue = false) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['review-rating'],
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
    onSuccess: (_result, { itemId, body }) => {
      if (!reconcileQueue) return
      qc.setQueriesData<Awaited<ReturnType<typeof api.due>>>({ queryKey: ['due', body.session_id] }, (old) =>
        old
          ? {
              ...old,
              items: old.items.filter((item) => item.item_id !== itemId),
              total_due: Math.max(
                0,
                old.total_due - (old.items.some((item) => item.item_id === itemId) ? 1 : 0),
              ),
            }
          : old,
      )
    },
  })
}
