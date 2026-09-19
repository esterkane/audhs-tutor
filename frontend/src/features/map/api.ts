import { useQuery } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type MapOut = Schemas['MapOut']

export function useSkillMap() {
  return useQuery({ queryKey: ['skill-map'], queryFn: () => apiFetch<MapOut>('/api/skills/map') })
}
