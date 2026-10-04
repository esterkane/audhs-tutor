import { useQuery } from '@tanstack/react-query'
import { type Schemas } from '../../lib/api'

import { boundedRead } from '../../lib/boundedRead'

export type MapOut = Schemas['MapOut']

export function useSkillMap(areaId = '') {
  return useQuery({
    queryKey: ['skill-map', areaId],
    queryFn: ({ signal }) => boundedRead<MapOut>(`/api/skills/map${areaId ? `?area_id=${encodeURIComponent(areaId)}` : ''}`, signal, 'Skill map'),
    retry: false,
  })
}
