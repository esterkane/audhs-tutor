import { useReviewSubmission } from './useReviewSubmission'
import { useQuery, useIsMutating } from '@tanstack/react-query'
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

export function useRate(sessionId: string, reconcileQueue = false) {
  return useReviewSubmission(sessionId, reconcileQueue)
}
