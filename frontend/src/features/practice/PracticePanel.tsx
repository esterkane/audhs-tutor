import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { Choice } from '../../components/ui/choice'
import { Textarea } from '../../components/ui/textarea'
import { useActivities, useLogPractice } from './api'

const TITLES: Record<string, string> = { movement: 'Move first', guitar: 'Guitar practice' }

/** A whole-domain block (ADR-0006): pick one concrete activity, do it, rate it, continue — or skip. */
export function PracticePanel({
  sessionId,
  domain,
  plannedMin,
  onDone,
  onSkip,
}: {
  sessionId: string
  domain: 'movement' | 'guitar'
  plannedMin: number
  onDone: () => void
  onSkip: () => void
}) {
  const activities = useActivities()
  const log = useLogPractice()
  const options = activities.data?.activities[domain] ?? []
  const [activity, setActivity] = useState<string | null>(null)
  const [rating, setRating] = useState<number | null>(null)
  const [notes, setNotes] = useState('')
  const [startedAt] = useState(() => Date.now())

  async function finish() {
    if (!activity || !rating) return
    await log.mutateAsync({
      session_id: sessionId,
      domain,
      activity,
      duration_min: Math.max(0, Math.round(((Date.now() - startedAt) / 60_000) * 10) / 10),
      self_rating: rating,
      notes: notes.trim() || null,
    })
    onDone()
  }

  return (
    <Card>
      <CardTitle>{TITLES[domain]}</CardTitle>
      <p className="text-sm text-muted mb-3">
        About {plannedMin} min. Pick one, do it, then rate how it went. Skipping is fine and is remembered as
        a pattern, never as a fault.
      </p>
      <Choice<string>
        label="Which one?"
        options={options.map((o) => ({ value: o, label: o }))}
        value={activity ?? ''}
        onChange={setActivity}
        columns={Math.max(1, Math.min(3, options.length))}
      />
      {activity && (
        <div className="mt-4">
          <Choice<number>
            label="Rate this block (1 = could not do it, 5 = did all of it)"
            options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
            value={rating ?? 0}
            onChange={setRating}
            columns={5}
          />
          <Textarea
            aria-label="Notes (optional)"
            placeholder="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="mt-3 min-h-14"
          />
        </div>
      )}
      <div className="flex flex-wrap gap-2 mt-4">
        <Button
          variant="primary"
          disabled={!activity || !rating || log.isPending}
          onClick={() => void finish()}
        >
          Log and continue
        </Button>
        <Button variant="ghost" onClick={onSkip}>
          Skip this block
        </Button>
      </div>
      {log.isError && (
        <p role="alert" className="text-warn mt-2">
          {(log.error as Error).message}
        </p>
      )}
    </Card>
  )
}
