import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type CorpusStats = Schemas['CorpusStats']
export type DocumentList = Schemas['DocumentList']
export type IngestRequest = Schemas['IngestRequest']
export type IngestOut = Schemas['IngestOut']
export type IngestJobRequest = Schemas['IngestJobRequest']
export type IngestJobOut = Schemas['IngestJobOut']
export type IngestRunOut = Schemas['IngestRunOut']
export type SearchRequest = Schemas['SearchRequest']
export type SearchOut = Schemas['SearchOut']
export type SearchHit = Schemas['SearchHit']
export type IngestCapabilities = Schemas['IngestCapabilities']

export function useCorpusStats() {
  return useQuery({
    queryKey: ['corpus', 'stats'],
    queryFn: () => apiFetch<CorpusStats>('/api/corpus/stats'),
  })
}

export function useCapabilities() {
  return useQuery({
    queryKey: ['corpus', 'capabilities'],
    queryFn: () => apiFetch<IngestCapabilities>('/api/corpus/capabilities'),
    staleTime: 60_000,
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

/** Background ingest (course-material stage 1): start, poll while it runs, cancel, resume. */
export function useStartIngestJob() {
  return useMutation({
    mutationFn: (body: IngestJobRequest) =>
      apiFetch<IngestJobOut>('/api/corpus/ingest/jobs', { method: 'POST', body: JSON.stringify(body) }),
  })
}

export function useIngestJob(jobId: string | null) {
  const qc = useQueryClient()
  return useQuery({
    queryKey: ['corpus', 'ingest-job', jobId],
    queryFn: async () => {
      const job = await apiFetch<IngestJobOut>(`/api/corpus/ingest/jobs/${jobId}`)
      if (job.status !== 'queued' && job.status !== 'running') {
        void qc.invalidateQueries({ queryKey: ['corpus', 'stats'] })
        void qc.invalidateQueries({ queryKey: ['corpus', 'documents'] })
        void qc.invalidateQueries({ queryKey: ['corpus', 'ingest-runs'] })
      }
      return job
    },
    enabled: jobId !== null,
    refetchInterval: (q) => {
      const st = q.state.data?.status
      return st === 'queued' || st === 'running' ? 1000 : false
    },
  })
}

export function useCancelIngestJob() {
  return useMutation({
    mutationFn: (jobId: string) =>
      apiFetch<IngestJobOut>(`/api/corpus/ingest/jobs/${jobId}/cancel`, { method: 'POST' }),
  })
}

export function useIngestRuns() {
  return useQuery({
    queryKey: ['corpus', 'ingest-runs'],
    queryFn: () => apiFetch<IngestRunOut[]>('/api/corpus/ingest/runs'),
  })
}
