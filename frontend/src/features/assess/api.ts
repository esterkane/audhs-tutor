import { useAssessmentSubmission, type PendingAssessment } from './useAssessmentSubmission'
import { useQuery } from '@tanstack/react-query'
import { api, type AttemptResult } from '../../lib/api'

export function useNextItem(sessionId: string | null, skillId: string | null, key: number, active = true) {
  return useQuery({
    queryKey: ['assess-next', sessionId, skillId, key],
    queryFn: () => api.nextItem(sessionId!, skillId ?? undefined),
    enabled: !!sessionId && active,
  })
}

export function useAttempt(
  sessionId: string,
  onDelivered?: (pending: PendingAssessment, result: AttemptResult) => void,
) {
  return useAssessmentSubmission(sessionId, '/api/assess/attempt', onDelivered)
}
