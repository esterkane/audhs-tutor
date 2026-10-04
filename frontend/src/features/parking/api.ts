import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type ParkOut = Schemas['ParkOut']

export function useParked(status: 'parked' | 'promoted' = 'parked') {
  return useQuery({
    queryKey: ['parking', status],
    queryFn: () => apiFetch<Schemas['ParkList']>(`/api/parking?status=${status}`),
  })
}

/** A deadline bounds the client wait, not server-side execution. Never retry mutations automatically. */
async function changeThought(path: string, body?: object): Promise<ParkOut> {
  const controller = new AbortController()
  let timer: ReturnType<typeof setTimeout> | undefined
  try {
    return await Promise.race([
      apiFetch<ParkOut>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined, signal: controller.signal }),
      new Promise<never>((_, reject) => { timer = setTimeout(() => { controller.abort(); reject(new Error('Thought action timed out')) }, 15000) }),
    ])
  } finally { clearTimeout(timer) }
}

export function useParkingActions() {
  const qc = useQueryClient()
  const invalidate = () => void qc.invalidateQueries({ queryKey: ['parking'] })
  const promote = useMutation({
    mutationFn: ({ id, to }: { id: string; to: string }) =>
      changeThought(`/api/parking/${encodeURIComponent(id)}/promote`, { promoted_to: to }),
    retry: false,
    onSettled: invalidate,
  })
  const drop = useMutation({
    mutationFn: (id: string) => changeThought(`/api/parking/${encodeURIComponent(id)}/drop`),
    retry: false,
    onSettled: invalidate,
  })
  return { promote, drop, invalidate }
}
