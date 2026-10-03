import { useLayoutEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ApiError, api, apiFetch, type Schemas } from '../../lib/api'
type ReviewRating = Schemas['ReviewRating']
type ReviewOut = Schemas['ReviewOut']

export const reviewRecoveryKey = (session: string) => `review-request:v1:${session}`
type Submission = {
  itemId: string
  body: ReviewRating
  questionLabel?: string
  revealLabel?: string
  optionsLabels?: string[] | null
}
export type PendingReview = {
  version: 1
  id: string
  itemId: string
  body: ReviewRating
  question: string
  reveal?: string
  options?: string[] | null
  rejectedContent?: boolean
}
const previousKey = (session: string) => `review-previous-rating:v1:${session}`
const previousMemory = new Map<string, PendingReview[]>()
function loadPrevious(session: string, strict = false): PendingReview[] {
  if (previousMemory.has(session)) return previousMemory.get(session)!
  try {
    const value = JSON.parse(sessionStorage.getItem(previousKey(session)) ?? 'null')
    const entries = Array.isArray(value) ? value : value ? [value] : []
    const valid = entries.filter(
      (value) =>
        value?.version === 1 &&
        value.body?.session_id === session &&
        typeof value.question === 'string' &&
        [1, 2, 3, 4].includes(value.body.rating),
    )
    if (strict && valid.length !== entries.length) throw new Error('Archive is damaged')
    return valid
  } catch (cause) {
    if (strict) throw cause
    return []
  }
}
const pageMemory = new Map<string, PendingReview | null>()
function write(session: string, value: PendingReview) {
  if (pageMemory.has(session)) pageMemory.set(session, value)
  else sessionStorage.setItem(reviewRecoveryKey(session), JSON.stringify(value))
}
function remove(session: string) {
  if (pageMemory.has(session)) pageMemory.set(session, null)
  else sessionStorage.removeItem(reviewRecoveryKey(session))
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
function read(session: string): PendingReview | null {
  if (pageMemory.has(session)) return pageMemory.get(session) ?? null
  const raw = sessionStorage.getItem(reviewRecoveryKey(session))
  if (!raw) return null
  const value = JSON.parse(raw) as PendingReview
  if (
    value.version !== 1 ||
    !uuid.test(value.id) ||
    value.body?.session_id !== session ||
    typeof value.itemId !== 'string' ||
    !value.itemId ||
    ![1, 2, 3, 4].includes(value.body.rating) ||
    typeof value.question !== 'string'
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

/** One unresolved rating intent per session/tab. Never rate again from a lookup or timeout. */
export function useReviewSubmission(sessionId: string, reconcileQueue = false) {
  const qc = useQueryClient()
  const key = reviewRecoveryKey(sessionId)
  const [archivedRatings, setArchivedRatings] = useState(() => loadPrevious(sessionId))
  const [scope, setScope] = useState(key)
  const [stored, setStored] = useState(() => load(sessionId))
  const [lookup, setLookup] = useState<Schemas['ReviewRequestState'] | null>(null)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')
  const activeKey = useRef(key)
  const operation = useRef<AbortController | null>(null)
  if (scope !== key) {
    setScope(key)
    setArchivedRatings(loadPrevious(sessionId))
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

  function recordContentRejection(cause: unknown, pending: PendingReview) {
    if (
      activeKey.current !== key ||
      !(cause instanceof ApiError) ||
      cause.status !== 409 ||
      !['review_content_changed', 'review_content_required'].includes(cause.code)
    )
      return
    try {
      if (read(sessionId)?.id !== pending.id) return
      const rejected = { ...pending, rejectedContent: true }
      write(sessionId, rejected)
      setStored({ pending: rejected, error: '' })
      setLookup(null)
    } catch {
      setError(
        'The card changed, but recovery could not be updated. Keep your rating and check its saved result.',
      )
    }
  }

  function clear(expectedId?: string) {
    if (operation.current) return
    try {
      const current = read(sessionId)
      if (current?.id !== (expectedId ?? stored.pending?.id)) {
        setStored({ pending: current, error: '' })
        setLookup(null)
        setError('Recovery information changed in this session. Check the currently saved submission.')
        return
      }
      if (current?.rejectedContent) {
        const archive = [...loadPrevious(sessionId, true).filter((entry) => entry.id !== current.id), current]
        if (pageMemory.has(sessionId)) previousMemory.set(sessionId, archive)
        else sessionStorage.setItem(previousKey(sessionId), JSON.stringify(archive))
        setArchivedRatings(archive)
      }
      remove(sessionId)
      setStored({ pending: null, error: '' })
      setLookup(null)
      setError('')
    } catch {
      setStored((previous) => ({
        ...previous,
        error: 'Recovery information could not be cleared. Keep your rating and try again.',
      }))
    }
  }

  const mutation = useMutation({
    mutationKey: ['review-rating'],
    mutationFn: async (submission: Submission) => {
      if (activeKey.current !== key) throw new Error('The session changed; your rating was not sent.')
      const previous = load(sessionId)
      setStored(previous)
      if (previous.error) throw new Error(previous.error)
      if (previous.pending)
        throw new Error('An earlier submission needs checking. Your current rating has not been sent.')
      const { questionLabel, revealLabel, optionsLabels, itemId, body } = submission
      if (body.session_id !== sessionId) throw new Error('This rating belongs to another session.')
      const pending: PendingReview = {
        version: 1,
        id: crypto.randomUUID(),
        itemId,
        body: { ...body },
        question: questionLabel ?? 'Review card',
        reveal: revealLabel,
        options: optionsLabels,
      }
      try {
        write(sessionId, pending)
      } catch {
        setStored({ pending: null, error: 'Recovery storage could not save this submission.' })
        throw new Error(
          'The recovery identity could not be saved. No rating was sent; keep your rating and retry.',
        )
      }
      setStored({ pending, error: '' })
      setLookup(null)
      setError('')
      const result = await bounded((signal) =>
        apiFetch<ReviewOut>(`/api/review/${encodeURIComponent(pending.itemId)}`, {
          method: 'POST',
          body: JSON.stringify(pending.body),
          headers: { 'Idempotency-Key': pending.id },
          signal,
        }),
      ).catch((cause) => {
        recordContentRejection(cause, pending)
        throw cause
      })
      if (result.item_id !== pending.itemId)
        throw new Error('The returned feedback belongs to another review card.')
      // Keep the identity until the caller durably checkpoints the advanced queue.
      setLookup({ status: 'completed', result })
      return { result, requestId: pending.id }
    },
    retry: false,
    onSuccess: (_result, { itemId, body }) => {
      if (!reconcileQueue) return
      qc.setQueriesData<Awaited<ReturnType<typeof api.due>>>({ queryKey: ['due', body.session_id] }, (old) =>
        old
          ? {
              ...old,
              items: old.items.filter((item) => item.item_id !== itemId),
              total_due: Math.max(
                0,
                old.total_due - (old.items.some((item) => item.item_id === itemId) ? 1 : 0),
              ),
            }
          : old,
      )
    },
  })

  async function check() {
    const pending = stored.pending
    if (!pending || operation.current) return
    setChecking(true)
    setError('')
    try {
      const result = await bounded((signal) =>
        apiFetch<Schemas['ReviewRequestState']>(
          `/api/review/requests/${pending.id}?session_id=${encodeURIComponent(sessionId)}`,
          { signal },
        ),
      )
      if (result.result && result.result.item_id !== pending.itemId)
        throw new Error('The saved result belongs to another review card.')
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
        apiFetch<ReviewOut>(`/api/review/${encodeURIComponent(pending.itemId)}`, {
          method: 'POST',
          headers: { 'Idempotency-Key': pending.id },
          body: JSON.stringify(pending.body),
          signal,
        }),
      )
      if (result.item_id !== pending.itemId) throw new Error('Mismatched review result.')
      setLookup({ status: 'completed', result })
    } catch (cause) {
      recordContentRejection(cause, pending)
      if (activeKey.current === key) setError((cause as Error).message)
    } finally {
      if (activeKey.current === key) setChecking(false)
    }
  }

  return {
    ...mutation,
    recovery: {
      archivedRatings,
      previousRating: archivedRatings.at(-1) ?? null,
      dismissPrevious: (id?: string) => {
        try {
          const remaining = loadPrevious(sessionId, true).filter(
            (entry) => entry.id !== (id ?? archivedRatings.at(-1)?.id),
          )
          if (pageMemory.has(sessionId)) previousMemory.set(sessionId, remaining)
          else sessionStorage.setItem(previousKey(sessionId), JSON.stringify(remaining))
          setArchivedRatings(remaining)
        } catch {
          setError('The previous rating could not be dismissed. It is still kept.')
        }
      },
      stale: !!stored.pending?.rejectedContent,
      pending: stored.pending,
      error: error || stored.error,
      storageError: stored.error,
      reportStorageError: (message: string) => setStored((previous) => ({ ...previous, error: message })),
      lookup,
      checking: checking || mutation.isPending,
      check,
      resend,
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
        previousMemory.set(sessionId, archivedRatings)
        pageMemory.set(sessionId, pending)
        setStored({ pending, error: '' })
        setError('')
      },
    },
  }
}
