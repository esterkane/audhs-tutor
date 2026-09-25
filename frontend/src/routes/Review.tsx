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
  const rate = useRate(true)
  const ratingPending = useRatingPending()
  const session = useSession(sessionId)
  const transition = useBlockTransition(sessionId)
  const nav = useNavigate()

  const [shownAt, setShownAt] = useState(nowMs)

  if (!sessionId)
    return (
      <Card>
        <p>No session running.</p>
        <Button variant="primary" onClick={() => nav('/')}>
          Go to Home
        </Button>
      </Card>
    )
  if (due.isError)
    return (
      <Card>
        <p role="alert">Could not load review cards. Your saved ratings are retained.</p>
        <Button onClick={() => void due.refetch()}>Retry</Button>
        <SessionControls sessionId={sessionId} />
      </Card>
    )
  if (due.isLoading || !due.data) return <Card>Loading review…</Card>
  const items = due.data.items
  const admitted = queue.admitted ?? items.map((i) => i.item_id)
  if (queue.admitted === null) setQueue((q) => ({ ...q, admitted }))
  const remaining = items.filter(
    (i) => !queue.reviewed.includes(i.item_id) && (showAll || admitted.includes(i.item_id)),
  )
  const item = remaining.find((i) => i.item_id === queue.current) ?? remaining[0]
  const currentId = item?.item_id ?? null
  if (currentId !== queue.current) {
    setQueue((q) => ({ ...q, current: currentId, revealed: null }))
    setConfidence(null)
    setShownAt(nowMs())
  }
  const revealed = currentId !== null && queue.revealed === currentId
  const setRevealed = (value: boolean) => setQueue((q) => ({ ...q, revealed: value ? currentId : null }))
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
      await rate.mutateAsync({
        itemId: item.item_id,
        body: {
          session_id: sessionId!,
          rating,
          latency_ms: nowMs() - shownAt,
          confidence_pre: confidence ?? undefined,
          hint_count: hintCount,
        },
      })
      setRevealed(false)
      clearDraft(helpKey)
      setConfidence(null)
      setShownAt(nowMs())
      // Persist in the successful request continuation even if this view has unmounted.
      const saved = restoreQueue(queueKey)
      const next: ReviewCheckpoint = {
        ...queue,
        ...saved,
        admitted: saved.admitted ?? queue.admitted,
        reviewed: [...new Set([...queue.reviewed, ...saved.reviewed, item.item_id])],
        current: null,
        revealed: null,
      }
      try {
        sessionStorage.setItem(queueKey, JSON.stringify(next))
      } catch {
        /* server rating remains saved */
      }
      setQueue(next)
    } catch {
      /* mutation error is displayed; retain the card for retry */
    } finally {
      saving.current = false
    }
  }

  return (
    <div className="grid gap-4">
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
                  disabled={ratingPending}
                  className="flex-col h-auto py-2"
                >
                  <span>{r.label}</span>
                  <span className="text-xs opacity-80">{r.hint}</span>
                </Button>
              ))}
            </div>
            {rate.isError && (
              <p role="alert" className="text-warn mt-2">
                {(rate.error as Error).message} — the rating was not saved; try again.
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
