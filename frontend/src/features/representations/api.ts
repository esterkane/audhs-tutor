import { useMutation, useQuery } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type KindsOut = Schemas['KindsOut']
export type RenderOut = Schemas['RenderOut']

export function useKinds(skillId: string | null) {
  return useQuery({
    queryKey: ['rep-kinds', skillId],
    queryFn: () => apiFetch<KindsOut>(`/api/objects/${skillId}/representations`),
    enabled: !!skillId,
  })
}

export function useRender() {
  return useMutation({
    mutationFn: ({ skillId, kind, sessionId }: { skillId: string; kind: string; sessionId: string }) =>
      apiFetch<RenderOut>(`/api/objects/${skillId}/representations/${kind}`, {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId }),
      }),
  })
}

export function usePrefer() {
  return useMutation({
    mutationFn: ({
      skillId,
      sessionId,
      chosenId,
      rejectedId,
    }: {
      skillId: string
      sessionId: string
      chosenId: string
      rejectedId: string
    }) =>
      fetch(`/api/objects/${skillId}/representations/prefer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, chosen_id: chosenId, rejected_id: rejectedId }),
      }),
  })
}
