import { useStopSession } from '../features/session/useStopSession'
import { SessionControls } from '../features/session/SessionControls'
import { ReadAloud } from '../features/voice/ReadAloud'
import { readDraft, writeDraft, clearDraft } from '../features/assess/draft'
import { QuestionHelp } from '../features/assess/QuestionHelp'
import { OptionalConfidence } from '../components/OptionalConfidence'
import { QuestionFeedback } from '../features/areas/QuestionFeedback'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Markdown } from '../components/Markdown'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Choice } from '../components/ui/choice'
import { Textarea } from '../components/ui/textarea'
import { useAttempt, useNextItem } from '../features/assess/api'
import { ChallengePanel } from '../features/challenge/ChallengePanel'
import { PlanStrip } from '../features/plan/PlanStrip'
import { BLOCK_LABELS, type Block } from '../features/plan/api'
import { skipNote, startLabel } from '../features/plan/labels'
import { useKinds, usePrefer, useRender, type RenderOut } from '../features/representations/api'
import {
  REVIEW_BLOCK_TYPES,
  firstIndex,
  routeForPhase,
  useBlockTransition,
  useCheckpoint,
  useSession,
} from '../features/session/api'
import { SoftTimer } from '../features/session/SoftTimer'
import { AdaptationCards } from '../features/adaptations/AdaptationCards'
import { PracticePanel } from '../features/practice/PracticePanel'
import { LanguageBlock } from '../features/listening/LanguageBlock'
import { CodeExercise } from '../features/code/CodeExercise'
import { VoicePanel } from '../features/voice/VoicePanel'
import { usePreferences } from '../features/preferences/api'
import { useExercise } from '../features/code/api'
import { useReplan } from '../features/plan/api'
import { useSensory } from '../features/sensory/useSensory'
import { useTutorStream } from '../features/tutor/useTutorStream'
import { SourceViewer } from '../features/curriculum/SourceViewer'
import { useReport } from '../features/curriculum/api'
import type { AttemptResult, SessionOut } from '../lib/api'
import { SOFT_TIMER_MIN, useMode } from '../stores/mode'

type Phase = 'teach' | 'assess' | 'challenge' | 'practice'
function withheldCount(dropped: string[] | undefined): number {
  return (dropped ?? []).filter((d) => d.endsWith(':quarantined')).length
}

export function Session() {
  const { sessionId } = useMode()
  const nav = useNavigate()
  const session = useSession(sessionId)
  if (!sessionId) {
    return (
      <Card>
        <p>No session running.</p>
        <Button variant="primary" onClick={() => nav('/')}>
          Go to Home
        </Button>
      </Card>
    )
  }
  if (session.isLoading || !session.data) return <Card>Loading session…</Card>
  // keyed by the server's block id: a new block (or a resumed session) starts with fresh UI state
  const st = session.data.state
  return (
    <div className="grid gap-4">
      <SessionControls sessionId={sessionId} skillId={st.skill_id} />
      <SessionBody
        key={`${session.data.id}:${st?.block_id ?? 'none'}`} // a re-plan must not wipe the screen
        sessionId={sessionId}
        data={session.data}
      />
    </div>
  )
}

function StartCard({ sessionId, data }: { sessionId: string; data: SessionOut }) {
  const nav = useNavigate()
  const transition = useBlockTransition(sessionId)
  const plan = (data.plan ?? []) as Block[]
  const reviewIx = firstIndex(plan, (t) => REVIEW_BLOCK_TYPES.includes(t))
  const learnIx = firstIndex(plan, (t) => !REVIEW_BLOCK_TYPES.includes(t))
  const [note, setNote] = useState<string | null>(null)
  async function beginChecked(index: number) {
    if (transition.pending) return
    const state = await transition.start(index)
    if (!state.allowed) {
      setNote(state.message)
      return
    }
    nav(routeForPhase(state))
  }
  async function continuePlan() {
    if (transition.pending || !data.state) return
    const state = await transition.next({ from_index: data.state.block_index ?? null, reason: 'finished' })
    if (!state.allowed) {
      setNote(state.message)
      return
    }
    nav(state.plan_complete ? '/recap' : routeForPhase(state))
  }
  if (data.state?.plan_complete)
    return (
      <Card>
        <CardTitle>Plan complete</CardTitle>
        <p className="text-sm text-muted">Every planned block is done. Finish with the recap.</p>
        <Button variant="primary" className="mt-3" onClick={() => nav('/recap')}>
          Recap
        </Button>
      </Card>
    )
  // a block ended (stop, then a change of mind): continue where the plan is, never restart it
  if (data.state?.block_status === 'ended' && data.state.next_index != null) {
    const nextBlock = plan[data.state.next_index]
    return (
      <Card>
        <CardTitle>Continue the plan?</CardTitle>
        <PlanStrip blocks={plan} current={-1} firstStarted={data.state.first_started_index} />
        <div className="flex gap-2 flex-wrap mt-3">
          <Button variant="primary" onClick={() => void continuePlan()} disabled={transition.pending}>
            Continue: {BLOCK_LABELS[nextBlock.type] ?? nextBlock.type} ({nextBlock.planned_min} min)
          </Button>
          <Button onClick={() => nav('/recap')}>Finish session</Button>
        </div>
        {note && (
          <p role="status" className="text-sm text-warn mt-2">
            {note}
          </p>
        )}
      </Card>
    )
  }
  return (
    <Card>
      <CardTitle>Choose where to begin</CardTitle>
      <p className="text-sm text-muted mb-3">
        Follow the plan one activity at a time. You can stop and recap at any point.
      </p>
      <PlanStrip blocks={plan} current={-1} />
      <div className="flex gap-2 flex-wrap mt-3">
        {learnIx != null && (
          <Button variant="primary" onClick={() => void beginChecked(learnIx)} disabled={transition.pending}>
            {startLabel(plan, learnIx, data.active_skill?.title ?? data.next_skill?.title)}
          </Button>
        )}
        {reviewIx != null && data.due_reviews > 0 && (
          <Button onClick={() => void beginChecked(reviewIx)} disabled={transition.pending}>
            Review first ({data.due_reviews} due){skipNote(plan, reviewIx)}
          </Button>
        )}
        {!plan.length && (
          <Button variant="primary" onClick={() => nav('/recap')}>
            No blocks planned — recap
          </Button>
        )}
      </div>
      {note && (
        <p role="status" className="text-sm text-warn mt-2">
          {note}
        </p>
      )}
      {transition.error && (
        <p role="alert" className="text-warn mt-2">
          {transition.error.message}
        </p>
      )}
    </Card>
  )
}

function SessionBody({ sessionId, data }: { sessionId: string; data: SessionOut }) {
  const stopSession = useStopSession(sessionId)
  const { skillId, setSkill, mode, setEnergy } = useMode()
  const nav = useNavigate()
  const checkpoint = useCheckpoint()
  const transition = useBlockTransition(sessionId)
  const replan = useReplan()
  const { notifications } = useSensory()
  const st = data.state
  const plan = (data.plan ?? []) as Block[]
  const blockIndex = st?.block_status === 'running' ? (st.block_index ?? null) : null
  const currentBlock = blockIndex != null ? plan[blockIndex] : undefined
  // the server phase says which screen; within the session screen the learner moves teach ↔ assess
  const serverPhase = st?.phase
  const [phase, setPhase] = useState<Phase>(() =>
    serverPhase === 'assess' ||
    serverPhase === 'challenge' ||
    serverPhase === 'practice' ||
    serverPhase === 'teach'
      ? serverPhase
      : 'teach',
  )
  const [hintCount, setHintCount] = useState(0)
  const [graspPassed, setGraspPassed] = useState(false)
  const [blockNote, setBlockNote] = useState<string | null>(null)
  const skill = data.active_skill ?? data.next_skill // the block's skill, not the map's recommendation
  const activeSkillId = st?.skill_id ?? skill?.id ?? null

  // Zustand is an external store: syncing it from an effect is the intended pattern.
  useEffect(() => {
    if (activeSkillId && skillId !== activeSkillId) setSkill(activeSkillId)
  }, [activeSkillId, skillId, setSkill])
  // a running review/recap block belongs to another screen
  useEffect(() => {
    if (blockIndex != null && (serverPhase === 'review' || serverPhase === 'recap')) nav(routeForPhase(st))
  }, [blockIndex, serverPhase, st, nav])

  if (blockIndex == null || !currentBlock) return <StartCard sessionId={sessionId} data={data} />

  const timerMinutes = currentBlock.planned_min ?? SOFT_TIMER_MIN[mode]

  function changePhase(p: Phase) {
    setPhase(p)
    void checkpoint.mutateAsync({
      id: sessionId,
      body: { phase: p, skill_id: activeSkillId, block_index: blockIndex ?? undefined },
    })
  }

  async function finishBlock(reason: 'finished' | 'save_and_stop' | 'switch_early' | 'skipped') {
    if (transition.pending || blockIndex == null) return
    try {
      await doFinish(reason)
    } catch {
      /* transition.error is rendered; nothing changed on the server */
    }
  }

  async function doFinish(reason: 'finished' | 'save_and_stop' | 'switch_early' | 'skipped') {
    if (blockIndex == null) return
    if (reason === 'save_and_stop') {
      await stopSession.mutateAsync()
      return
    }
    const res = await transition.next({ from_index: blockIndex, reason, grasp_passed: graspPassed })
    if (!res.allowed) {
      setBlockNote(res.message)
      changePhase('assess')
      return
    }
    setBlockNote(null)
    if (res.plan_complete || res.block_index == null) {
      nav('/recap')
      return
    }
    const route = routeForPhase(res)
    if (route !== '/session') nav(route)
    // staying on /session: the new block id re-keys SessionBody, which resets phase/hints/grasp
  }

  return (
    <div className="grid gap-4">
      <AdaptationCards origin="planner" />
      {stopSession.error && <p role="alert">{stopSession.error.message}</p>}
      <Card>
        <p className="text-sm text-muted">
          Activity {blockIndex + 1} of {plan.length} · {BLOCK_LABELS[currentBlock.type] ?? currentBlock.type}{' '}
          · about {timerMinutes} min
        </p>
        <p className="text-sm mt-2">
          {phase === 'teach'
            ? 'Start with an explanation. Try a question when ready, or save this topic for later.'
            : phase === 'assess'
              ? 'Read the context, use a hint if helpful, and try an answer when ready.'
              : phase === 'challenge'
                ? 'Apply the idea to a challenge, then continue the plan.'
                : 'Follow the activity below. When you finish or skip it, the next activity opens.'}
        </p>
        {data.experiment && (
          <p className="text-sm mt-2" role="status">
            Experiment "{String(data.experiment.name)}":{' '}
            {data.experiment.arm
              ? `this session runs the "${String(data.experiment.arm)}" arm`
              : 'each skill keeps the arm it was assigned to (shown per turn)'}
            .
          </p>
        )}
        <details className="mt-3">
          <summary className="cursor-pointer text-sm">Session plan and energy settings</summary>
          <div className="mt-3">
            <PlanStrip blocks={plan} current={blockIndex} firstStarted={st?.first_started_index} />
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
              <span id="energy-now">Energy now:</span>
              <div role="group" aria-labelledby="energy-now" className="flex gap-1">
                {[1, 2, 3, 4, 5].map((n) => (
                  <Button
                    key={n}
                    size="sm"
                    pressed={data.energy === n}
                    disabled={replan.isPending}
                    aria-label={`Energy ${n}`}
                    onClick={() => {
                      if (n === data.energy) return
                      setEnergy(n)
                      void replan.mutateAsync({ session_id: sessionId, energy: n, from_index: blockIndex })
                    }}
                  >
                    {n}
                  </Button>
                ))}
              </div>
              <span className="text-muted">
                A change re-plans the remaining blocks as a suggestion, never silently; the review cap follows
                your energy at once (undo: "Show all" on the review screen).
              </span>
            </div>
          </div>
        </details>
        <CardTitle className="mt-3">
          {phase === 'practice'
            ? `${currentBlock.domain === 'language' ? 'Language' : currentBlock.domain === 'guitar' ? 'Guitar' : 'Movement'} block`
            : `${phase === 'teach' ? 'Learn' : phase === 'assess' ? 'Check yourself' : 'Challenge'}: ${skill?.title ?? '…'}`}
        </CardTitle>
        {skill && (phase === 'teach' || phase === 'assess') && (
          <div className="mt-2 text-sm">
            <h3 className="font-medium">What you are learning</h3>
            <p className="mt-1">{skill.description || skill.title}</p>
            <ReadAloud key={skill.id} text={skill.description || skill.title} />
          </div>
        )}
        {blockNote && (
          <p role="status" className="text-sm text-warn mt-2">
            {blockNote}
          </p>
        )}
        {transition.error && (
          <p role="alert" className="text-sm text-warn mt-2">
            {transition.error.message} — nothing was changed; try again.
          </p>
        )}
      </Card>
      {(phase === 'teach' || phase === 'assess') && (
        <div hidden={phase !== 'teach'}>
          <TeachPanel
            active={phase === 'teach'}
            sessionId={sessionId}
            skillId={activeSkillId}
            onCheck={() => changePhase('assess')}
            onHintLevel={setHintCount}
            onSwitchEarly={() => void finishBlock('switch_early')}
          />
        </div>
      )}
      {phase === 'assess' && (
        <AssessPanel
          sessionId={sessionId}
          skillId={activeSkillId}
          hintCount={hintCount}
          onBack={() => changePhase('teach')}
          onGraded={(r) => {
            setHintCount(0)
            if (r.score >= 0.85) setGraspPassed(true)
          }}
          onFinishBlock={() => void finishBlock('finished')}
          transitionPending={transition.pending}
        />
      )}
      {(phase === 'teach' || phase === 'assess') && activeSkillId && (
        <OptionalExercise sessionId={sessionId} skillId={activeSkillId} mastery={skill?.mastery ?? 0} />
      )}
      {phase === 'challenge' && (
        <ChallengePanel
          sessionId={sessionId}
          skillId={activeSkillId}
          onDone={() => void finishBlock('finished')}
        />
      )}
      {phase === 'practice' && currentBlock.domain === 'language' && (
        <LanguageBlock sessionId={sessionId} onDone={() => void finishBlock('finished')} />
      )}
      {phase === 'practice' && currentBlock.domain !== 'language' && (
        <PracticePanel
          sessionId={sessionId}
          domain={currentBlock.domain === 'guitar' ? 'guitar' : 'movement'}
          plannedMin={currentBlock.planned_min}
          onDone={() => void finishBlock('finished')}
          onSkip={() => void finishBlock('skipped')}
        />
      )}
      {st?.block_started_at && (
        <SoftTimer
          key={st.block_id ?? String(blockIndex)}
          blockKey={st.block_id ?? String(blockIndex)}
          startedAt={st.block_started_at}
          plannedMin={timerMinutes}
          extensionMin={st.timer_extension_min ?? 0}
          onExtend={(min) => void transition.extend(blockIndex, min)}
          onSaveStop={() => void finishBlock('save_and_stop')}
          onFinishBlock={() => void finishBlock('finished')}
          notify={notifications}
          pending={transition.pending}
        />
      )}
    </div>
  )
}

function TeachPanel({
  active,
  sessionId,
  skillId,
  onCheck,
  onHintLevel,
  onSwitchEarly,
}: {
  sessionId: string
  skillId: string | null
  onCheck: () => void
  onHintLevel: (n: number) => void
  onSwitchEarly: () => void
  active: boolean
}) {
  const [input, setInput] = useState('')
  const { text, meta, done, error, busy, run, stop } = useTutorStream()
  useEffect(() => {
    if (!active) stop()
  }, [active, stop])
  const kinds = useKinds(skillId)
  const render = useRender()
  const prefer = usePrefer()
  const [alt, setAlt] = useState<RenderOut | null>(null)
  const [prevAlt, setPrevAlt] = useState<RenderOut | null>(null)
  const [openSource, setOpenSource] = useState<{
    chunkId: string
    citation: string
    turnId: string
  } | null>(null)
  const reportTurn = useReport()
  const prefs = usePreferences()
  const voiceOn = (prefs.data?.values as Record<string, unknown> | undefined)?.['voice.enabled'] === true
  const [talking, setTalking] = useState(false)
  const base = { session_id: sessionId, skill_id: skillId }
  useEffect(() => {
    if (meta) onHintLevel(meta.hint_level)
  }, [meta, onHintLevel])
  // "Reported" and an open source belong to one turn: derived, so a new answer starts clean
  const reportedThisTurn =
    reportTurn.isSuccess && done != null && reportTurn.variables?.turn_id === done.turn_id
  const sourceForThisTurn = openSource && done && openSource.turnId === done.turn_id ? openSource : null

  async function showDifferently(kind: string) {
    if (!skillId) return
    const out = await render.mutateAsync({ skillId, kind, sessionId })
    setPrevAlt(alt)
    setAlt(out)
  }

  return (
    <>
      <Card>
        <label htmlFor="ask" className="text-sm font-medium">
          Ask about this lesson (optional)
        </label>
        <Textarea
          id="ask"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Leave empty to start with an explanation."
        />
        <div className="flex gap-2 flex-wrap mt-2">
          <Button
            variant={done || alt ? 'secondary' : 'primary'}
            disabled={busy}
            onClick={() =>
              void run({
                ...base,
                text: input.trim() || 'Explain the next idea for this skill.',
                action: 'explain',
              })
            }
          >
            {busy ? 'Preparing explanation…' : text ? 'Explain again' : 'Start explanation'}
          </Button>
          <details>
            <summary className="cursor-pointer text-sm py-2">More ways to learn</summary>
            <div className="flex gap-2 flex-wrap mt-2">
              <Button
                disabled={busy}
                onClick={() => void run({ ...base, text: input.trim() || 'I am stuck.', action: 'hint' })}
              >
                Hint
              </Button>
              <Button
                disabled={busy}
                onClick={() =>
                  void run({ ...base, text: input.trim() || 'Recap this skill.', action: 'summarize' })
                }
              >
                Summary of this skill
              </Button>
            </div>
          </details>
          {busy && (
            <Button variant="ghost" onClick={stop}>
              Stop explanation
            </Button>
          )}
          {voiceOn && !talking && (
            <Button variant="ghost" onClick={() => setTalking(true)}>
              Talk instead
            </Button>
          )}
        </div>
      </Card>
      {active && voiceOn && talking && (
        <VoicePanel sessionId={sessionId} skillId={skillId} onClose={() => setTalking(false)} />
      )}
      {(text || busy || error) && (
        <Card aria-busy={busy}>
          {meta && (
            <p className="text-xs text-muted mb-2">
              {meta.action}
              {meta.action === 'hint' ? ` · level ${meta.hint_level}` : ''} · {meta.questioning_style}
              {meta.experiment_arm ? ' · set by the experiment arm' : ''}
              {meta.arm_not_applied ? ' (representation kept: not yet at the mastery this arm needs)' : ''}
            </p>
          )}
          {error ? (
            <p role="alert" className="text-warn">
              {error}
            </p>
          ) : (
            <>
              <Markdown text={text || '…'} />
              {active && done && !busy && <ReadAloud key={done.turn_id} text={text} />}
            </>
          )}
          {done && (
            <p role="status" className="sr-only">
              Answer complete.
            </p>
          )}
          {done && done.outcome === 'partial' && (
            <p className="text-sm text-muted mt-2" role="status">
              Answer cut short — the model stopped mid-way. What you read is what arrived. Ask again, or use
              Hint for the next step.
            </p>
          )}
          {done && done.route && done.route !== 'primary' && (
            <p className="text-xs text-muted mt-2" role="status">
              {done.route === 'degraded'
                ? "Answered by a local model instead of the planned hosted one: today's hosted budget is used up. Nothing else changed."
                : 'Answered by a fallback model: the planned model was not ready. Nothing else changed.'}
            </p>
          )}
          {done && done.registry_id && (
            <details className="text-xs text-muted mt-1">
              <summary className="cursor-pointer">About this answer</summary>
              Model {done.registry_id} ({done.route ?? 'primary'})
              {done.usage_source === 'estimated' ? ' · token usage estimated' : ''}
            </details>
          )}
          {done && done.sources.length > 0 && (
            <details className="mt-3 text-sm text-muted">
              <summary className="cursor-pointer font-medium">Sources for this explanation</summary>
              <ol className="list-decimal ml-5">
                {done.sources.map((s) => (
                  <li key={s.chunk_id}>
                    <button
                      type="button"
                      className="underline text-left"
                      onClick={() =>
                        setOpenSource({ chunkId: s.chunk_id, citation: s.citation, turnId: done.turn_id })
                      }
                    >
                      {s.citation}
                    </button>
                    {s.cited ? '' : ' — not cited'}
                    {(s.flagged ?? []).length > 0 && (
                      <span className="text-warn"> (flagged: {(s.flagged ?? []).join(', ')})</span>
                    )}
                  </li>
                ))}
              </ol>
              {sourceForThisTurn && (
                <div className="mt-2">
                  <SourceViewer
                    key={sourceForThisTurn.chunkId}
                    chunkId={sourceForThisTurn.chunkId}
                    citation={sourceForThisTurn.citation}
                    turnId={done.turn_id}
                    onClose={() => setOpenSource(null)}
                  />
                </div>
              )}
            </details>
          )}
          {done && withheldCount(done.dropped) > 0 && (
            <p className="text-sm text-muted mt-1" role="status">
              {withheldCount(done.dropped)} source{withheldCount(done.dropped) === 1 ? '' : 's'} withheld:
              flagged text from a web or untrusted tier is not sent to the tutor. You can inspect and re-tier
              it under Corpus.
            </p>
          )}
          {done && done.sources.length === 0 && withheldCount(done.dropped) === 0 && (
            <p className="text-sm text-muted mt-2">no course source for this</p>
          )}
          {done && (
            <p className="text-xs mt-2">
              {reportedThisTurn ? (
                <span role="status">Reported — kept next to this turn; nothing was rewritten.</span>
              ) : (
                <button
                  type="button"
                  className="underline text-muted"
                  disabled={reportTurn.isPending}
                  onClick={() =>
                    reportTurn.mutate({
                      kind: 'wrong_explanation',
                      turn_id: done.turn_id,
                      skill_id: skillId,
                      note: '',
                    })
                  }
                >
                  Report this explanation as wrong
                </button>
              )}
            </p>
          )}
        </Card>
      )}
      {alt && (
        <Card>
          <p className="text-xs text-muted mb-2">
            {alt.kind.replace('_', ' ')} · same learning object{alt.cached ? ' · from cache' : ''}
          </p>
          <Markdown text={alt.content} />
          {active && <ReadAloud key={alt.representation_id} text={alt.content} />}
          {prevAlt && prevAlt.representation_id !== alt.representation_id && (
            <div className="mt-3">
              <p className="text-sm font-medium mb-1">Which explanation worked better?</p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => {
                    if (skillId)
                      prefer.mutate({
                        skillId,
                        sessionId,
                        chosenId: alt.representation_id,
                        rejectedId: prevAlt.representation_id,
                      })
                    setPrevAlt(null)
                  }}
                >
                  This one ({alt.kind.replace('_', ' ')})
                </Button>
                <Button
                  size="sm"
                  onClick={() => {
                    if (skillId)
                      prefer.mutate({
                        skillId,
                        sessionId,
                        chosenId: prevAlt.representation_id,
                        rejectedId: alt.representation_id,
                      })
                    setPrevAlt(null)
                  }}
                >
                  The previous one ({prevAlt.kind.replace('_', ' ')})
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
      {!busy && (done || alt) && (
        <Card>
          <p className="text-sm font-medium mb-2">Next: try one question about this idea.</p>
          <div className="flex gap-2 flex-wrap mb-3">
            <Button variant="primary" onClick={onCheck}>
              Try a question
            </Button>
          </div>
          <details>
            <summary className="cursor-pointer text-sm">
              Need another explanation or a different activity?
            </summary>
            <Choice<string>
              label="Show it differently"
              options={(kinds.data?.kinds ?? [])
                .filter((k) => k.allowed)
                .map((k) => ({
                  value: k.kind as string,
                  label: k.label as string,
                  hint: k.cached ? 'cached' : undefined,
                }))}
              value={alt?.kind ?? null}
              onChange={(k) => void showDifferently(k)}
              columns={3}
            />
            {render.isPending && <p className="text-sm text-muted mt-2">Rendering…</p>}
            {render.isError && (
              <p role="alert" className="text-warn mt-2">
                {(render.error as Error).message}
              </p>
            )}
            <Button className="mt-3" variant="ghost" onClick={onSwitchEarly}>
              Request another activity (a check may be required)
            </Button>
          </details>
          <details className="mt-3">
            <summary className="cursor-pointer text-sm">Full solution (explicit request, logged)</summary>
            <Button
              className="mt-2"
              onClick={() => void run({ ...base, text: 'show the full solution', action: 'full_solution' })}
            >
              Show the full solution
            </Button>
          </details>
        </Card>
      )}
    </>
  )
}

function AssessPanel({
  sessionId,
  skillId,
  hintCount,
  onBack,
  onGraded,
  onFinishBlock,
  transitionPending,
}: {
  sessionId: string
  skillId: string | null
  hintCount: number
  onBack: () => void
  onGraded: (r: AttemptResult) => void
  onFinishBlock: () => void
  transitionPending: boolean
}) {
  const [round, setRound] = useState(0)
  const next = useNextItem(sessionId, skillId, round)
  const attempt = useAttempt()
  const [confidence, setConfidence] = useState<number | null>(null)
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState<AttemptResult | null>(null)
  const [startedAt, setStartedAt] = useState(() => Date.now())
  const item = next.data?.item
  const answerKey = `audhs-answer:${sessionId}:${item?.id ?? ''}`
  const savedAnswer = item ? readDraft(answerKey).answer : ''
  const currentAnswer = answer || savedAnswer

  async function submit() {
    if (!item) return
    try {
      const res = await attempt.mutateAsync({
        session_id: sessionId,
        assessment_id: item.id,
        answer: currentAnswer,
        confidence_pre: confidence,
        latency_ms: Date.now() - startedAt,
        hint_count: hintCount + readDraft(answerKey).hints,
      })
      clearDraft(answerKey)
      setResult(res)
      onGraded(res)
    } catch {
      // The mutation alert offers retry; preserve the answer and confidence.
    }
  }

  function nextItem() {
    setStartedAt(Date.now())
    setResult(null)
    setAnswer('')
    setConfidence(null)
    setRound((r) => r + 1)
  }

  if (next.isLoading) return <Card>Loading item…</Card>
  if (!item)
    return (
      <Card>
        <p>No assessment items for this skill yet.</p>
        <Button onClick={onBack}>Back to explanation</Button>
      </Card>
    )

  return (
    <>
      <Card>
        <p className="text-sm text-muted mb-2">
          {item.kind === 'mcq'
            ? 'Choose one answer below.'
            : item.kind === 'cloze'
              ? 'Fill in the missing word or phrase.'
              : item.kind === 'explain_back'
                ? 'Explain in your own words. A short answer is enough.'
                : 'Answer the question below.'}
        </p>
        <p className="text-base mb-3">{item.question}</p>
        {!result && (
          <QuestionHelp
            key={item.id}
            sessionId={sessionId}
            skillId={skillId}
            question={item.question}
            onHint={() => writeDraft(answerKey, { hints: readDraft(answerKey).hints + 1 })}
          />
        )}
        <QuestionFeedback key={item.id} target={{ assessment_id: item.id }} />
        {!result && (
          <>
            {item.kind === 'mcq' && item.options ? (
              <Choice<string>
                label="Your answer"
                options={item.options.map((o, i) => ({ value: String(i), label: o }))}
                value={currentAnswer || null}
                onChange={(value) => {
                  setAnswer(value)
                  writeDraft(answerKey, { answer: value })
                }}
                columns={1}
              />
            ) : (
              <>
                <label htmlFor="answer" className="text-sm font-medium">
                  Your answer
                </label>
                <Textarea
                  id="answer"
                  value={currentAnswer}
                  onChange={(e) => {
                    setAnswer(e.target.value)
                    writeDraft(answerKey, { answer: e.target.value })
                  }}
                />
              </>
            )}
            <div className="mt-3">
              <OptionalConfidence value={confidence} onChange={setConfidence} />
            </div>
            <div className="flex gap-2 mt-3">
              <Button
                variant="primary"
                onClick={() => void submit()}
                disabled={!currentAnswer.trim() || attempt.isPending}
              >
                {attempt.isPending ? 'Checking your answer…' : 'Check my answer'}
              </Button>
              <Button variant="ghost" onClick={onBack}>
                Back to explanation
              </Button>
            </div>
            {attempt.isError && (
              <p role="alert" className="text-warn mt-2">
                {(attempt.error as Error).message}
              </p>
            )}
          </>
        )}
      </Card>
      {result && (
        <Card role="status" className={result.score >= 0.85 ? 'border-ok' : 'border-warn'}>
          <h3 className="font-medium">Feedback on your answer</h3>
          <details className="text-sm text-muted mt-2">
            <summary className="cursor-pointer">Score and grading details</summary>
            <p>
              Score {(result.score * 100).toFixed(0)}% · graded by {result.grader_level} · confidence{' '}
              {result.confidence_pre == null
                ? 'not supplied'
                : `${result.confidence_pre}/5: ${result.calibration}`}
            </p>
          </details>
          <p className="mt-2">{result.feedback}</p>
          <p className="mt-1 text-sm">{result.next_step}</p>
          {result.misconception && (
            <p className="mt-1 text-sm text-warn">Possible misconception: {result.misconception}</p>
          )}
          <ul className="mt-2 text-sm list-disc ml-5">
            {result.criterion_results.map((c) => (
              <li key={c.criterion}>
                {c.passed ? '✓' : '✗'} {c.criterion}
                {c.evidence ? ` — ${c.evidence}` : ''}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-sm text-muted">
            Mastery now {(result.mastery * 100).toFixed(0)}% · next review{' '}
            {new Date(result.review.due as string).toLocaleString()}
          </p>
          <div className="flex gap-2 flex-wrap mt-3">
            <Button variant="primary" onClick={onFinishBlock} disabled={transitionPending}>
              {transitionPending ? 'Opening next activity…' : 'Continue the plan'}
            </Button>
            <Button onClick={onBack} disabled={transitionPending}>
              Revisit the explanation
            </Button>
            <Button variant="ghost" onClick={nextItem} disabled={transitionPending}>
              Try another question (optional)
            </Button>
          </div>
        </Card>
      )}
    </>
  )
}

/** A code exercise exists for some skills (P8). Collapsed by default: one task at a time. */
function OptionalExercise({
  sessionId,
  skillId,
  mastery,
}: {
  sessionId: string
  skillId: string
  mastery: number
}) {
  const exercise = useExercise(skillId)
  if (!exercise.data) return null
  return (
    <details className="mt-2">
      <summary className="cursor-pointer text-sm font-medium">
        Code exercise (optional{mastery < 0.6 ? ' — best after the worked example' : ''}):{' '}
        {exercise.data.title}
      </summary>
      <div className="mt-2">
        <CodeExercise sessionId={sessionId} skillId={skillId} />
      </div>
    </details>
  )
}
