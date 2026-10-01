import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type LessonSummary = Schemas['LessonSummary']
export type LessonOut = Schemas['LessonOut']
export type TaskOut = Schemas['TaskOut']

export function useListeningLessons() {
  return useQuery({
    queryKey: ['listening', 'lessons'],
    queryFn: () => apiFetch<Schemas['LessonList']>('/api/listening/lessons'),
  })
}

export function useLesson(documentId: string | null) {
  return useQuery({
    queryKey: ['listening', 'lesson', documentId],
    queryFn: () => apiFetch<LessonOut>(`/api/listening/lessons/${documentId}`),
    enabled: !!documentId,
  })
}

/** The task for one clip: created once on the server (model proposal or source-cut cloze). */
export function useClipTask() {
  return useMutation({
    mutationFn: (p: { documentId: string; index: number; sessionId: string; useModel?: boolean }) =>
      apiFetch<TaskOut>(`/api/listening/lessons/${p.documentId}/sections/${p.index}/task`, {
        method: 'POST',
        body: JSON.stringify({ session_id: p.sessionId, use_model: p.useModel ?? true }),
      }),
  })
}

/** Exposure log: playing a clip is never evidence. */
export function useListened() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (p: {
      documentId: string
      index: number
      sessionId: string
      chunkId: string
      replays: number
      seconds: number
    }) =>
      apiFetch<void>(`/api/listening/lessons/${p.documentId}/sections/${p.index}/listened`, {
        method: 'POST',
        body: JSON.stringify({
          session_id: p.sessionId,
          chunk_id: p.chunkId,
          replays: p.replays,
          seconds: p.seconds,
        }),
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['listening'] }),
  })
}

/** The review path for a model-proposed question: the learner marks it as checked. */
export function useValidateTask() {
  return useMutation({
    mutationFn: (p: { assessmentId: string; validated: boolean }) =>
      apiFetch<TaskOut>(`/api/listening/tasks/${p.assessmentId}/validate`, {
        method: 'POST',
        body: JSON.stringify({ validated: p.validated }),
      }),
  })
}
