import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type ProposalOut = Schemas['ProposalOut']
export type HistoryOut = Schemas['HistoryOut']
export type Decision = Schemas['DecideIn']['decision']

export function usePendingAdaptations() {
  return useQuery({
    queryKey: ['adaptations', 'pending'],
    queryFn: () => apiFetch<Schemas['ProposalList']>('/api/adaptations'),
  })
}

/** The adaptation log: every card and what happened to it. Every change the system made is here,
 *  with an undo affordance (AuDHD invariant: no covert adaptation). */
export function useAdaptationLog() {
  const qc = useQueryClient()
  const log = useQuery({
    queryKey: ['adaptations', 'log'],
    queryFn: () => apiFetch<Schemas['HistoryList']>('/api/adaptations/log'),
  })
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['adaptations'] })
    void qc.invalidateQueries({ queryKey: ['preferences'] })
    void qc.invalidateQueries({ queryKey: ['session'] }) // a plan card changes the session's blocks
  }
  const decide = useMutation({
    mutationFn: ({ id, decision, sessionId }: { id: string; decision: Decision; sessionId: string | null }) =>
      apiFetch<Schemas['HistoryList']>(`/api/adaptations/${id}/decide`, {
        method: 'POST',
        body: JSON.stringify({ decision, session_id: sessionId }),
      }),
    onSuccess: invalidate,
  })
  const undo = useMutation({
    mutationFn: (id: string) =>
      apiFetch<Schemas['HistoryList']>(`/api/adaptations/${id}/undo`, { method: 'POST' }),
    onSuccess: invalidate,
  })
  return { log, decide, undo }
}
