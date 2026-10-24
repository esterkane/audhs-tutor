import { useQuery } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'
export const useAuthoringSetup = () =>
  useQuery({
    queryKey: ['authoring-setup'],
    queryFn: () => apiFetch<Schemas['AuthoringSetup']>('/api/authoring/setup'),
  })
