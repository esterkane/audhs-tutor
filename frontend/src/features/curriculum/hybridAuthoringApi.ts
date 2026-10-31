import { boundedRead } from '../../lib/boundedRead'
import { useQuery } from '@tanstack/react-query'
import { type Schemas } from '../../lib/api'
export const useAuthoringSetup = () =>
  useQuery({
    queryKey: ['authoring-setup'],
    queryFn: ({signal}) => boundedRead<Schemas['AuthoringSetup']>('/api/authoring/setup', signal, 'Authoring settings'),
    retry: false,
  })
