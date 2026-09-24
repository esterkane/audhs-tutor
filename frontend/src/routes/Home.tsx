import { useAreas } from '../features/areas/api'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Choice } from '../components/ui/choice'
import { AdaptationCards } from '../features/adaptations/AdaptationCards'
import { PromotedReminders } from '../features/parking/ParkedList'
import { useExperiments } from '../features/experiments/api'
import { usePreferences, useSetPreference } from '../features/preferences/api'
import { useMaterial } from '../features/curriculum/api'
import { useSkills } from '../features/skills/api'
import { usePlanPreview } from '../features/plan/api'
import {
  REVIEW_BLOCK_TYPES,
  firstIndex,
  routeForPhase,
  useBlockTransition,
  useCurrentSession,
  useStartSession,
} from '../features/session/api'
import type { SessionOut } from '../lib/api'
import type { Block } from '../features/plan/api'
import { skipNote, startLabel } from '../features/plan/labels'
import { MODE_LABELS, useMode, type Mode } from '../stores/mode'

export function Home() {
  const { mode, energy, socratic, setMode, setEnergy, setSocratic, setSession, sessionId } = useMode()
  const start = useStartSession()
  const nav = useNavigate()
  const [offer, setOffer] = useState<SessionOut | null>(null)
  const transition = useBlockTransition(offer?.id ?? sessionId)
  const current = useCurrentSession()
  const resumable = current.data && current.data.id
  const prefs = usePreferences()
  const setPref = useSetPreference()
  const material = useMaterial()
  const skills = useSkills()
  const preview = usePlanPreview(mode, energy)
  const experiments = useExperiments()
  const goal = String((prefs.data?.values as Record<string, unknown> | undefined)?.['goal.course'] ?? '')
  const areas = useAreas()
  const areaGoal = String(prefs.data?.values?.['goal.area'] ?? '')
  const publishedCourses = (material.data?.courses ?? []).filter((c) => c.published_skills > 0)
  const defaultMode = (prefs.data?.values as Record<string, unknown> | undefined)?.['session.default_mode']
  const preselected = useRef(false)
  // Preferences (incl. accepted adaptation cards) preselect the mode once per visit; the learner
  // still chooses. Zustand is an external store, so syncing it from an effect is the intended way.
  useEffect(() => {
    if (sessionId || preselected.current || typeof defaultMode !== 'string') return
    preselected.current = true
    if (defaultMode !== useMode.getState().mode) useMode.getState().setMode(defaultMode as Mode)
  }, [defaultMode, sessionId])
  const runningExperiment = (experiments.data?.experiments ?? []).find((e) => e.status === 'running')

  async function begin() {
    const s = await start.mutateAsync({ mode, energy, socratic })
    setSession(s.id, s.state?.skill_id ?? s.next_skill?.id ?? null)
    // Offer, never auto-route: the learner picks which comes first. Without due items the plan
    // starts at its first block on the session screen (StartCard).
    if (s.due_reviews > 0) setOffer(s)
    else nav('/session')
  }

  /** Plan semantics: "review first" starts the first review block; "new material first" starts
   *  the first non-review block (a movement primer counts as preparation for new material).
   *  Blocks before the chosen one are not started; they show as passed over in the plan strip. */
  async function chooseFirst(which: 'review' | 'learn') {
    if (!offer || transition.pending) return
    const plan = (offer.plan ?? []) as Array<{ type: string }>
    const index =
      which === 'review'
        ? firstIndex(plan, (t) => REVIEW_BLOCK_TYPES.includes(t))
        : firstIndex(plan, (t) => !REVIEW_BLOCK_TYPES.includes(t))
    if (index == null) {
      nav(which === 'review' ? '/review' : '/session') // off-plan review or the start card
      return
    }
    const state = await transition.start(index)
    nav(routeForPhase(state))
  }

  if (offer) {
    const lowEnergy = offer.mode === 'low_capacity' || offer.energy <= 2
    const capped = Math.min(offer.review_cap, offer.due_reviews)
    const plan = (offer.plan ?? []) as Block[]
    const reviewIx = firstIndex(plan, (t) => REVIEW_BLOCK_TYPES.includes(t))
    const learnIx = firstIndex(plan, (t) => !REVIEW_BLOCK_TYPES.includes(t))
    return (
      <Card>
        <CardTitle>Which first?</CardTitle>
        <p className="text-sm text-muted mb-3">
          {lowEnergy
            ? `Low energy: the shortest useful path is a capped review (${capped} of ${offer.due_reviews} due), then recap.`
            : `${offer.due_reviews} items are due; the planner suggests review before new material.`}
        </p>
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={lowEnergy ? 'primary' : 'secondary'}
            onClick={() => void chooseFirst('review')}
            disabled={transition.pending}
          >
            Review ({capped} of {offer.due_reviews} due){reviewIx != null ? skipNote(plan, reviewIx) : ''}
          </Button>
          <Button
            variant={lowEnergy ? 'secondary' : 'primary'}
            onClick={() => void chooseFirst('learn')}
            disabled={transition.pending}
          >
            {learnIx != null
              ? startLabel(plan, learnIx, offer.next_skill?.title)
              : `New material: ${offer.next_skill?.title ?? 'next skill'}`}
          </Button>
        </div>
        {transition.error && (
          <p role="alert" className="text-warn mt-2">
            {transition.error.message}
          </p>
        )}
      </Card>
    )
  }

  // "Next up" is always a skill title: from the running session, else the map's next node.
  // A block *reason* ("worked example first") is scaffolding, never shown as a title.
  const mapNext = skills.data?.skills.find((n) => n.id === skills.data?.next_skill_id) ?? null
  const nextSkill = current.data?.next_skill ?? mapNext
  const scaffold = preview.data?.blocks.find((b) => b.type === 'new_material')?.reason
  return (
    <div className="grid gap-4">
      <AdaptationCards />
      <PromotedReminders />
      <Card>
        <CardTitle>Learn toward</CardTitle>
        <label className="block text-sm font-medium mt-2">
          Knowledge area
          <select
            className="block border border-line rounded-md px-2 py-1 mt-1"
            value={areaGoal}
            onChange={(e) => setPref.mutate({ key: 'goal.area', value: e.target.value })}
          >
            <option value="">Whole map or course goal below</option>
            {(areas.data?.areas ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.title}
              </option>
            ))}
          </select>
        </label>
        <p className="text-sm text-muted my-2">
          An area goal takes precedence over the course goal below and uses activated lessons across sources.
          Until it has active lessons, the whole map remains available.{' '}
          <Link to="/areas">Review learning areas</Link>
        </p>
        <div className="flex flex-wrap gap-2 items-end">
          <label className="text-sm font-medium">
            Goal
            <select
              className="block border border-line rounded-md px-2 py-1 mt-1"
              value={goal}
              disabled={Boolean(areaGoal)}
              onChange={(e) => setPref.mutate({ key: 'goal.course', value: e.target.value })}
            >
              <option value="">Whole skill map</option>
              {publishedCourses.map((c) => (
                <option key={c.course} value={c.course}>
                  {c.course} ({c.published_skills} skills)
                </option>
              ))}
            </select>
          </label>
          <span className="text-sm text-muted">
            {publishedCourses.length === 0
              ? 'No published course lessons yet — publish a draft under Lessons to learn toward a course.'
              : goal
                ? `Next skills come from "${goal}" first (its unlocked, unmastered skills in prerequisite order).`
                : 'The next skill is the first unlocked, unmastered node on the whole map.'}
          </span>
        </div>
        {setPref.isError && (
          <p role="alert" className="text-sm text-warn mt-2">
            The goal was not saved: {(setPref.error as Error).message}
          </p>
        )}
        {nextSkill && (
          <p className="text-sm mt-2">
            Next up: <span className="font-medium">{nextSkill.title}</span>
            {` — mastery ${Math.round((nextSkill.mastery ?? 0) * 100)}%, prerequisites met`}
            {scaffold ? ` · ${scaffold}` : ''}
          </p>
        )}
      </Card>
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
        <p className="text-sm text-muted mt-3" role="status">
          {preview.data
            ? `Planned: ${preview.data.blocks
                .map(
                  (b) => `${b.type.replace('_', ' ')} ${b.planned_min} min${b.optional ? ' (optional)' : ''}`,
                )
                .join(' → ')} · about ${preview.data.total_min} min in total.`
            : 'Planning…'}
        </p>
        <details className="mt-3">
          <summary className="cursor-pointer text-sm font-medium">
            More options · questioning style:{' '}
            {socratic ? 'Socratic (chosen for this session)' : 'Explicit (default)'}
          </summary>
          <div className="mt-2">
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
            {runningExperiment && (
              <p className="text-sm text-muted mt-1" role="status">
                An experiment is running ("{runningExperiment.name}"):{' '}
                {runningExperiment.unit_type === 'node'
                  ? "on assigned skills the experiment's arm replaces this choice"
                  : 'this session may be assigned an arm that replaces this choice (the session screen says which)'}
                . Stop it under Experiments to get full control back.
              </p>
            )}
          </div>
        </details>
      </Card>
      <div className="flex gap-2 flex-wrap">
        {(sessionId || resumable) && (
          <Button
            variant="primary"
            size="lg"
            onClick={() => {
              if (current.data)
                setSession(
                  current.data.id,
                  current.data.state?.skill_id ?? current.data.next_skill?.id ?? null,
                )
              nav(routeForPhase(current.data?.state))
            }}
          >
            Resume session
            {current.data?.state?.block_status === 'running' && current.data.state.phase
              ? ` (${current.data.state.phase})`
              : ''}
          </Button>
        )}
        <Button
          variant={sessionId || resumable ? 'secondary' : 'primary'}
          size="lg"
          onClick={() => void begin()}
          disabled={start.isPending}
        >
          {start.isPending ? 'Starting…' : 'Start session'}
        </Button>
      </div>
      {start.isError && (
        <p role="alert" className="text-warn">
          Could not start: {(start.error as Error).message}
        </p>
      )}
    </div>
  )
}
