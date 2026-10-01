import { useMutation, useQuery } from '@tanstack/react-query'
import { ApiError, apiFetch, type Schemas } from '../../lib/api'

export type ExerciseView = Schemas['ExerciseView']
export type HintOut = Schemas['HintOut']
export type SolutionOut = Schemas['SolutionOut']

/** The catalogue exercise for a skill; null when there is none (404). */
export function useExercise(skillId: string | null) {
  return useQuery({
    queryKey: ['exercise', skillId],
    queryFn: async (): Promise<ExerciseView | null> => {
      try {
        return await apiFetch<ExerciseView>(`/api/exercises/for-skill/${skillId}`)
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null
        throw e
      }
    },
    enabled: !!skillId,
    retry: false,
  })
}

export function useHint() {
  return useMutation({
    mutationFn: (p: { assessmentId: string; sessionId: string; level: number }) =>
      apiFetch<HintOut>(`/api/exercises/${p.assessmentId}/hint`, {
        method: 'POST',
        body: JSON.stringify({ session_id: p.sessionId, level: p.level }),
      }),
  })
}

export function useSolution() {
  return useMutation({
    mutationFn: (p: { assessmentId: string; sessionId: string }) =>
      apiFetch<SolutionOut>(`/api/exercises/${p.assessmentId}/solution`, {
        method: 'POST',
        body: JSON.stringify({ session_id: p.sessionId }),
      }),
  })
}
