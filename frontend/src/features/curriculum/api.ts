import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { boundedRead } from '../../lib/boundedRead'
import { apiFetch, type Schemas } from '../../lib/api'

export type MaterialList = Schemas['MaterialList']
export type SectionList = Schemas['SectionList']
export type DraftOut = Schemas['DraftOut']
export type DraftList = Schemas['DraftList']
export type PublishOut = Schemas['PublishOut']
export type ChunkOut = Schemas['ChunkOut']
export type ReportIn = Schemas['ReportIn']
export type ReportOut = Schemas['ReportOut']
export type SourceList = Schemas['CourseSourceList']
export type SourceOut = Schemas['CourseSourceOut']
export type SourceRoleOut = Schemas['CourseSourceRoleOut']

export function useMaterial() {
  return useQuery({
    queryKey: ['curriculum', 'material'],
    queryFn: () => apiFetch<MaterialList>('/api/curriculum/material'),
  })
}

export function useSections(course: string | null) {
  return useQuery({
    queryKey: ['curriculum', 'sections', course],
    queryFn: () => apiFetch<SectionList>(`/api/curriculum/sections?course=${encodeURIComponent(course!)}`),
    enabled: !!course,
  })
}

export function useDrafts() {
  return useQuery({
    queryKey: ['curriculum', 'drafts'],
    queryFn: () => apiFetch<DraftList>('/api/curriculum/drafts'),
  })
}

export function useDraftActions() {
  const qc = useQueryClient()
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['curriculum'] })
    void qc.invalidateQueries({ queryKey: ['areas'] })
    void qc.invalidateQueries({ queryKey: ['skills'] })
    void qc.invalidateQueries({ queryKey: ['session-current'] })
  }
  const create = useMutation({
    mutationFn: (body: { course: string; section: string | null; use_model?: boolean }) =>
      apiFetch<DraftOut>('/api/curriculum/drafts', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: invalidate,
  })
  const update = useMutation({
    mutationFn: ({ id, payload, expected_version }: { id: string; payload: DraftOut['payload']; expected_version: number }) =>
      apiFetch<DraftOut>(`/api/curriculum/drafts/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ payload, expected_version }),
      }),
    onSuccess: invalidate,
  })
  const publish = useMutation({
    mutationFn: ({ id, expected_version }: { id: string; expected_version: number }) =>
      apiFetch<PublishOut>(`/api/curriculum/drafts/${id}/publish`, { method: 'POST', body: JSON.stringify({ expected_version }) }),
    onSuccess: invalidate,
  })
  const reject = useMutation({
    mutationFn: ({ id, expected_version }: { id: string; expected_version: number }) => apiFetch<DraftOut>(`/api/curriculum/drafts/${id}/reject`, { method: 'POST', body: JSON.stringify({ expected_version }) }),
    onSuccess: invalidate,
  })
  const refresh = useMutation({
    mutationFn: (id: string) => boundedRead<DraftOut>(`/api/curriculum/drafts/${id}`, new AbortController().signal, 'Latest draft'),
    onSuccess: () => {
      update.reset()
      publish.reset()
      reject.reset()
      invalidate()
    },
  })
  return { create, update, publish, reject, refresh }
}

export function useChunk(chunkId: string | null) {
  return useQuery({
    queryKey: ['curriculum', 'chunk', chunkId],
    queryFn: ({ signal }) => boundedRead<ChunkOut>(`/api/curriculum/chunks/${encodeURIComponent(chunkId ?? "")}`, signal, 'Source passage'),
    enabled: !!chunkId,
    retry: false,
  })
}

export function useReport() {
  return useMutation({
    mutationFn: (body: ReportIn) =>
      apiFetch<ReportOut>('/api/curriculum/reports', { method: 'POST', body: JSON.stringify(body) }),
  })
}

/** Course curation (stage 3): what each document is for its course — owner decision or suggestion. */
export function useSources(course: string | null) {
  return useQuery({
    queryKey: ['curriculum', 'sources', course],
    queryFn: () => apiFetch<SourceList>(`/api/curriculum/sources?course=${encodeURIComponent(course!)}`),
    enabled: !!course,
  })
}

export function useSourceRole() {
  const qc = useQueryClient()
  const invalidate = () => void qc.invalidateQueries({ queryKey: ['curriculum', 'sources'] })
  const set = useMutation({
    mutationFn: ({
      course,
      documentId,
      role,
      reason,
    }: {
      course: string
      documentId: string
      role: string
      reason?: string
    }) =>
      apiFetch<SourceRoleOut>(`/api/curriculum/sources/${documentId}?course=${encodeURIComponent(course)}`, {
        method: 'PUT',
        body: JSON.stringify({ role, reason: reason ?? '' }),
      }),
    onSuccess: invalidate,
  })
  const reset = useMutation({
    mutationFn: ({ course, documentId }: { course: string; documentId: string }) =>
      apiFetch<SourceRoleOut>(`/api/curriculum/sources/${documentId}?course=${encodeURIComponent(course)}`, {
        method: 'DELETE',
      }),
    onSuccess: invalidate,
  })
  return { set, reset }
}
