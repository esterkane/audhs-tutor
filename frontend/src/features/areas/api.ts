import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'
export type Area = Schemas['AreaOut']
export function useAreas() {
  return useQuery({ queryKey: ['areas'], queryFn: () => apiFetch<Schemas['AreaList']>('/api/areas') })
}
export function useAreaJob() {
  return useQuery({
    queryKey: ['area-job'],
    queryFn: () => apiFetch<Schemas['AreaJobOut']>('/api/areas/draft-job/status'),
    refetchInterval: (q) => (q.state.data?.running ? 1500 : false),
  })
}
export function useAreaActions() {
  const qc = useQueryClient()
  const initialize = useMutation({
    mutationFn: () => apiFetch<Schemas['AreaList']>('/api/areas/initialize', { method: 'POST' }),
    onSuccess: (d) => qc.setQueryData(['areas'], d),
  })
  const edit = useMutation({
    mutationFn: ({ id, ...body }: Schemas['AreaEdit'] & { id: string }) =>
      apiFetch<Schemas['AreaList']>(`/api/areas/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: (d) => qc.setQueryData(['areas'], d),
  })
  const start = useMutation({
    mutationFn: (body?: { area_id: string; force_new: boolean }) =>
      apiFetch<Schemas['AreaJobOut']>('/api/areas/draft-job/start', {
        method: 'POST',
        body: JSON.stringify(body ?? {}),
      }),
    onSuccess: (d) => qc.setQueryData(['area-job'], d),
  })
  const stop = useMutation({
    mutationFn: () => apiFetch<Schemas['AreaJobOut']>('/api/areas/draft-job/stop', { method: 'POST' }),
    onSuccess: (d) => qc.setQueryData(['area-job'], d),
  })
  return { initialize, edit, start, stop }
}
export function useQuestionFeedback() {
  const qc = useQueryClient()
  const query = useQuery({
    queryKey: ['question-feedback'],
    queryFn: () => apiFetch<Schemas['FeedbackList']>('/api/areas/feedback/questions'),
  })
  const save = useMutation({
    mutationFn: (body: Schemas['FeedbackIn']) =>
      apiFetch<Schemas['FeedbackOut']>('/api/areas/feedback/questions', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['question-feedback'] })
    },
  })
  const withdraw = useMutation({
    mutationFn: (id: string) =>
      apiFetch<Schemas['FeedbackList']>(`/api/areas/feedback/questions/${id}`, { method: 'DELETE' }),
    onSuccess: (d) => qc.setQueryData(['question-feedback'], d),
  })
  const preference = useMutation({
    mutationFn: (body: Schemas['FeedbackPreference']) =>
      apiFetch<Schemas['FeedbackList']>('/api/areas/feedback/preferences', {
        method: 'PUT',
        body: JSON.stringify(body),
      }),
    onSuccess: (d) => {
      qc.setQueryData(['question-feedback'], d)
      void qc.invalidateQueries({ queryKey: ['preferences'] })
    },
  })
  return { query, save, withdraw, preference }
}
