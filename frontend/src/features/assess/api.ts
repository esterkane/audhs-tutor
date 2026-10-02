import { useAssessmentSubmission } from './useAssessmentSubmission'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

export function useNextItem(sessionId: string | null, skillId: string | null, key: number) {
  return useQuery({
    queryKey: ['assess-next', sessionId, skillId, key],
    queryFn: () => api.nextItem(sessionId!, skillId ?? undefined),
    enabled: !!sessionId,
  })
}

export function useAttempt(sessionId: string) {
  return useAssessmentSubmission(sessionId)
}
