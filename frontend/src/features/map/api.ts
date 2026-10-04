import { useQuery } from '@tanstack/react-query'
import { type Schemas } from '../../lib/api'

import { boundedRead } from '../../lib/boundedRead'

export type MapOut = Schemas['MapOut']

export function useSkillMap() {
  return useQuery({
    queryKey: ['skill-map'],
    queryFn: ({ signal }) => boundedRead<MapOut>('/api/skills/map', signal, 'Skill map'),
    retry: false,
  })
}
