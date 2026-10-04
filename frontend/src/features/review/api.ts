import { useReviewSubmission } from './useReviewSubmission'
import { useQuery, useIsMutating } from '@tanstack/react-query'
import type { DueList } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'

export function useDue(sessionId: string | null, all = false) {
  return useQuery({
    queryKey: ['due', sessionId, all],
    queryFn: ({ signal }) =>
      boundedRead<DueList>(
        `/api/review/due?session_id=${encodeURIComponent(sessionId!)}${all ? '&all=true' : ''}`,
        signal,
        'Review cards',
      ),
    retry: false,
    enabled: !!sessionId,
  })
}

export function useRatingPending() {
  return useIsMutating({ mutationKey: ['review-rating'] }) > 0
}

export function useRate(sessionId: string, reconcileQueue = false) {
  return useReviewSubmission(sessionId, reconcileQueue)
}
