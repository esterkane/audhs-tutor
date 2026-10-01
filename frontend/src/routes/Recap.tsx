import { SessionControls } from '../features/session/SessionControls'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Choice } from '../components/ui/choice'
import { Textarea } from '../components/ui/textarea'
import { useEndSession } from '../features/session/api'
import type { SessionOut } from '../lib/api'
import { useMode } from '../stores/mode'

export function Recap() {
  const { sessionId, reset } = useMode()
  const end = useEndSession()
  const nav = useNavigate()
  const [energyAfter, setEnergyAfter] = useState<number | null>(null)
  const [recall, setRecall] = useState<number | null>(null)
  const [notes, setNotes] = useState('')
  const [summary, setSummary] = useState<SessionOut | null>(null)

  if (!sessionId && !summary)
    return (
      <Card>
        <p>No session to recap.</p>
        <Button variant="primary" onClick={() => nav('/')}>
          Go to Home
        </Button>
      </Card>
    )

  async function finish() {
    if (!sessionId) return
    const s = await end.mutateAsync({
      id: sessionId,
      body: {
        energy_after: energyAfter ?? undefined,
        self_report: recall ?? undefined,
        notes: notes || undefined,
      },
    })
    setSummary(s)
    reset()
  }

  if (summary)
    return (
      <Card>
        <CardTitle>Session saved</CardTitle>
        <p>
          Next skill on the map: {summary.next_skill?.title ?? '—'} (
          {((summary.next_skill?.mastery ?? 0) * 100).toFixed(0)}% mastery). {summary.due_reviews} items due
          for review.
        </p>
        <Button variant="primary" className="mt-3" onClick={() => nav('/')}>
          Back to Home
        </Button>
      </Card>
    )

  return (
    <Card>
      {sessionId && <SessionControls sessionId={sessionId} />}
      <CardTitle>Finish your session</CardTitle>
      <p className="text-sm text-muted mb-3">
        Ratings and notes are optional. You can save immediately. These ratings describe this session; they
        are not a test score.
      </p>
      <Choice<number>
        label="Energy now (1–5)"
        options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
        value={energyAfter}
        onChange={setEnergyAfter}
        columns={5}
      />
      <div className="mt-4">
        <Choice<number>
          label="How much of today's material can you still recall without looking? (1 = almost none, 5 = all of it)"
          options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
          value={recall}
          onChange={setRecall}
          columns={5}
        />
      </div>
      <label htmlFor="notes" className="block text-sm font-medium mt-4">
        One line for next time (optional)
      </label>
      <Textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} className="min-h-16" />
      <Button variant="primary" className="mt-3" onClick={() => void finish()} disabled={end.isPending}>
        {end.isPending ? 'Saving…' : 'Save and finish session'}
      </Button>
      {end.isError && (
        <p role="alert" className="text-warn mt-2">
          {(end.error as Error).message}
        </p>
      )}
    </Card>
  )
}
