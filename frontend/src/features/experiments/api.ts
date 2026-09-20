import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type ExperimentOut = Schemas['ExperimentOut']
export type ResultsOut = Schemas['ResultsOut']
export type MetricOut = Schemas['MetricOut']

export function useExperiments() {
  return useQuery({
    queryKey: ['experiments'],
    queryFn: () => apiFetch<Schemas['ExperimentList']>('/api/experiments'),
  })
}

export function useResults(id: string | null) {
  return useQuery({
    queryKey: ['experiments', id, 'results'],
    queryFn: () => apiFetch<ResultsOut>(`/api/experiments/${id}/results`),
    enabled: id !== null,
  })
}

export function useExperimentActions() {
  const qc = useQueryClient()
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['experiments'] })
    void qc.invalidateQueries({ queryKey: ['session'] })
  }
  const fromTemplate = useMutation({
    mutationFn: (template: string) =>
      apiFetch<ExperimentOut>('/api/experiments/from-template', {
        method: 'POST',
        body: JSON.stringify({ template }),
      }),
    onSuccess: invalidate,
  })
  const start = useMutation({
    mutationFn: (id: string) => apiFetch<ExperimentOut>(`/api/experiments/${id}/start`, { method: 'POST' }),
    onSuccess: invalidate,
  })
  const stop = useMutation({
    mutationFn: (id: string) => apiFetch<ExperimentOut>(`/api/experiments/${id}/stop`, { method: 'POST' }),
    onSuccess: invalidate,
  })
  return { fromTemplate, start, stop }
}
