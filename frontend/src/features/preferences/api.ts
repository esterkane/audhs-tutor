import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type PrefOut = Schemas['PrefOut']

export function usePreferences() {
  return useQuery({ queryKey: ['preferences'], queryFn: () => apiFetch<PrefOut>('/api/preferences') })
}

export function useSetPreference() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { key: string; value: unknown }) =>
      apiFetch<PrefOut>('/api/preferences', { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: (data, variables) => {
      qc.setQueryData(['preferences'], data)
      if (variables.key.startsWith('goal.'))
        void qc.invalidateQueries({ predicate: (q) => q.queryKey[0] !== 'preferences' })
    },
  })
}
