import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Choice } from '../components/ui/choice'
import { AdaptationCards } from '../features/adaptations/AdaptationCards'
import { PromotedReminders } from '../features/parking/ParkedList'
import { useExperiments } from '../features/experiments/api'
import { usePreferences } from '../features/preferences/api'
import { useCurrentSession, useStartSession } from '../features/session/api'
import type { SessionOut } from '../lib/api'
import { MODE_LABELS, useMode, type Mode } from '../stores/mode'

export function Home() {
  const { mode, energy, socratic, setMode, setEnergy, setSocratic, setSession, sessionId } = useMode()
  const start = useStartSession()
  const nav = useNavigate()
  const [offer, setOffer] = useState<SessionOut | null>(null)
  const current = useCurrentSession()
  const resumable = current.data && current.data.id
  const prefs = usePreferences()
  const experiments = useExperiments()
  const defaultMode = (prefs.data?.values as Record<string, unknown> | undefined)?.['session.default_mode']
  const preselected = useRef(false)
  // Preferences (incl. accepted adaptation cards) preselect the mode once per visit; the learner
  // still chooses. Zustand is an external store, so syncing it from an effect is the intended way.
  useEffect(() => {
    if (sessionId || preselected.current || typeof defaultMode !== 'string') return
    preselected.current = true
    if (defaultMode !== useMode.getState().mode) useMode.getState().setMode(defaultMode as Mode)
  }, [defaultMode, sessionId])
  const nodeExperiment = (experiments.data?.experiments ?? []).find(
    (e) => e.status === 'running' && e.unit_type === 'node',
  )

  async function begin() {
    const s = await start.mutateAsync({ mode, energy, socratic })
    setSession(s.id, s.next_skill?.id ?? null)
    // Offer, never auto-route: the learner picks which comes first.
    if (s.due_reviews > 0) setOffer(s)
    else nav('/session')
  }

  if (offer) {
    const lowEnergy = offer.mode === 'low_capacity' || offer.energy <= 2
    const capped = Math.min(offer.review_cap, offer.due_reviews)
    return (
      <Card>
        <CardTitle>Which first?</CardTitle>
        <p className="text-sm text-muted mb-3">
          {lowEnergy
            ? `Low energy: the shortest useful path is a capped review (${capped} of ${offer.due_reviews} due), then recap.`
            : `${offer.due_reviews} items are due; the planner suggests review before new material.`}
        </p>
        <div className="flex gap-2 flex-wrap">
          <Button variant={lowEnergy ? 'primary' : 'secondary'} onClick={() => nav('/review')}>
            Review ({capped} of {offer.due_reviews} due)
          </Button>
          <Button variant={lowEnergy ? 'secondary' : 'primary'} onClick={() => nav('/session')}>
            New material: {offer.next_skill?.title ?? 'next skill'}
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <div className="grid gap-4">
      <AdaptationCards />
      <PromotedReminders />
      <Card>
        <CardTitle>Set up this session</CardTitle>
        <Choice<Mode>
          label="State mode"
          options={(Object.keys(MODE_LABELS) as Mode[]).map((m) => ({
            value: m,
            label: MODE_LABELS[m].title,
            hint: MODE_LABELS[m].hint,
          }))}
          value={mode}
          onChange={setMode}
        />
        {typeof defaultMode === 'string' && defaultMode === mode && !sessionId && (
          <p className="text-sm text-muted mt-1">
            Preselected from your default (Preferences). Change it freely.
          </p>
        )}
        <div className="mt-4">
          <Choice<number>
            label="Energy (1 = running on empty, 5 = plenty)"
            options={[1, 2, 3, 4, 5].map((n) => ({
              value: n,
              label: String(n),
            }))}
            value={energy}
            onChange={setEnergy}
            columns={5}
          />
        </div>
        <div className="mt-4">
          <Choice<'explicit' | 'socratic'>
            label="Questioning style for this session"
            options={[
              {
                value: 'explicit',
                label: 'Explicit (default)',
                hint: 'Direct explanations in short steps.',
              },
              {
                value: 'socratic',
                label: 'Socratic',
                hint: 'One narrowing question per turn.',
              },
            ]}
            value={socratic ? 'socratic' : 'explicit'}
            onChange={(v) => setSocratic(v === 'socratic')}
            columns={2}
          />
          {nodeExperiment && (
            <p className="text-sm text-muted mt-1" role="status">
              An experiment is running ("{nodeExperiment.name}"): on assigned skills the experiment's style
              replaces this choice. Stop it under Experiments to get full control back.
            </p>
          )}
        </div>
      </Card>
      <div className="flex gap-2 flex-wrap">
        <Button variant="primary" size="lg" onClick={() => void begin()} disabled={start.isPending}>
          {start.isPending ? 'Starting…' : 'Start session'}
        </Button>
        {(sessionId || resumable) && (
          <Button
            size="lg"
            onClick={() => {
              if (current.data)
                setSession(
                  current.data.id,
                  current.data.checkpoint?.skill_id
                    ? String(current.data.checkpoint.skill_id)
                    : (current.data.next_skill?.id ?? null),
                )
              nav(current.data?.checkpoint?.phase === 'review' ? '/review' : '/session')
            }}
          >
            Resume session{current.data?.checkpoint?.phase ? ` (${current.data.checkpoint.phase})` : ''}
          </Button>
        )}
      </div>
      {start.isError && (
        <p role="alert" className="text-warn">
          Could not start: {(start.error as Error).message}
        </p>
      )}
    </div>
  )
}
