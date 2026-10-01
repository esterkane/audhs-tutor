import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { useMode } from '../../stores/mode'
import { useAdaptationLog, usePendingAdaptations, type Decision } from './api'

const CHOICES: Array<{ decision: Decision; label: string; hint: string }> = [
  {
    decision: 'try',
    label: 'Try it this session',
    hint: 'Reverts when the next session starts; you may be asked again.',
  },
  { decision: 'default', label: 'Make it the default', hint: 'Stays until you undo it in Preferences.' },
  { decision: 'no', label: 'No', hint: 'May be suggested again in 14 days.' },
  { decision: 'never', label: "Don't suggest this again", hint: 'Never for this pattern.' },
]

/** Proposal cards. The system never applies these on its own: one of four explicit choices. */
export function AdaptationCards({ origin }: { origin?: 'planner' | 'observed_pattern' } = {}) {
  const pending = usePendingAdaptations()
  const { decide } = useAdaptationLog()
  const { sessionId } = useMode()
  const cards = (pending.data?.proposals ?? []).filter((c) => !origin || c.origin === origin)
  if (cards.length === 0) return null
  return (
    <div className="grid gap-3" aria-label="Suggested adaptations">
      {cards.map((c) => (
        <Card key={c.id} className="border-accent">
          <CardTitle>Suggestion: {c.what}</CardTitle>
          <p className="text-sm">{c.why}</p>
          <p className="text-sm text-muted mt-1">
            Would set <code>{c.pref}</code> to <code>{String(c.value)}</code>. Reversible.
          </p>
          <div className="flex flex-wrap gap-2 mt-3">
            {CHOICES.filter(
              (ch) =>
                !(ch.decision === 'try' && !sessionId) && // a trial needs a running session
                !(ch.decision === 'default' && c.pref === 'session.plan'), // a plan has no default
            ).map((ch) => (
              <Button
                key={ch.decision}
                variant={ch.decision === 'try' ? 'primary' : 'secondary'}
                disabled={decide.isPending}
                title={ch.hint}
                onClick={() => decide.mutate({ id: c.id, decision: ch.decision, sessionId })}
              >
                {ch.label}
              </Button>
            ))}
          </div>
          {decide.isError && (
            <p role="alert" className="text-warn mt-2">
              {(decide.error as Error).message}
            </p>
          )}
        </Card>
      ))}
    </div>
  )
}

/** The log with undo, shown under Preferences. */
export function AdaptationLog() {
  const { log, undo } = useAdaptationLog()
  const entries = log.data?.entries ?? []
  return (
    <Card>
      <CardTitle>Adaptation log</CardTitle>
      <p className="text-sm text-muted mb-2">
        Every change the system suggested, what you decided, and whether it is in effect. Anything in effect
        can be undone here.
      </p>
      {entries.length === 0 ? (
        <p className="text-sm">No suggestions yet.</p>
      ) : (
        <ul className="grid gap-2 text-sm">
          {entries.map((e) => (
            <li key={e.id} className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>{e.what}</span>
              <span className="text-muted">
                {e.decision ? `decided: ${e.decision}` : 'open'}
                {e.trial && e.decision === 'try' ? ' (one session)' : ''}
                {e.undone_at ? ' · undone' : e.in_effect ? ' · in effect' : ''}
              </span>
              {e.in_effect && (
                <Button size="sm" onClick={() => undo.mutate(e.id)} disabled={undo.isPending}>
                  Undo
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
