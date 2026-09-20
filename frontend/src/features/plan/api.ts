import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type Block = Schemas['Block']
export type BlockOut = Schemas['BlockOut']
export type BlockEvent = Schemas['BlockEvent']

export function useBlockStart() {
  return useMutation({
    mutationFn: (body: BlockEvent) =>
      apiFetch<BlockOut>('/api/plan/blocks/start', { method: 'POST', body: JSON.stringify(body) }),
  })
}

export function useBlockEnd() {
  return useMutation({
    mutationFn: (body: BlockEvent) =>
      apiFetch<BlockOut>('/api/plan/blocks/end', { method: 'POST', body: JSON.stringify(body) }),
  })
}

export const BLOCK_LABELS: Record<string, string> = {
  movement_primer: 'Move',
  retrieval: 'Warm-up review',
  new_material: 'New material',
  challenge: 'Challenge',
  interleaved_review: 'Interleaved review',
  domain_switch: 'Other domain',
  recap: 'Recap',
}

export function useReplan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { session_id: string; energy: number; from_index: number }) =>
      apiFetch<Schemas['ReplanOut']>('/api/plan/replan', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['adaptations'] })
      void qc.invalidateQueries({ queryKey: ['session'] })
    },
  })
}
