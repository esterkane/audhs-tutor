import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Choice } from '../components/ui/choice'
import { useDue, useRate } from '../features/review/api'
import { nowMs } from '../lib/time'
import { useMode } from '../stores/mode'

const RATINGS = [
  { value: 1, label: 'Again', hint: 'Could not recall' },
  { value: 2, label: 'Hard', hint: 'Recalled with effort' },
  { value: 3, label: 'Good', hint: 'Recalled' },
  { value: 4, label: 'Easy', hint: 'Instant' },
]

export function Review() {
  const { sessionId } = useMode()
  const [showAll, setShowAll] = useState(false)
  const [confidence, setConfidence] = useState<number | null>(null)
  const due = useDue(sessionId, showAll)
  const rate = useRate()
  const nav = useNavigate()
  const [idx, setIdx] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const shownAt = useRef(nowMs())

  if (!sessionId)
    return (
      <Card>
        <p>No session running.</p>
        <Button variant="primary" onClick={() => nav('/')}>
          Go to Home
        </Button>
      </Card>
    )
  if (due.isLoading || !due.data) return <Card>Loading review…</Card>
  const items = due.data.items
  const item = items[idx]

  if (!item)
    return (
      <Card>
        <CardTitle>Review done</CardTitle>
        <p>
          {items.length === 0
            ? 'Nothing is due right now.'
            : `${items.length} of ${due.data.total_due} due items reviewed (capped at ${due.data.cap} for this session).`}
        </p>
        <div className="flex gap-2 mt-3">
          <Button variant="primary" onClick={() => nav('/session')}>
            Learn something
          </Button>
          <Button onClick={() => nav('/recap')}>Finish session</Button>
        </div>
      </Card>
    )

  async function rateIt(rating: number) {
    await rate.mutateAsync({
      itemId: item.item_id,
      body: {
        session_id: sessionId!,
        rating,
        latency_ms: nowMs() - shownAt.current,
      },
    })
    setRevealed(false)
    shownAt.current = nowMs()
    setIdx((i) => i + 1)
  }

  return (
    <div className="grid gap-4">
      <Card>
        <p className="text-xs text-muted">
          Review {idx + 1} of {items.length}
          {due.data.total_due > items.length
            ? ` (capped at ${due.data.cap}; ${due.data.total_due} due in total)`
            : ''}{' '}
          · {item.skill_title}
        </p>
        <p className="text-base mt-2">{item.question}</p>
        {item.options && (
          <ol className="list-decimal ml-5 mt-2 text-sm">
            {item.options.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ol>
        )}
        {!revealed ? (
          <div className="mt-3">
            <Choice<number>
              label="Before revealing: how sure are you of your recall? (1 = no idea, 5 = certain)"
              options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
              value={confidence}
              onChange={setConfidence}
              columns={5}
            />
            <Button
              variant="primary"
              className="mt-3"
              onClick={() => setRevealed(true)}
              disabled={confidence == null}
            >
              Show answer
            </Button>
          </div>
        ) : (
          <div className="mt-3">
            <p className="font-medium">Answer</p>
            <p>{item.reveal}</p>
            <p className="text-sm font-medium mt-3 mb-2">How did recall go?</p>
            <div className="grid grid-cols-4 gap-2">
              {RATINGS.map((r) => (
                <Button
                  key={r.value}
                  onClick={() => void rateIt(r.value)}
                  disabled={rate.isPending}
                  className="flex-col h-auto py-2"
                >
                  <span>{r.label}</span>
                  <span className="text-xs opacity-80">{r.hint}</span>
                </Button>
              ))}
            </div>
          </div>
        )}
      </Card>
      <div className="flex gap-2 flex-wrap">
        <Button variant="ghost" onClick={() => nav('/recap')}>
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
