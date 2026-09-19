import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type CorpusStats = Schemas['CorpusStats']
export type DocumentList = Schemas['DocumentList']
export type IngestRequest = Schemas['IngestRequest']
export type IngestOut = Schemas['IngestOut']
export type SearchRequest = Schemas['SearchRequest']
export type SearchOut = Schemas['SearchOut']
export type SearchHit = Schemas['SearchHit']

export function useCorpusStats() {
  return useQuery({
    queryKey: ['corpus', 'stats'],
    queryFn: () => apiFetch<CorpusStats>('/api/corpus/stats'),
  })
}

export function useDocuments(course: string | null) {
  return useQuery({
    queryKey: ['corpus', 'documents', course],
    queryFn: () =>
      apiFetch<DocumentList>(`/api/corpus/documents${course ? `?course=${encodeURIComponent(course)}` : ''}`),
    enabled: course !== null,
  })
}

export function useIngest() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: IngestRequest) =>
      apiFetch<IngestOut>('/api/corpus/ingest', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['corpus'] }),
  })
}

export function useSearch() {
  return useMutation({
    mutationFn: (body: SearchRequest) =>
      apiFetch<SearchOut>('/api/corpus/search', { method: 'POST', body: JSON.stringify(body) }),
  })
}

export function useForgetDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (documentId: string) =>
      apiFetch<Schemas['ForgetOut']>(`/api/corpus/documents/${documentId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['corpus'] }),
  })
}

export function useRetierDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ documentId, trust_tier }: { documentId: string; trust_tier: number }) =>
      apiFetch<Schemas['DocumentOut']>(`/api/corpus/documents/${documentId}`, {
        method: 'PATCH',
        body: JSON.stringify({ trust_tier }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['corpus'] }),
  })
}
