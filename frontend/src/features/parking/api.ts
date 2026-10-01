import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type ParkOut = Schemas['ParkOut']

export function useParked(status: 'parked' | 'promoted' = 'parked') {
  return useQuery({
    queryKey: ['parking', status],
    queryFn: () => apiFetch<Schemas['ParkList']>(`/api/parking?status=${status}`),
  })
}

export function useParkingActions() {
  const qc = useQueryClient()
  const invalidate = () => void qc.invalidateQueries({ queryKey: ['parking'] })
  const promote = useMutation({
    mutationFn: ({ id, to }: { id: string; to: string }) =>
      apiFetch<ParkOut>(`/api/parking/${id}/promote`, {
        method: 'POST',
        body: JSON.stringify({ promoted_to: to }),
      }),
    onSuccess: invalidate,
  })
  const drop = useMutation({
    mutationFn: (id: string) => apiFetch<ParkOut>(`/api/parking/${id}/drop`, { method: 'POST' }),
    onSuccess: invalidate,
  })
  return { promote, drop, invalidate }
}
