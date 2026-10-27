import { useQuery } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

import { FocusContext } from './useFocusPolicy'

export function FocusPolicy({ children }: { children: React.ReactNode }) {
  const query = useQuery({
    queryKey: ['learning-focus'],
    retry: false,
    queryFn: () => apiFetch<Schemas['LearningFocusOut']>('/api/learning-focus'),
  })
  return (
    <FocusContext.Provider
      value={{ loaded: !query.isPending, error: query.isError, cutoff: query.data?.reference_before ?? null }}
    >
      {children}
    </FocusContext.Provider>
  )
}
