import { apiFetch, type Schemas } from '../lib/api'
import { ReviewRecovery } from '../features/review/ReviewRecovery'
import { QuestionHelp } from '../features/assess/QuestionHelp'
import { ReadAloud } from '../features/voice/ReadAloud'
import { readDraft, writeDraft, clearDraft } from '../features/assess/draft'
import { useSkills } from '../features/skills/api'
import { OptionalConfidence } from '../components/OptionalConfidence'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { SessionControls } from '../features/session/SessionControls'
import { useDue, useRate, useRatingPending } from '../features/review/api'
import { REVIEW_BLOCK_TYPES, routeForPhase, useBlockTransition, useSession } from '../features/session/api'
import { nowMs } from '../lib/time'
import { useMode } from '../stores/mode'

const RATINGS = [
  { value: 1, label: 'Again', hint: 'Could not recall' },
  { value: 2, label: 'Hard', hint: 'Recalled with effort' },
  { value: 3, label: 'Good', hint: 'Recalled' },
  { value: 4, label: 'Easy', hint: 'Instant' },
]

type ReviewCheckpoint = {
  version: 1
  admitted: string[] | null
  reviewed: string[]
  current: string | null
  revealedVersion?: string | null
  revealed: string | null
  all: boolean
}
function restoreQueue(key: string): ReviewCheckpoint {
  try {
    const v = JSON.parse(sessionStorage.getItem(key) ?? 'null')
    if (
      v?.version === 1 &&
      (v.admitted === null ||
        (Array.isArray(v.admitted) && v.admitted.every((id: unknown) => typeof id === 'string'))) &&
      Array.isArray(v.reviewed) &&
      v.reviewed.every((id: unknown) => typeof id === 'string') &&
      (v.current === null || typeof v.current === 'string') &&
      (v.revealed === null || typeof v.revealed === 'string') &&
      typeof v.all === 'boolean'
    )
      return v
  } catch {
    /* unavailable storage: keep this visit usable */
  }
  return { version: 1, admitted: null, reviewed: [], current: null, revealed: null, all: false }
}

export function Review() {
  const { sessionId } = useMode()
  return <ReviewSession key={sessionId ?? 'none'} sessionId={sessionId} />
}

function ReviewSession({ sessionId }: { sessionId: string | null }) {
  const queueKey = `audhs-review-queue:v1:${sessionId}`
  const [queue, setQueue] = useState(() => restoreQueue(queueKey))
  const saving = useRef(false)
  useEffect(() => {
    if (!sessionId) return
    try {
      sessionStorage.setItem(queueKey, JSON.stringify(queue))
    } catch {
      /* no progress writes depend on browser storage */
    }
  }, [queue, queueKey, sessionId])
  const skills = useSkills()
  const [, refreshHelp] = useState(0)
  const showAll = queue.all
  const setShowAll = (all: boolean) => setQueue((q) => ({ ...q, all }))
  // confidence is per card: it is sent with the rating and cleared for the next card
  const [confidence, setConfidence] = useState<number | null>(null)
  const due = useDue(sessionId, showAll)
  const rate = useRate(sessionId ?? '', true)
  const ratingPending = useRatingPending()
  const session = useSession(sessionId)
  const transition = useBlockTransition(sessionId)
  const nav = useNavigate()

  const [shownAt, setShownAt] = useState(nowMs)
  const [frozen, setFrozen] = useState<Schemas['ReviewItemOut'] | null>(null)
  const candidates = (due.data?.items ?? []).filter(
    (i) =>
      !queue.reviewed.includes(i.item_id) &&
      (showAll || queue.admitted === null || queue.admitted.includes(i.item_id)),
  )
  const candidate = candidates.find((i) => i.item_id === queue.current) ?? candidates[0]
  const item = frozen && !queue.reviewed.includes(frozen.item_id) ? frozen : candidate
  if (item && item !== frozen) setFrozen(item)

  function markReviewed(itemId: string) {
    const saved = restoreQueue(queueKey)
    const next: ReviewCheckpoint = {
      ...queue,
      ...saved,
      admitted: saved.admitted ?? queue.admitted,
      reviewed: [...new Set([...queue.reviewed, ...saved.reviewed, itemId])],
      current: null,
      revealed: null,
    }
    try {
      sessionStorage.setItem(queueKey, JSON.stringify(next))
    } catch {
      if (!rate.recovery.memoryOnly) {
        const message =
          'Rating saved, but the review queue could not be stored. Restore storage or explicitly continue in page memory.'
        rate.recovery.reportStorageError(message)
        throw new Error(message)
      }
    }
    setQueue(next)
    clearDraft(`audhs-review:${sessionId}:${itemId}`)
    setConfidence(null)
    setShownAt(nowMs())
  }
  const recoveryPanel = (
    <ReviewRecovery
      recovery={rate.recovery}
      onRefresh={async (signal) => {
        const pending = rate.recovery.pending
        if (!pending || pending.itemId !== item?.item_id)
          throw new Error('Reopen the original review card to refresh it.')
        const fresh = await apiFetch<Schemas['ReviewItemOut']>(
          `/api/review/items/${encodeURIComponent(pending.itemId)}?session_id=${encodeURIComponent(sessionId!)}`,
          { signal },
        )
        if (signal.aborted) return
        if (fresh.item_id !== pending.itemId)
          throw new Error('The returned card does not match the original rating.')
        setFrozen(fresh)
        setQueue((q) => ({ ...q, current: fresh.item_id, revealed: null, revealedVersion: null }))
        setConfidence(null)
        setShownAt(nowMs())
      }}
      onConfirmed={async (itemId) => {
        const fresh = await due.refetch()
        if (fresh.error)
          throw new Error('Rating is saved, but the current queue could not load. Retry updating it.')
        markReviewed(itemId)
      }}
    />
  )

  if (!sessionId)
    return (
      <Card>
        <p>No session running.</p>
        <Button variant="primary" onClick={() => nav('/')}>
          Go to Home
        </Button>
      </Card>
    )
  if (due.isError && !due.data)
    return (
      <Card>
        {recoveryPanel}
        <p role="alert">Could not load review cards. Your saved ratings are retained.</p>
        <Button disabled={due.isFetching} onClick={() => void due.refetch()}>
          Retry
        </Button>
        <Button onClick={() => nav('/')}>Go to Home</Button>
        <SessionControls sessionId={sessionId} />
      </Card>
    )
  if (due.isLoading || !due.data)
    return (
      <>
        {recoveryPanel}
        <Card>
          <p role="status">Loading review…</p>
          <Button onClick={() => nav('/')}>Go to Home</Button>
        </Card>
      </>
    )
  const refreshWarning = due.isError ? (
    <Card>
      <p role="status">Could not refresh review cards. The displayed card and your progress are kept.</p>
      <Button disabled={due.isFetching} onClick={() => void due.refetch()}>
        {due.isFetching ? 'Retrying…' : 'Retry review cards'}
      </Button>
    </Card>
  ) : null
  const items = due.data.items
  const admitted = queue.admitted ?? items.map((i) => i.item_id)
  if (queue.admitted === null) setQueue((q) => ({ ...q, admitted }))
  const remaining = items.filter(
    (i) => !queue.reviewed.includes(i.item_id) && (showAll || admitted.includes(i.item_id)),
  )
  const currentId = item?.item_id ?? null
  if (currentId !== queue.current) {
    setQueue((q) => ({ ...q, current: currentId, revealed: null }))
    setConfidence(null)
    setShownAt(nowMs())
  }
  const revealed =
    currentId !== null && queue.revealed === currentId && queue.revealedVersion === item?.content_version
  const setRevealed = (value: boolean) =>
    setQueue((q) => ({
      ...q,
      revealed: value ? currentId : null,
      revealedVersion: value ? item?.content_version : null,
    }))
  const idx = queue.reviewed.length
  const helpKey = `audhs-review:${sessionId}:${item?.item_id ?? ''}`
  const hintCount = readDraft(helpKey).hints
  const state = session.data?.state
  const inReviewBlock =
    !!state && state.block_status === 'running' && REVIEW_BLOCK_TYPES.includes(state.block?.type ?? '')

  async function continuePlan() {
    if (!state || transition.pending) return
    try {
      const next = await transition.next({ from_index: state.block_index ?? null, reason: 'finished' })
      nav(next.plan_complete ? '/recap' : routeForPhase(next))
    } catch {
      /* transition.error is rendered; the plan did not move */
    }
  }

  async function stopHere() {
    if (transition.pending) return
    try {
      if (inReviewBlock && state && state.block_index != null) {
        await transition.end({ index: state.block_index, reason: 'save_and_stop', switched_early: true })
      }
      nav('/recap')
    } catch {
      /* transition.error is rendered; stay here */
    }
  }

  if (!item)
    return (
      <Card>
        <SessionControls sessionId={sessionId} />
        {recoveryPanel}
        {refreshWarning}
        <CardTitle>Review done</CardTitle>
        <p>
          {due.data.total_due === 0
            ? 'Nothing is due right now.'
            : `${queue.reviewed.length} cards reviewed in this session. This selected review set is complete.`}
        </p>
        {!showAll && due.data.total_due > remaining.length && (
          <Button onClick={() => setShowAll(true)}>Show all due cards</Button>
        )}
        <div className="flex gap-2 mt-3 flex-wrap">
          {inReviewBlock ? (
            <Button variant="primary" onClick={() => void continuePlan()} disabled={transition.pending}>
              Continue the plan
            </Button>
          ) : (
            <Button variant="primary" onClick={() => nav('/session')}>
              Back to the session
            </Button>
          )}
          <Button onClick={() => void stopHere()} disabled={transition.pending}>
            Finish session
          </Button>
        </div>
        {transition.error && (
          <p role="alert" className="text-warn mt-2">
            {transition.error.message}
          </p>
        )}
      </Card>
    )

  async function rateIt(rating: number) {
    if (saving.current || ratingPending) return
    saving.current = true
    try {
      const completed = await rate.mutateAsync({
        itemId: item.item_id,
        questionLabel: item.question,
        revealLabel: item.reveal,
        optionsLabels: item.options,
        body: {
          session_id: sessionId!,
          rating,
          content_version: item.content_version,
          latency_ms: nowMs() - shownAt,
          confidence_pre: confidence ?? undefined,
          hint_count: hintCount,
        },
      })
      markReviewed(item.item_id)
      rate.recovery.clear(completed.requestId)
    } catch {
      /* mutation error is displayed; retain the card for retry */
    } finally {
      saving.current = false
    }
  }

  return (
    <div className="grid gap-4">
      {refreshWarning}
      {recoveryPanel}
      <SessionControls sessionId={sessionId} skillId={item.skill_id} />
      {state && !inReviewBlock && (
        <p className="text-sm text-muted" role="status">
          Off-plan review: rating cards here is always useful, but it does not advance the session plan
          {state.block
            ? ` (${state.block_status === 'running' ? 'current' : 'last'} block: ${state.block.type.replace('_', ' ')})`
            : ''}
          .
        </p>
      )}
      <Card>
        <CardTitle>Recall what you learned</CardTitle>
        <p className="text-sm text-muted mb-3">
          {revealed
            ? 'Compare with your answer, then choose how easily you recalled it. Your rating opens the next card.'
            : 'Answer in your head or aloud. Then reveal the answer when ready.'}
        </p>
        <p className="text-xs text-muted">
          Review {idx + 1} of {idx + remaining.length}
          {due.data.total_due > items.length
            ? ` (capped at ${due.data.cap}; ${due.data.total_due} due in total)`
            : ''}{' '}
          · {item.skill_title}
        </p>
        <p className="text-sm mt-2">{skills.data?.skills.find((s) => s.id === item.skill_id)?.description}</p>
        <p className="text-base mt-2">{item.question}</p>
        {!revealed && (
          <QuestionHelp
            key={item.item_id}
            sessionId={sessionId}
            skillId={item.skill_id}
            question={item.question}
            onHint={() => {
              writeDraft(helpKey, { hints: readDraft(helpKey).hints + 1 })
              refreshHelp((n) => n + 1)
            }}
          />
        )}
        {item.options && (
          <ol className="list-decimal ml-5 mt-2 text-sm">
            {item.options.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ol>
        )}
        {!revealed ? (
          <div className="mt-3">
            <OptionalConfidence value={confidence} onChange={setConfidence} />
            <Button variant="primary" className="mt-3" onClick={() => setRevealed(true)}>
              Show answer
            </Button>
          </div>
        ) : (
          <div className="mt-3">
            <p className="font-medium">Answer</p>
            <p>{item.reveal}</p>
            <ReadAloud key={item.item_id} text={item.reveal} />
            {hintCount > 0 && (
              <p className="text-sm">Help was used. Choose Again or Hard so this question returns sooner.</p>
            )}
            <p className="text-sm font-medium mt-3 mb-2">How did recall go?</p>
            <div className="grid grid-cols-4 gap-2">
              {RATINGS.filter((r) => !hintCount || r.value <= 2).map((r) => (
                <Button
                  key={r.value}
                  onClick={() => void rateIt(r.value)}
                  disabled={ratingPending || !!rate.recovery.pending || !!rate.recovery.error}
                  className="flex-col h-auto py-2"
                >
                  <span>{r.label}</span>
                  <span className="text-xs opacity-80">{r.hint}</span>
                </Button>
              ))}
            </div>
            {rate.isError && (
              <p role="alert" className="text-warn mt-2">
                {(rate.error as Error).message} — check the earlier submission before trying again.
              </p>
            )}
          </div>
        )}
      </Card>
      <div className="flex gap-2 flex-wrap">
        <Button variant="ghost" onClick={() => void stopHere()} disabled={transition.pending}>
          Stop here (save progress)
        </Button>
        {due.data.total_due > items.length && !showAll && (
          <Button variant="ghost" onClick={() => setShowAll(true)}>
            Show all {due.data.total_due} due (undo the cap)
          </Button>
        )}
      </div>
    </div>
  )
}
