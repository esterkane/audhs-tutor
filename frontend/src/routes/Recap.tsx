import { SessionControls } from '../features/session/SessionControls'
import { useRef, useState } from 'react'
import { useRecapDraft } from '../features/session/useRecapDraft'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Choice } from '../components/ui/choice'
import { Textarea } from '../components/ui/textarea'
import { useStopSession } from '../features/session/useStopSession'
import type { SessionOut } from '../lib/api'
import { useMode } from '../stores/mode'

export function Recap() {
  const { sessionId } = useMode()
  const nav = useNavigate()
  const saving = useRef(false)
  const draft = useRecapDraft(sessionId)
  const { energyAfter, recall, notes } = draft
  const [summary, setSummary] = useState<SessionOut | null>(null)
  const end = useStopSession(sessionId ?? '', (saved) => { draft.clear(); setSummary(saved) })

  if (!sessionId && !summary)
    return (
      <Card>
        <CardTitle as="h1">Session recap</CardTitle>
        <p>No session to recap.</p>
        <Button variant="primary" onClick={() => nav('/')}>
          Go to Home
        </Button>
      </Card>
    )

  async function finish(withRecap = true) {
    if (!sessionId || saving.current) return
    saving.current = true
    try {
      await end.mutateAsync(withRecap ? {
        energy_after: energyAfter ?? undefined,
        self_report: recall ?? undefined,
        notes: notes || undefined,
      } : undefined)
    } finally { saving.current = false }
  }

  if (summary)
    return (
      <Card>
        <CardTitle as="h1">Session saved</CardTitle>
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
      {sessionId && <SessionControls sessionId={sessionId} endAction={{
        run: () => { void finish(false).catch(() => { /* The shared error remains visible. */ }) },
        isPending: end.isPending, error: null,
      }} />}
      <CardTitle as="h1">Finish your session</CardTitle>
      <p className="text-sm text-muted mb-3">
        Ratings and notes are optional. You can save immediately. These ratings describe this session; they
        are not a test score.
      </p>
      <fieldset disabled={end.isPending} className="border-0 p-0 m-0 min-w-0">
      <Choice<number>
        label="Energy now (1–5)"
        options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
        value={energyAfter}
        onChange={(energyAfter) => draft.edit({ energyAfter })}
        columns={5}
      />
      <div className="mt-4">
        <Choice<number>
          label="How much of today's material can you still recall without looking? (1 = almost none, 5 = all of it)"
          options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
          value={recall}
          onChange={(recall) => draft.edit({ recall })}
          columns={5}
        />
      </div>
      <label htmlFor="notes" className="block text-sm font-medium mt-4">
        One line for next time (optional)
      </label>
      <Textarea id="notes" value={notes} onChange={(e) => draft.edit({ notes: e.target.value })} className="min-h-16" />
      {draft.error && <p role="alert">{draft.error}</p>}
      <Button variant="primary" className="mt-3" onClick={() => void finish().catch(() => { /* Error is displayed below; keep the draft. */ })} disabled={end.isPending}>
        {end.isPending ? (end.variables === undefined ? 'Ending session…' : 'Saving…') : 'Save and finish session'}
      </Button>
      </fieldset>
      {end.isError && (
        <p role="alert" className="text-warn mt-2">
          {(end.error as Error).message}
        </p>
      )}
    </Card>
  )
}
