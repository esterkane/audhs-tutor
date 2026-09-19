import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

export function useSession(sessionId: string | null) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => api.session(sessionId!),
    enabled: !!sessionId,
  })
}

export function useStartSession() {
  return useMutation({ mutationFn: api.startSession })
}

export function useEndSession() {
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string
      body: { energy_after: number; self_report: number; notes?: string }
    }) => api.endSession(id, body),
  })
}
