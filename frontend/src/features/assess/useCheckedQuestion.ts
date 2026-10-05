import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { AssessmentView, AttemptResult, Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'
import type { PendingAssessment } from './useAssessmentSubmission'

type Pointer = { version: 1; sessionId: string; requestId: string; attemptId: string; item: AssessmentView }
export const checkedQuestionKey = (scope: string) => `checked-question:v1:${scope}`
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
function read(scope: string, sessionId: string, skillId: string | null) {
  try {
    const raw = sessionStorage.getItem(checkedQuestionKey(scope))
    if (!raw) return { saved: null, error: '' }
    if (raw.length > 100000) throw new Error('Oversized return record')
    const saved = JSON.parse(raw) as Pointer
    const item = saved.item
    const strings = (value: unknown) =>
      value == null || (Array.isArray(value) && value.every((x) => typeof x === 'string'))
    if (
      saved.version !== 1 ||
      saved.sessionId !== sessionId ||
      !uuid.test(saved.requestId) ||
      typeof saved.attemptId !== 'string' ||
      !saved.attemptId ||
      !item ||
      typeof item.id !== 'string' ||
      !item.id ||
      item.skill_id !== skillId ||
      typeof item.question !== 'string' ||
      typeof item.kind !== 'string' ||
      typeof item.content_version !== 'string' ||
      !item.content_version ||
      typeof item.confidence_required !== 'boolean' ||
      !strings(item.options) ||
      !strings(item.criteria)
    )
      throw new Error('Invalid return record')
    return { saved, error: '' }
  } catch {
    return { saved: null, error: 'The checked-question return record could not be read. No answer was sent.' }
  }
}

/** A browser pointer to server evidence, never a cached grade or automatic resubmission. */
export function useCheckedQuestion(
  scope: string,
  sessionId: string,
  skillId: string | null,
  active: boolean,
) {
  const [initial] = useState(() => read(scope, sessionId, skillId))
  const [saved, setSaved] = useState(initial.saved)
  const [error, setError] = useState(initial.error)
  const result = useQuery({
    queryKey: ['checked-question', scope, saved?.requestId],
    enabled: active && !!saved,
    retry: false,
    refetchOnWindowFocus: false,
    queryFn: async ({ signal }) => {
      if (!saved) throw new Error('No checked question to restore.')
      const value = await boundedRead<Schemas['AssessmentRequestState']>(
        `/api/assess/requests/${encodeURIComponent(saved.requestId)}?session_id=${encodeURIComponent(sessionId)}`,
        signal,
        'Checked feedback',
      )
      if (value.status !== 'completed' || !value.result)
        throw new Error('The original checked feedback is unavailable. Nothing was graded again.')
      if (
        value.result.assessment_id !== saved.item.id ||
        value.result.attempt_id !== saved.attemptId ||
        value.result.skill_id !== skillId
      )
        throw new Error('The saved feedback does not match this question. Nothing was graded again.')
      return value.result
    },
  })
  function remember(pending: PendingAssessment, outcome: AttemptResult, item: AssessmentView) {
    if (
      pending.body.session_id !== sessionId ||
      pending.body.assessment_id !== item.id ||
      pending.body.content_version !== item.content_version ||
      outcome.assessment_id !== item.id ||
      item.skill_id !== skillId
    )
      return
    try {
      const raw = JSON.stringify({
        version: 1,
        sessionId,
        requestId: pending.id,
        attemptId: outcome.attempt_id,
        item,
      } satisfies Pointer)
      if (raw.length > 100000) throw new Error('Oversized return record')
      sessionStorage.setItem(checkedQuestionKey(scope), raw)
      setError('')
    } catch {
      setError(
        'Feedback is here, but its return record could not be saved. Open saved feedback before leaving.',
      )
    }
  }
  function clear() {
    try {
      sessionStorage.removeItem(checkedQuestionKey(scope))
      setSaved(null)
      setError('')
      return true
    } catch {
      setError('The return record could not be cleared. Your current question is kept.')
      return false
    }
  }
  return { saved, error, result, remember, clear }
}
