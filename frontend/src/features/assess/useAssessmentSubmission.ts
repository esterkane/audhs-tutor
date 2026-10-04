import { useLayoutEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ApiError, apiFetch, type AttemptRequest, type AttemptResult, type Schemas } from '../../lib/api'

export const assessmentRecoveryKey = (session: string) => `assessment-request:v1:${session}`
type Submission = AttemptRequest & { questionLabel?: string; answerLabel?: string }
export type PendingAssessment = {
  version: 1
  id: string
  endpoint: string
  body: AttemptRequest
  question: string
  answerDisplay?: string
  rejectedContent?: boolean
}
const previousMemory = new Map<string, PendingAssessment[]>()
const previousKey = (session: string) => `assessment-previous-answer:v1:${session}`
function readPrevious(session: string): PendingAssessment[] {
  if (previousMemory.has(session)) return previousMemory.get(session) ?? []
  const raw = sessionStorage.getItem(previousKey(session))
  if (!raw) return []
  const parsed: unknown = JSON.parse(raw)
  const values = (Array.isArray(parsed) ? parsed : [parsed]) as PendingAssessment[]
  if (
    !values.every(
      (value) =>
        value?.version === 1 &&
        typeof value.id === 'string' &&
        value.body?.session_id === session &&
        typeof value.question === 'string' &&
        typeof value.body.answer === 'string',
    )
  )
    throw new Error('Previous answers could not be read.')
  return values
}
function loadPrevious(session: string): PendingAssessment[] {
  try {
    return readPrevious(session)
  } catch {
    return []
  }
}
const pageMemory = new Map<string, PendingAssessment | null>()
function write(session: string, value: PendingAssessment) {
  if (pageMemory.has(session)) pageMemory.set(session, value)
  else sessionStorage.setItem(assessmentRecoveryKey(session), JSON.stringify(value))
}
function remove(session: string) {
  if (pageMemory.has(session)) pageMemory.set(session, null)
  else sessionStorage.removeItem(assessmentRecoveryKey(session))
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
function read(session: string): PendingAssessment | null {
  if (pageMemory.has(session)) return pageMemory.get(session) ?? null
  const raw = sessionStorage.getItem(assessmentRecoveryKey(session))
  if (!raw) return null
  const value = JSON.parse(raw) as PendingAssessment
  if (
    value.version !== 1 ||
    !uuid.test(value.id) ||
    value.body?.session_id !== session ||
    typeof value.body.assessment_id !== 'string' ||
    typeof value.body.answer !== 'string' ||
    typeof value.question !== 'string' ||
    !['/api/assess/attempt', '/api/challenge/submit'].includes(value.endpoint)
  )
    throw new Error('Recovery information could not be read. No submission was sent.')
  return value
}
function load(session: string) {
  try {
    return { pending: read(session), error: '' }
  } catch {
    return {
      pending: null,
      error:
        'Recovery storage is unavailable or damaged. No new submission will be sent until it can be read.',
    }
  }
}

/** One unresolved grading intent per session/tab. Never regenerate from a lookup or timeout. */
export function useAssessmentSubmission(sessionId: string, endpoint = '/api/assess/attempt') {
  const key = assessmentRecoveryKey(sessionId)
  const [previousAnswers, setPreviousAnswers] = useState(() => loadPrevious(sessionId))
  const [scope, setScope] = useState(key)
  const [stored, setStored] = useState(() => load(sessionId))
  const [lookup, setLookup] = useState<Schemas['AssessmentRequestState'] | null>(null)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')
  const activeKey = useRef(key)
  const operation = useRef<AbortController | null>(null)
  if (scope !== key) {
    setScope(key)
    setPreviousAnswers(loadPrevious(sessionId))
    setStored(load(sessionId))
    setLookup(null)
    setError('')
    setChecking(false)
  }
  useLayoutEffect(() => {
    activeKey.current = key
    return () => {
      activeKey.current = ''
      operation.current?.abort()
      operation.current = null
    }
  }, [key])

  async function bounded<T>(work: (signal: AbortSignal) => Promise<T>): Promise<T> {
    if (operation.current) throw new Error('A submission or result check is already running.')
    const controller = new AbortController()
    operation.current = controller
    let timer: ReturnType<typeof setTimeout> | undefined
    let onAbort: (() => void) | undefined
    try {
      const result = await Promise.race([
        work(controller.signal),
        new Promise<never>((_, reject) => {
          onAbort = () => reject(new Error('Request interrupted. Check its result before submitting again.'))
          controller.signal.addEventListener('abort', onAbort, { once: true })
          timer = setTimeout(() => controller.abort(), 15000)
        }),
      ])
      if (operation.current !== controller || controller.signal.aborted || activeKey.current !== key)
        throw new Error('This result belongs to an earlier activity.')
      return result
    } finally {
      clearTimeout(timer)
      if (onAbort) controller.signal.removeEventListener('abort', onAbort)
      if (operation.current === controller) operation.current = null
    }
  }

  // Only these explicit pre-claim errors prove that no grading was started.
  function recordContentRejection(cause: unknown, pending: PendingAssessment) {
    if (
      activeKey.current !== key ||
      !(cause instanceof ApiError) ||
      cause.status !== 409 ||
      !['assessment_content_changed', 'assessment_content_required'].includes(cause.code)
    )
      return
    try {
      if (read(sessionId)?.id !== pending.id) return
      const rejected = { ...pending, rejectedContent: true }
      write(sessionId, rejected)
      setStored({ pending: rejected, error: '' })
      setLookup(null)
    } catch {
      // Keep the original identity if persistence fails; ordinary lookup stays safe.
      setError(
        'The question changed, but its recovery record could not be updated. Keep your answer and check the saved result.',
      )
    }
  }

  function clear() {
    if (operation.current) return
    try {
      const current = read(sessionId)
      if (current?.id !== stored.pending?.id) {
        setStored({ pending: current, error: '' })
        setLookup(null)
        setError('Recovery information changed in this session. Check the currently saved submission.')
        return
      }
      if (current?.rejectedContent) {
        // Preserve original wording/answer after refresh, including across reloads.
        // Failure to save the archive leaves the original recovery record intact.
        const archived = [...readPrevious(sessionId).filter((value) => value.id !== current.id), current]
        if (pageMemory.has(sessionId)) previousMemory.set(sessionId, archived)
        else sessionStorage.setItem(previousKey(sessionId), JSON.stringify(archived))
        setPreviousAnswers(archived)
      }
      remove(sessionId)
      setStored({ pending: null, error: '' })
      setLookup(null)
      setError('')
    } catch {
      setError('Recovery information could not be cleared. Keep your answer and try again.')
    }
  }

  const mutation = useMutation({
    mutationFn: async (submission: Submission) => {
      if (activeKey.current !== key) throw new Error('The session changed; your answer was not sent.')
      const previous = load(sessionId)
      setStored(previous)
      if (previous.error) throw new Error(previous.error)
      if (previous.pending)
        throw new Error('An earlier submission needs checking. Your current answer has not been sent.')
      const { questionLabel, answerLabel, ...body } = submission
      if (body.session_id !== sessionId) throw new Error('This answer belongs to another session.')
      const pending: PendingAssessment = {
        version: 1,
        id: crypto.randomUUID(),
        endpoint,
        body: { ...body },
        question: questionLabel ?? 'Assessment submission',
        answerDisplay: answerLabel ?? body.answer,
      }
      try {
        write(sessionId, pending)
      } catch {
        setStored({ pending: null, error: 'Recovery storage could not save this submission.' })
        throw new Error(
          'The recovery identity could not be saved. No answer was sent; keep your answer and retry.',
        )
      }
      setStored({ pending, error: '' })
      setLookup(null)
      setError('')
      let result: AttemptResult
      try {
        result = await bounded((signal) =>
          apiFetch<AttemptResult>(endpoint, {
            method: 'POST',
            body: JSON.stringify(pending.body),
            headers: { 'Idempotency-Key': pending.id },
            signal,
          }),
        )
      } catch (cause) {
        recordContentRejection(cause, pending)
        throw cause
      }
      if (result.assessment_id !== pending.body.assessment_id)
        throw new Error('The returned feedback belongs to another assessment.')
      // Successful delivery may clear the intent. On storage failure retain it for explicit lookup.
      try {
        if (read(sessionId)?.id === pending.id) remove(sessionId)
        setStored(load(sessionId))
      } catch {
        setError('Feedback arrived, but its recovery record could not be cleared.')
      }
      return result
    },
    retry: false,
  })

  async function check() {
    const pending = stored.pending
    if (!pending || operation.current) return
    setChecking(true)
    setError('')
    try {
      const result = await bounded((signal) =>
        apiFetch<Schemas['AssessmentRequestState']>(
          `/api/assess/requests/${pending.id}?session_id=${encodeURIComponent(sessionId)}`,
          { signal },
        ),
      )
      if (result.result && result.result.assessment_id !== pending.body.assessment_id)
        throw new Error('The saved result belongs to another assessment.')
      setLookup(result)
    } catch (cause) {
      if (activeKey.current === key) setError((cause as Error).message)
    } finally {
      if (activeKey.current === key) setChecking(false)
    }
  }

  async function resend() {
    const pending = stored.pending
    if (!pending || pending.rejectedContent || lookup?.status !== 'not_found' || operation.current) return
    setChecking(true)
    setError('')
    try {
      if (read(sessionId)?.id !== pending.id)
        throw new Error('Recovery information changed. Reload it before sending.')
      const result = await bounded((signal) =>
        apiFetch<AttemptResult>(pending.endpoint, {
          method: 'POST',
          headers: { 'Idempotency-Key': pending.id },
          body: JSON.stringify(pending.body),
          signal,
        }),
      )
      if (result.assessment_id !== pending.body.assessment_id)
        throw new Error('Mismatched assessment result.')
      setLookup({ status: 'completed', result })
    } catch (cause) {
      recordContentRejection(cause, pending)
      if (activeKey.current === key) setError((cause as Error).message)
    } finally {
      if (activeKey.current === key) setChecking(false)
    }
  }

  async function finish() {
    const pending = stored.pending
    if (!pending || lookup?.status !== 'grade_ready' || operation.current) return
    setChecking(true)
    setError('')
    try {
      if (read(sessionId)?.id !== pending.id)
        throw new Error('Recovery information changed. Reload it before saving.')
      const result = await bounded((signal) =>
        apiFetch<AttemptResult>(
          `/api/assess/requests/${pending.id}/finish?session_id=${encodeURIComponent(sessionId)}`,
          { method: 'POST', signal },
        ),
      )
      if (result.assessment_id !== pending.body.assessment_id)
        throw new Error('The saved feedback belongs to another assessment.')
      setLookup({ status: 'completed', result })
    } catch (cause) {
      // Content changes here do not prove the answer was never graded. Retain
      // the original identity and staged result rather than enabling regrading.
      if (activeKey.current === key) setError((cause as Error).message)
    } finally {
      if (activeKey.current === key) setChecking(false)
    }
  }

  return {
    ...mutation,
    recovery: {
      pending: stored.pending,
      previousAnswers,
      previousAnswer: previousAnswers.at(-1) ?? null,
      dismissPrevious: (id: string) => {
        try {
          const remaining = readPrevious(sessionId).filter((value) => value.id !== id)
          if (pageMemory.has(sessionId)) previousMemory.set(sessionId, remaining)
          else sessionStorage.setItem(previousKey(sessionId), JSON.stringify(remaining))
          setPreviousAnswers(remaining)
        } catch {
          setError('The previous answer could not be dismissed from storage.')
        }
      },
      stale: stored.pending?.rejectedContent === true,
      error: error || stored.error,
      lookup,
      checking: checking || mutation.isPending,
      check,
      resend,
      finish,
      clear,
      reload: () => setStored(load(sessionId)),
      memoryOnly: pageMemory.has(sessionId),
      continueInMemory: () => {
        if (operation.current) return
        let pending = stored.pending
        try {
          pending = read(sessionId)
        } catch {
          /* Preserve the last readable identity. */
        }
        previousMemory.set(sessionId, previousAnswers)
        pageMemory.set(sessionId, pending)
        setStored({ pending, error: '' })
        setError('')
      },
    },
  }
}
