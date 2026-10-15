import { validBrief } from '../ask/conversationBrief'
import { validLessonBody, type LessonBody } from '../ask/lessonDraft'
import { applyVisualEdits, editableFields, type visualSaveBody } from '../ask/visualEditing'
import { useRef, useState } from 'react'
import type { TutorRequest } from './api'
import type { Schemas, TurnRequest } from '../../lib/api'

export type FollowupRetryBody = Omit<Schemas['AnswerFollowup'], 'purpose'> & {
  parent_answer_id: string
  purpose?: Schemas['AnswerFollowup']['purpose']
}
export type PendingTutorRequest<T = TutorRequest> = {
  key: string
  body: T
  view: { snapshot: string; submitted: string; display: string; mode: 'explicit' | 'socratic' }
}
// Ask keeps failed retry writes across in-tab navigation; never automatically submits them.
const askFallback = new Map<string, PendingTutorRequest<unknown> | null>()
const askMemoryWarning =
  'Retry identity is retained while navigating in this tab. Reload recovery may be unavailable.'
const memoryWarning =
  'Retry is kept only while this page stays open. Reload may show an older retry or lose these details. New work may make another model call.'
const warning =
  'Retry details could not be saved in this tab. Keep this page open; recovery after reload is unavailable.'

function read<T>(
  storageKey: string,
  validBody: (body: unknown) => body is T,
  retainInMemory = false,
): {
  pending: PendingTutorRequest<T> | null
  error: string
  blocked: boolean
  inaccessible?: boolean
} {
  if (retainInMemory && askFallback.has(storageKey)) {
    const entry = askFallback.get(storageKey)
    if (entry == null) return { pending: null, error: askMemoryWarning, blocked: false }
    if (validBody(entry.body))
      return { pending: { ...entry, body: entry.body }, error: askMemoryWarning, blocked: false }
    return { pending: null, error: 'Retry details are invalid. Discard them explicitly.', blocked: true }
  }
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
  retainInMemory = false,
) {
  const storageKey = `tutor-request:v1:${scope}`
  const [initial] = useState(() =>
    persistent
      ? read(storageKey, validBody, retainInMemory)
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
      if (retainInMemory) askFallback.set(storageKey, next)
      setError(retainInMemory ? askMemoryWarning : memoryWarning)
      return next
    }
    try {
      const encoded = JSON.stringify(next)
      if (encoded.length > 200000) throw new Error('Oversized retry record')
      sessionStorage.setItem(storageKey, encoded)
      if (retainInMemory) askFallback.delete(storageKey)
    } catch {
      if (retainInMemory) askFallback.set(storageKey, next)
      setError(retainInMemory ? askMemoryWarning : warning)
    }
    return next
  }

  function accept(key: string) {
    if (current.current?.key !== key) return
    if (retainInMemory) askFallback.set(storageKey, null)
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
    if (retainInMemory && !memoryOnly.current) askFallback.delete(storageKey)
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
    if (retainInMemory) {
      if (memoryOnly.current) askFallback.set(storageKey, null)
      else askFallback.delete(storageKey)
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
    if (retainInMemory) askFallback.set(storageKey, null)
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
    value.question.length <= 2000 &&
    (value.purpose === undefined || ['followup', 'correction'].includes(value.purpose))
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

export function useAskRequestRecovery(scope: string) {
  return useTypedRequestRecovery<Schemas['AskQuestion']>(
    scope,
    (body): body is Schemas['AskQuestion'] => {
      if (!body || typeof body !== 'object') return false
      const value = body as Schemas['AskQuestion']
      const sources = value.sources
      const validSources =
        sources == null ||
        (Array.isArray(sources.passage_ids) &&
          sources.passage_ids.length > 0 &&
          sources.passage_ids.length <= 6 &&
          sources.passage_ids.every((id) => typeof id === 'string' && id.length > 0 && id.length <= 128) &&
          new Set(sources.passage_ids).size === sources.passage_ids.length &&
          !!sources.passage_hashes &&
          Object.keys(sources.passage_hashes).length === sources.passage_ids.length &&
          sources.passage_ids.every((id) => /^[a-f0-9]{64}$/.test(sources.passage_hashes[id] ?? '')))
      return (
        validSources &&
        (value.conversation_brief == null || validBrief(value.conversation_brief)) &&
        typeof value.question === 'string' &&
        !!value.question.trim() &&
        value.question.length <= 2000 &&
        [value.area_id, value.parent_answer_id].every(
          (v) => v == null || (typeof v === 'string' && v.length > 0 && v.length <= 128),
        )
      )
    },
    true,
    true,
  )
}

export function useAnswerCheckRecovery(scope: string) {
  return useTypedRequestRecovery<Schemas['AnswerCheckRequest']>(
    scope,
    (body): body is Schemas['AnswerCheckRequest'] => {
      if (!body || typeof body !== 'object') return false
      const value = body as Schemas['AnswerCheckRequest']
      return (
        typeof value.answer_id === 'string' &&
        value.answer_id.length > 0 &&
        value.answer_id.length <= 128 &&
        Array.isArray(value.passage_ids) &&
        value.passage_ids.length > 0 &&
        value.passage_ids.length <= 6 &&
        value.passage_ids.every((id) => typeof id === 'string' && id.length > 0 && id.length <= 128) &&
        new Set(value.passage_ids).size === value.passage_ids.length &&
        !!value.passage_hashes &&
        Object.keys(value.passage_hashes).length === value.passage_ids.length &&
        value.passage_ids.every((id) => /^[a-f0-9]{64}$/.test(value.passage_hashes[id] ?? ''))
      )
    },
    true,
    true,
  )
}

export type VisualGenerationBody = { binding: Schemas['AnswerVisualBinding'] }
export function useVisualRequestRecovery(scope: string) {
  return useTypedRequestRecovery<VisualGenerationBody>(scope, (body): body is VisualGenerationBody => {
    if (!body || typeof body !== 'object') return false
    const binding = (body as VisualGenerationBody).binding
    return !!binding && binding.schema_version === 'answer-visual-binding.v1'
      && typeof binding.answer_id === 'string' && binding.answer_id.length > 0 && binding.answer_id.length <= 128
      && [binding.question_sha256, binding.answer_sha256, binding.lineage_sha256].every(hash => typeof hash === 'string' && /^[a-f0-9]{64}$/.test(hash))
      && (binding.learning_purpose == null || (typeof binding.learning_purpose === 'string' && binding.learning_purpose.length <= 4000))
  }, true, true)
}

export type VisualReviewBody = {
  action: 'review'; document_id: string; expected_revision: number; version_id: string;
  content_sha256: string; snapshot_sha256: string; decision: 'accept' | 'reject'; confirm: true; note: string
}
export function useVisualReviewRecovery(scope: string) {
  const recovery = useTypedRequestRecovery<VisualReviewBody>(scope, (body): body is VisualReviewBody => {
    if (!body || typeof body !== 'object') return false
    const value = body as VisualReviewBody
    return value.action === 'review' && value.confirm === true
      && ['accept', 'reject'].includes(value.decision)
      && [value.document_id, value.version_id].every(id => typeof id === 'string' && id.length > 0 && id.length <= 128)
      && Number.isInteger(value.expected_revision) && value.expected_revision >= 1
      && [value.content_sha256, value.snapshot_sha256].every(hash => typeof hash === 'string' && /^[a-f0-9]{64}$/.test(hash))
      && typeof value.note === 'string' && value.note.length <= 4000
  }, true, true)
  return { ...recovery, error: recovery.error.replaceAll('model call', 'saved review') }
}

export type VisualArchiveBody = { action: 'archive'; document_id: string; expected_revision: number; archived: boolean }
export function useVisualArchiveRecovery(scope: string) {
  const recovery = useTypedRequestRecovery<VisualArchiveBody>(scope, (body): body is VisualArchiveBody => {
    if (!body || typeof body !== 'object') return false
    const value = body as VisualArchiveBody
    return value.action === 'archive' && typeof value.document_id === 'string'
      && value.document_id.length > 0 && value.document_id.length <= 128
      && Number.isInteger(value.expected_revision) && value.expected_revision >= 1
      && typeof value.archived === 'boolean'
  }, true, true)
  return { ...recovery, error: recovery.error.replaceAll('model call', 'archive change') }
}

export function useVisualSaveRecovery(scope: string, documentId: string, version: Schemas['VisualVersionDetail']) {
  type Body = ReturnType<typeof visualSaveBody>
  const recovery = useTypedRequestRecovery<Body>(scope, (body): body is Body => {
    try {
      if (!body || typeof body !== 'object' || version.spec?.schema_version !== 'visual.answer.v1') return false
      const value = body as Body
      return value.action === 'save' && value.document_id === documentId
        && Number.isSafeInteger(value.expected_revision) && value.expected_revision > 0
        && JSON.stringify(value.spec) === JSON.stringify(applyVisualEdits(version.spec, editableFields(value.spec)))
    } catch { return false }
  }, true, true)
  return { ...recovery, error: recovery.error.replaceAll('model call', 'version save') }
}

export function useLessonPromotionRecovery(scope: string, answerId: string) {
  const recovery = useTypedRequestRecovery<LessonBody>(scope, (body): body is LessonBody => validLessonBody(body, answerId), true, true)
  return { ...recovery, error: recovery.error.replaceAll('model call', 'draft save') }
}
