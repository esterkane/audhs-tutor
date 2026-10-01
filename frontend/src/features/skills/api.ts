import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

export function useSkills() {
  return useQuery({ queryKey: ['skills'], queryFn: api.skills })
}
