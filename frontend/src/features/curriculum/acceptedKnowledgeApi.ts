import { useQuery } from '@tanstack/react-query'
import { type Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'

export function useAcceptedKnowledge(skillId: string | null) {
  return useQuery({ queryKey:['accepted-knowledge',skillId], enabled:!!skillId, retry:false,
    queryFn:({ signal }) => boundedRead<Schemas['KnowledgeReadingOut'] | null>(`/api/knowledge-material/skills/${encodeURIComponent(skillId!)}/reading`, signal, 'Accepted knowledge material') })
}
