import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'

export type PrefOut = Schemas['PrefOut']

export function usePreferences() {
  return useQuery({
    queryKey: ['preferences'],
    queryFn: ({ signal }) => boundedRead<PrefOut>('/api/preferences', signal, 'Preferences'),
    retry: false,
  })
}

export function useSetPreference() {
  const qc = useQueryClient()
  return useMutation({
    // A late read must not replace the successful save response in the shared cache.
    onMutate: () => qc.cancelQueries({ queryKey: ['preferences'] }),
    mutationFn: (body: { key: string; value: unknown }) =>
      apiFetch<PrefOut>('/api/preferences', { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: (data, variables) => {
      qc.setQueryData(['preferences'], data)
      if (variables.key.startsWith('goal.'))
        void qc.invalidateQueries({ predicate: (q) => q.queryKey[0] !== 'preferences' })
    },
  })
}
