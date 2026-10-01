import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type ModelRow = Schemas['ModelRow']
export type JobOut = Schemas['JobOut']
export type RoutingOut = Schemas['RoutingOut']
export type AddIn = Schemas['AddIn']
export type CostsOut = Schemas['CostsOut']

export function useModels() {
  return useQuery({ queryKey: ['models'], queryFn: () => apiFetch<Schemas['ModelList']>('/api/models') })
}

export function useRouting() {
  return useQuery({
    queryKey: ['models', 'routing'],
    queryFn: () => apiFetch<RoutingOut>('/api/models/routing'),
  })
}

/** Polls every 2 s only while `active` and a job is still running; stops by itself otherwise. */
export function useJobs(active: boolean) {
  return useQuery({
    queryKey: ['models', 'jobs'],
    queryFn: () => apiFetch<Schemas['JobList']>('/api/models/jobs'),
    refetchInterval: (query) =>
      active && (query.state.data?.jobs ?? []).some((j) => j.status === 'running') ? 2000 : false,
  })
}

export function useSearchModels() {
  return useMutation({
    mutationFn: (p: { q: string; gguf: boolean; mlx: boolean }) =>
      apiFetch<Schemas['HfSearchOut']>(
        `/api/models/search?q=${encodeURIComponent(p.q)}&gguf=${p.gguf}&mlx=${p.mlx}&limit=20`,
      ),
  })
}

export function useModelActions() {
  const qc = useQueryClient()
  const invalidate = () => void qc.invalidateQueries({ queryKey: ['models'] })
  const add = useMutation({
    mutationFn: (body: AddIn) =>
      apiFetch<ModelRow>('/api/models', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: invalidate,
  })
  const pull = useMutation({
    mutationFn: (id: string) => apiFetch<JobOut>(`/api/models/${id}/pull`, { method: 'POST' }),
    onSuccess: invalidate,
  })
  const bench = useMutation({
    mutationFn: (id: string) => apiFetch<JobOut>(`/api/models/${id}/bench`, { method: 'POST' }),
    onSuccess: invalidate,
  })
  const assign = useMutation({
    mutationFn: ({ id, task }: { id: string; task: string }) =>
      apiFetch<RoutingOut>(`/api/models/${id}/assign`, { method: 'POST', body: JSON.stringify({ task }) }),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: string) => apiFetch<ModelRow>(`/api/models/${id}`, { method: 'DELETE' }),
    onSuccess: invalidate,
  })
  return { add, pull, bench, assign, remove }
}

/** P6 cost view: what the daily cap sees, split by how sure we are of each figure. */
export function useCosts(days = 1) {
  return useQuery({
    queryKey: ['models', 'costs', days],
    queryFn: () => apiFetch<CostsOut>(`/api/models/costs?days=${days}`),
  })
}
