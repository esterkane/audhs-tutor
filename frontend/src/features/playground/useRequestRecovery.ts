import { useRef, useState } from 'react'
import type { TutorRequest } from './api'
import type { Schemas, TurnRequest } from '../../lib/api'

export type FollowupRetryBody = Schemas['AnswerFollowup'] & { parent_answer_id: string }
export type PendingTutorRequest<T = TutorRequest> = {
  key: string
  body: T
  view: { snapshot: string; submitted: string; display: string; mode: 'explicit' | 'socratic' }
}
const memoryWarning =
  'Retry is kept only while this page stays open. Reload may show an older retry or lose these details. New work may make another model call.'
const warning =
  'Retry details could not be saved in this tab. Keep this page open; recovery after reload is unavailable.'

function read<T>(
  storageKey: string,
  validBody: (body: unknown) => body is T,
): {
  pending: PendingTutorRequest<T> | null
  error: string
  blocked: boolean
  inaccessible?: boolean
} {
  let raw: string | null
  try {
    raw = sessionStorage.getItem(storageKey)
  } catch {
    return {
      pending: null,
      error: 'Browser storage is inaccessible. You can explicitly continue without reload recovery.',
      blocked: true,
      inaccessible: true,
    }
  }
  try {
    if (!raw) return { pending: null, error: '', blocked: false }
    if (raw.length > 200000) throw new Error('Oversized retry record')
    const value = JSON.parse(raw) as PendingTutorRequest<T>
    if (
      !value ||
      !/^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(value.key) ||
      !validBody(value.body) ||
      !value.view ||
      !['snapshot', 'submitted', 'display'].every((k) => typeof value.view[k as 'snapshot'] === 'string') ||
      !['explicit', 'socratic'].includes(value.view.mode)
    )
      throw new Error('Invalid retry record')
    return { pending: value, error: '', blocked: false }
  } catch {
    return {
      pending: null,
      error:
        'Saved retry details could not be restored. Discard them explicitly before sending a new request.',
      blocked: true,
    }
  }
}

/** One unresolved request per surface. Retry storage is tab-local; normal tutor calls still send context. */
function useTypedRequestRecovery<T>(
  scope: string,
  validBody: (body: unknown) => body is T,
  persistent = true,
) {
  const storageKey = `tutor-request:v1:${scope}`
  const [initial] = useState(() =>
    persistent
      ? read(storageKey, validBody)
      : { pending: null, error: '', blocked: false, inaccessible: false },
  )
  const current = useRef(initial.pending)
  const blocked = useRef(initial.blocked)
  const memoryOnly = useRef(false)
  const [canUseMemoryOnly, setCanUseMemoryOnly] = useState(!!initial.inaccessible)
  const [pending, setPending] = useState(initial.pending)
  const [error, setError] = useState(initial.error)
  const [needsDiscard, setNeedsDiscard] = useState(initial.blocked)

  function prepare(body: T, view: PendingTutorRequest<T>['view']): PendingTutorRequest<T> {
    if (blocked.current)
      throw new Error('Discard the unreadable retry details before starting a new request.')
    // Freeze exactly what is sent; optional undefined fields disappear as on the HTTP wire.
    const frozen = JSON.parse(JSON.stringify(body)) as T
    if (current.current) {
      if (JSON.stringify(current.current.body) === JSON.stringify(frozen)) return current.current
      throw new Error(
        'An earlier request has no confirmed result. Retry it, or discard its retry before sending different work.',
      )
    }
    const next = { key: crypto.randomUUID(), body: frozen, view: { ...view } }
    current.current = next
    setPending(next)
    if (!persistent) return next
    if (memoryOnly.current) {
      setError(memoryWarning)
      return next
    }
    try {
      const encoded = JSON.stringify(next)
      if (encoded.length > 200000) throw new Error('Oversized retry record')
      sessionStorage.setItem(storageKey, encoded)
    } catch {
      setError(warning)
    }
    return next
  }

  function accept(key: string) {
    if (current.current?.key !== key) return
    try {
      if (persistent && !memoryOnly.current) sessionStorage.removeItem(storageKey)
    } catch {
      current.current = null
      blocked.current = true
      setPending(null)
      setNeedsDiscard(true)
      setCanUseMemoryOnly(true)
      setError(
        'The reply was received, but saved retry details could not be cleared. Reload may show the old retry. Clear those details before starting another request.',
      )
      return
    }
    current.current = null
    setPending(null)
    setError(memoryOnly.current ? memoryWarning : '')
  }

  function discard(key?: string) {
    if (key && current.current?.key !== key) return
    // Clear disk first. Failure cannot make the next request silently replace this identity.
    try {
      if (persistent && !memoryOnly.current) sessionStorage.removeItem(storageKey)
    } catch {
      setCanUseMemoryOnly(true)
      setError('Retry details could not be removed. Keep this page open; retry will reuse the same request.')
      return
    }
    current.current = null
    blocked.current = false
    setPending(null)
    setNeedsDiscard(false)
    setError(memoryOnly.current ? memoryWarning : '')
  }

  function continueInMemory() {
    // Explicit learner choice: never silently discard an identity that may already have run.
    memoryOnly.current = true
    current.current = null
    blocked.current = false
    setPending(null)
    setNeedsDiscard(false)
    setCanUseMemoryOnly(false)
    setError(memoryWarning)
  }

  return { pending, error, needsDiscard, canUseMemoryOnly, continueInMemory, prepare, accept, discard }
}

function workspaceBody(body: unknown): body is TutorRequest {
  if (!body || typeof body !== 'object') return false
  const value = body as TutorRequest
  return (
    typeof value.session_id === 'string' &&
    typeof value.exercise === 'string' &&
    typeof value.code === 'string' &&
    (value.history === undefined ||
      (Array.isArray(value.history) &&
        value.history.length <= 6 &&
        value.history.every(
          (message) =>
            message && ['user', 'assistant'].includes(message.role) && typeof message.text === 'string',
        )))
  )
}
function followupBody(body: unknown): body is FollowupRetryBody {
  if (!body || typeof body !== 'object') return false
  const value = body as FollowupRetryBody
  return (
    typeof value.session_id === 'string' &&
    typeof value.parent_answer_id === 'string' &&
    value.parent_answer_id.length > 0 &&
    value.parent_answer_id.length <= 128 &&
    typeof value.question === 'string' &&
    !!value.question.trim() &&
    value.question.length <= 2000
  )
}
export function useRequestRecovery(scope: string) {
  return useTypedRequestRecovery(scope, workspaceBody)
}
export function useFollowupRequestRecovery(scope: string) {
  return useTypedRequestRecovery(scope, followupBody)
}

function lessonBody(body: unknown): body is TurnRequest {
  if (!body || typeof body !== 'object') return false
  const value = body as TurnRequest
  return (
    typeof value.session_id === 'string' &&
    typeof value.text === 'string' &&
    value.text.length > 0 &&
    value.text.length <= 4000 &&
    (value.skill_id == null || typeof value.skill_id === 'string')
  )
}
export function useLessonRequestRecovery(scope: string, persistent = true) {
  return useTypedRequestRecovery(scope, lessonBody, persistent)
}
