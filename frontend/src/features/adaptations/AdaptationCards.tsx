import { ApiError } from '../../lib/api'
import { PlanPreview, PlanRecovery } from './PlanReview'
import { Disclosure } from '../../components/ui/disclosure'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { useMode } from '../../stores/mode'
import { useAdaptationLog, usePendingAdaptations, type Decision } from './api'

const CHOICES: Array<{ decision: Decision; label: string; hint: string }> = [
  {
    decision: 'try',
    label: 'Try for this session',
    hint: 'Reverts when the next session starts; you may be asked again.',
  },
  { decision: 'default', label: 'Make this my default', hint: 'Stays until you undo it in Preferences.' },
  { decision: 'no', label: 'Not now', hint: 'May be suggested again in 14 days.' },
  { decision: 'never', label: "Don't suggest this again", hint: 'Never for this pattern.' },
]

/** Proposal cards. The system never applies these on its own: one of four explicit choices. */
export function AdaptationCards({ origin, collapsed = false }: { origin?: 'planner' | 'observed_pattern'; collapsed?: boolean } = {}) {
  const pending = usePendingAdaptations()
  const { decide } = useAdaptationLog()
  const { sessionId } = useMode()
  const cards = (pending.data?.proposals ?? []).filter((c) => !origin || c.origin === origin)
  if (cards.length === 0) return null
  const content = (
    <div className="grid min-w-0 grid-cols-1 gap-3 [overflow-wrap:anywhere]" role="region" aria-label="Suggested adaptations">
      {cards.map((c) => (
        <Card key={c.id} className="min-w-0 border-accent">
          <CardTitle>Suggestion: {c.what}</CardTitle>
          <p className="text-sm">{c.why}</p>
          <p className="text-sm text-muted mt-1">Nothing changes until you choose. Review applied adjustments in Preferences.</p>
          {c.pref === 'session.plan' && c.plan_state === 'ready' && <PlanPreview proposal={c} />}
          {c.pref === 'session.plan' && (c.plan_state === 'stale' || (decide.variables?.id === c.id && decide.error instanceof ApiError && decide.error.code === 'stale_plan')) && <PlanRecovery id={c.id} />}
          {c.plan_state === 'ended' && <p className="text-sm">This session has ended. Its plan is kept in history.</p>}
          <Disclosure className="mt-2" label="Technical details">
            <p className="text-sm">Preference: <code>{c.pref}</code> · Proposed value: <code>{String(c.value)}</code>.</p>
          </Disclosure>
          <div className="flex flex-wrap gap-2 mt-3">
            {CHOICES.filter(
              (ch) =>
                c.plan_state !== 'stale' &&
                !(c.pref === 'session.plan' && decide.variables?.id === c.id && decide.error instanceof ApiError && decide.error.code === 'stale_plan') &&
                !(ch.decision === 'try' && !(c.session_id ?? sessionId)) && // a trial needs a running session
                !(ch.decision === 'default' && c.pref === 'session.plan') &&
                !(ch.decision === 'try' && c.pref === 'session.plan' && c.plan_state !== 'ready'), // a plan has no default
            ).map((ch) => (
              <Button
                key={ch.decision}
                className="min-w-0 max-w-full whitespace-normal"
                variant={ch.decision === 'try' ? 'primary' : ch.decision === 'default' ? 'secondary' : 'ghost'}
                disabled={decide.isPending}
                title={ch.hint}
                onClick={() => decide.mutate({ id: c.id, decision: ch.decision, sessionId: c.session_id ?? sessionId })}
              >
                {c.pref === 'session.plan' && ch.decision === 'try' ? 'Apply reviewed plan' : ch.label}
              </Button>
            ))}
          </div>
          {decide.isError && decide.variables?.id === c.id && (
            <p role="alert" className="text-warn mt-2">
              {(decide.error as Error).message}
            </p>
          )}
        </Card>
      ))}
    </div>
  )
  return collapsed ? <Disclosure label={`Optional learning adjustments (${cards.length})`}>{content}</Disclosure> : content
}

/** The log with undo, shown under Preferences. */
export function AdaptationLog() {
  const { log, undo } = useAdaptationLog()
  const entries = log.data?.entries ?? []
  return (
    <Card>
      <CardTitle>Adaptation log</CardTitle>
      <p className="text-sm text-muted mb-2">
        Every suggested change and your decision. Undo is available when the session still matches; otherwise review a new adjustment for the remaining activities.
      </p>
      {log.isPending && <p role="status">Loading adaptation history…</p>}
      {log.isError && <p role="alert">Could not load adaptation history. {entries.length > 0 && 'Showing the last loaded records. '}<Button onClick={() => void log.refetch()} disabled={log.isFetching}>Retry history</Button></p>}
      {undo.isError && <p role="alert">Could not undo this adjustment. {(undo.error as Error).message}</p>}
      {log.isSuccess && entries.length === 0 ? (
        <p className="text-sm">No suggestions yet.</p>
      ) : (
        <ul className="grid gap-2 text-sm">
          {entries.map((e) => (
            <li key={e.id} className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>{e.what}</span>
              <span className="text-muted">
                {e.plan_state === 'superseded' ? 'Replaced by an updated preview' : e.decision === 'try' ? 'Tried for a session' : e.decision === 'default' ? 'Made default' : e.decision === 'no' ? 'Declined for now' : e.decision === 'never' ? 'Suggestions disabled for this pattern' : 'Awaiting a decision'}
                {e.trial && e.decision === 'try' ? ' (one session)' : ''}
                {e.undone_at ? ' · undone' : e.in_effect ? ' · in effect' : ''}
              </span>
              {e.in_effect && e.pref === 'session.plan' && (e.plan_state === 'stale' || (undo.variables === e.id && undo.error instanceof ApiError && undo.error.code === 'stale_plan')) && <PlanRecovery id={e.id} fromUndo />}
              {e.in_effect && (e.pref !== 'session.plan' || (e.plan_state === 'ready' && !(undo.variables === e.id && undo.error instanceof ApiError && undo.error.code === 'stale_plan'))) && (
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
