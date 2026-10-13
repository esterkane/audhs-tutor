import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { boundedRead } from '../../lib/boundedRead'
import type { Schemas } from '../../lib/api'

type Draft = { version: 1; attemptId: string; answer: string | null; kind?: 'assessed' | 'provisional' }
export function useAssessmentRevision(scope: string, sessionId: string, attemptId: string | null, active: boolean, kind: 'assessed' | 'provisional' = 'assessed') {
  const key = `assessment-revision:v1:${scope}`
  const [initial] = useState(() => {
    try {
      const value = JSON.parse(sessionStorage.getItem(key) ?? 'null') as Draft | null
      if (value && (value.version !== 1 || typeof value.attemptId !== 'string' || !value.attemptId ||
        (value.kind !== undefined && !['assessed', 'provisional'].includes(value.kind)) ||
        !(value.answer === null || typeof value.answer === 'string' && value.answer.length <= 20000))) throw new Error('Invalid draft')
      return { draft: value, error: '' }
    } catch { return { draft: null, error: 'The revision draft could not be restored. Your checked feedback is kept.' } }
  })
  const [draft, setDraft] = useState<Draft | null>(initial.draft)
  const [storageError, setStorageError] = useState(initial.error)
  const editing = !!draft && draft.attemptId === attemptId && (draft.kind ?? 'assessed') === kind
  const source = useQuery({
    queryKey: ['assessment-revision', sessionId, kind, draft?.attemptId],
    enabled: active && editing,
    retry: false,
    refetchOnWindowFocus: false,
    queryFn: ({ signal }) => boundedRead<Schemas['AssessmentRevisionSource'] | Schemas['ProvisionalRevisionSource']>(
      `/api/assess/${kind === 'provisional' ? 'feedback' : 'attempts'}/${encodeURIComponent(draft!.attemptId)}/revision?session_id=${encodeURIComponent(sessionId)}`,
      signal, 'Your submitted answer',
    ),
  })
  const data = editing && source.isSuccess && !source.isFetching && (kind === 'provisional' ? 'feedback_id' in source.data && source.data.feedback_id === attemptId : 'attempt_id' in source.data && source.data.attempt_id === attemptId) ? source.data : null
  function save(value: Draft) {
    setDraft(value)
    try { sessionStorage.setItem(key, JSON.stringify(value)); setStorageError('') }
    catch { setStorageError('Your revision is kept on this screen, but could not be saved in this browser. Copy it before leaving.') }
  }
  function clear(force = false) {
    try { sessionStorage.removeItem(key); setStorageError('') }
    catch {
      setStorageError('The saved revision draft could not be cleared. Your work is kept.')
      if (!force) return false
    }
    setDraft(null)
    return true
  }
  return {
    editing, source, data, storageError,
    revisionRequest: data ? ('root_feedback_id' in data ? { revision_of_feedback_id: data.root_feedback_id } : { revision_of_attempt_id: data.root_attempt_id }) : {},
    answer: draft?.answer ?? data?.answer ?? '',
    start: () => { if (attemptId) save({ version: 1, attemptId, answer: null, kind }) },
    edit: (answer: string) => { if (draft) save({ ...draft, answer }) },
    clear,
  }
}
