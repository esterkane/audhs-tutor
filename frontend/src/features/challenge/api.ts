import { useMutation, useQuery } from '@tanstack/react-query'
import { apiFetch, type AttemptRequest, type AttemptResult, type Schemas } from '../../lib/api'

export type ChallengeView = Schemas['ChallengeView']
export type ChallengeMode = Schemas['ChallengeStart']['mode']

export function useChallengeModes() {
  return useQuery({
    queryKey: ['challenge-modes'],
    queryFn: () => apiFetch<{ modes: { mode: string; hint: string }[] }>('/api/challenge/modes'),
  })
}

export function useChallengeStart() {
  return useMutation({
    mutationFn: (body: { session_id: string; mode: ChallengeMode; skill_id?: string | null }) =>
      apiFetch<ChallengeView>('/api/challenge/start', { method: 'POST', body: JSON.stringify(body) }),
  })
}

export function useChallengeSubmit() {
  return useMutation({
    mutationFn: (body: AttemptRequest) =>
      apiFetch<AttemptResult>('/api/challenge/submit', { method: 'POST', body: JSON.stringify(body) }),
  })
}
