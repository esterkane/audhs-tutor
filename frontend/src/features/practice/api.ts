import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type DueList, type Schemas } from '../../lib/api'

export type PracticeIn = Schemas['PracticeIn']
export type VocabIn = Schemas['VocabIn']

export function useActivities() {
  return useQuery({
    queryKey: ['practice', 'activities'],
    queryFn: () => apiFetch<Schemas['ActivitiesOut']>('/api/practice/activities'),
    staleTime: Infinity,
  })
}

export function useLogPractice() {
  return useMutation({
    mutationFn: (body: PracticeIn) =>
      apiFetch<Schemas['PracticeOut']>('/api/practice', { method: 'POST', body: JSON.stringify(body) }),
  })
}

export function useVocabDecks() {
  return useQuery({ queryKey: ['vocab'], queryFn: () => apiFetch<Schemas['DeckList']>('/api/vocab') })
}

export function useAddVocab() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: VocabIn) =>
      apiFetch<Schemas['VocabItemOut']>('/api/vocab', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['vocab'] })
      void qc.invalidateQueries({ queryKey: ['due'] })
    },
  })
}

/** Due language cards for the language block only (never mixed into the AI/ML review). */
export function useDueLanguage(sessionId: string | null) {
  return useQuery({
    queryKey: ['due', sessionId, 'language'],
    queryFn: () =>
      apiFetch<DueList>(
        `/api/review/due?session_id=${encodeURIComponent(sessionId!)}&domain=language&all=true`,
      ),
    enabled: sessionId !== null,
  })
}

export type ImportPreviewOut = Schemas['ImportPreviewOut']
export type ImportOut = Schemas['ImportOut']

export function useImportPreview() {
  return useMutation({
    mutationFn: (body: Schemas['ImportPreviewIn']) =>
      apiFetch<ImportPreviewOut>('/api/vocab/import/preview', { method: 'POST', body: JSON.stringify(body) }),
  })
}

export function useImportVocab() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Schemas['ImportIn']) =>
      apiFetch<ImportOut>('/api/vocab/import', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['vocab'] })
      void qc.invalidateQueries({ queryKey: ['due'] })
    },
  })
}
