import { SavedLessonReading } from '../features/tutor/SavedLessonReading'
import { LessonFocusContext } from '../features/session/focusContext'
import { LessonContextPanel } from '../features/session/LessonContextPanel'
import { SessionContext } from '../features/session/SessionContext'
import { QuestionPractice } from '../features/questions/QuestionPractice'
import { TransitionWaitNotice } from '../features/session/TransitionWaitNotice'
import { useAssessmentRevision } from '../features/assess/useAssessmentRevision'
import { useCheckedQuestion } from '../features/assess/useCheckedQuestion'
import { RememberContext } from '../features/recent/RememberContext'
import { AlongsideMode } from '../features/session/AlongsideMode'
import { AssessmentRecovery } from '../features/assess/AssessmentRecovery'
import { AssessmentEvidence } from '../features/assess/AssessmentEvidence'
import { AssessmentDiscussion } from '../features/assess/AssessmentDiscussion'
import { AssessmentSaveStatus } from '../features/programs/AssessmentSaveStatus'
import { AnswerSaveStatus } from '../features/programs/AnswerSaveStatus'
import { RepresentationSources } from '../features/representations/RepresentationSources'
import { RequestRecoveryControls } from '../features/playground/RequestRecoveryControls'
import { useLessonDraft } from '../features/tutor/useLessonDraft'
import { LessonReader, SavedLessonNotes } from '../features/tutor/LessonReader'
import { useStopSession } from '../features/session/useStopSession'
import { SessionControls } from '../features/session/SessionControls'
import { ReadAloud } from '../features/voice/ReadAloud'
import { readDraft, writeDraft, clearDraft, draftStorageFailed } from '../features/assess/draft'
import { QuestionHelp } from '../features/assess/QuestionHelp'
import { OptionalConfidence } from '../components/OptionalConfidence'
import { QuestionFeedback } from '../features/areas/QuestionFeedback'
import { useContext, useCallback, useLayoutEffect, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Markdown } from '../components/Markdown'
import { Button } from '../components/ui/button'
import { Disclosure } from '../components/ui/disclosure'
import { Card, CardTitle } from '../components/ui/card'
import { Choice } from '../components/ui/choice'
import { Textarea } from '../components/ui/textarea'
import { useAttempt, useNextItem } from '../features/assess/api'
import { ChallengePanel } from '../features/challenge/ChallengePanel'
import { PlanStrip } from '../features/plan/PlanStrip'
import { BLOCK_LABELS, type Block } from '../features/plan/api'
import { skipNote, startLabel } from '../features/plan/labels'
import { useKinds, usePrefer, useRender, useSavedReading, type RenderOut } from '../features/representations/api'
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
import { TutorResponseStatus } from '../features/tutor/TutorResponseStatus'
import { useTutorStream } from '../features/tutor/useTutorStream'
import { TutorSources } from '../features/tutor/TutorSources'
import { withheldCount } from '../features/tutor/sourceFlags'
import { useReport } from '../features/curriculum/api'
import { apiFetch, type AssessmentView, type AttemptResult, type SessionOut } from '../lib/api'
import { SOFT_TIMER_MIN, useMode } from '../stores/mode'

type Phase = 'teach' | 'assess' | 'challenge' | 'practice'

export function Session() {
  const focus = useContext(LessonFocusContext)
  const { key: locationKey } = useLocation()
  // Pause takes effect before the route commits; block-cache updates may re-key the body meanwhile.
  const navigationOwner = useRef({ key: locationKey, paused: false })
  useLayoutEffect(() => {
    navigationOwner.current = { key: locationKey, paused: false }
  }, [locationKey])
  const canNavigate = useCallback(() =>
    navigationOwner.current.key === locationKey && !navigationOwner.current.paused, [locationKey])
  const { sessionId } = useMode()
  const nav = useNavigate()
  const session = useSession(sessionId)
  if (!sessionId) {
    return (
      <Card>
        <CardTitle as="h1">Learning session</CardTitle>
        <p>No session running.</p>
        <Button variant="primary" onClick={() => nav('/')}>
          Go to Home
        </Button>
      </Card>
    )
  }
  if (!session.data)
    return (
      <Card>
        <CardTitle as="h1">Learning session</CardTitle>
        {session.isError ? (
          <>
            <p role="alert">Could not load this session. {session.error.message}</p>
            <Button disabled={session.isFetching} onClick={() => void session.refetch()}>
              {session.isFetching ? 'Retrying…' : 'Retry loading session'}
            </Button>
          </>
        ) : (
          <p role="status">Loading session…</p>
        )}
        <Button onClick={() => nav('/')}>Go to Home</Button>
      </Card>
    )
  // keyed by the server's block id: a new block (or a resumed session) starts with fresh UI state
  const st = session.data.state
  return (
    <div className="grid grid-cols-1 gap-4" data-capture-label={session.data.active_skill?.title} data-capture-query={st.block_status === "running" && st.skill_id && st.block_started_at && session.data.active_skill?.id === st.skill_id ? new URLSearchParams({ capture_session: sessionId, capture_skill: st.skill_id, capture_block: String(st.block_index), capture_started: st.block_started_at }).toString() : ""}>
      {!session.isError && typeof st.block_index === 'number' && st.block_status === 'running' && st.skill_id && st.block_started_at && session.data.active_skill?.id === st.skill_id && <RememberContext context={{ version: 1, kind: 'lesson', session_id: sessionId, skill_id: st.skill_id, block_index: st.block_index, block_started_at: st.block_started_at, label: session.data.active_skill.title.slice(0, 200) }} />}
      {session.isError && (
        <Card>
          <p role="status">Could not refresh this session. Your current work stays on this page.</p>
          <Button disabled={session.isFetching} onClick={() => void session.refetch()}>
            {session.isFetching ? 'Retrying…' : 'Retry loading session'}
          </Button>
        </Card>
      )}
      <SessionControls compact sessionId={sessionId} skillId={st.skill_id} onPause={() => { navigationOwner.current.paused = true }}>
        <SessionContext data={session.data} compact />
      </SessionControls>
      <div className="lesson-learning-grid">
      <LessonContextPanel data={session.data} />
      <div className="lesson-current-content min-w-0">
      <SessionBody
        canNavigate={canNavigate}
        key={`${session.data.id}:${st?.block_id ?? 'none'}`} // a re-plan must not wipe the screen
        sessionId={sessionId}
        data={session.data}
      />
      </div>
      </div>
      <div data-focus-secondary><AlongsideMode sessionId={sessionId} active={!focus?.active} /></div>
      {st.skill_id && <Disclosure data-focus-secondary label="Try a coding experiment">
        <p className="text-sm text-muted my-2">Open a separate Python workspace for this lesson. Code and chat stay separate from your assessed answers; no code runs automatically.</p>
        <Link className="underline" to={`/playground?lesson_session=${encodeURIComponent(sessionId)}&lesson_skill=${encodeURIComponent(st.skill_id)}`}>Open lesson experiment</Link>
      </Disclosure>}
    </div>
  )
}

function StartCard({ sessionId, data, canNavigate }: { sessionId: string; data: SessionOut; canNavigate: () => boolean }) {
  const nav = useNavigate()
  const active = useRef(false)
  useEffect(() => {
    active.current = true
    return () => { active.current = false }
  }, [sessionId])
  const transition = useBlockTransition(sessionId)
  const plan = (data.plan ?? []) as Block[]
  const reviewIx = firstIndex(plan, (t) => REVIEW_BLOCK_TYPES.includes(t))
  const learnIx = firstIndex(plan, (t) => !REVIEW_BLOCK_TYPES.includes(t))
  const [note, setNote] = useState<string | null>(null)
  async function beginChecked(index: number) {
    if (transition.pending) return
    const state = await transition.start(index)
    if (!active.current || !canNavigate()) return
    if (!state.allowed) {
      setNote(state.message)
      return
    }
    nav(routeForPhase(state))
  }
  async function continuePlan() {
    if (transition.pending || !data.state) return
    const state = await transition.next({ from_index: data.state.block_index ?? null, reason: 'finished' })
    if (!active.current || !canNavigate()) return
    if (!state.allowed) {
      setNote(state.message)
      return
    }
    nav(state.plan_complete ? '/recap' : routeForPhase(state))
  }
  if (data.state?.plan_complete)
    return (
      <Card>
        <CardTitle as="h1">Plan complete</CardTitle>
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
        <CardTitle as="h1">Continue the plan?</CardTitle>
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
      <CardTitle as="h1">Choose where to begin</CardTitle>
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
      <TransitionWaitNotice visible={transition.waitingLong} />
      {transition.error && (
        <p role="alert" className="text-warn mt-2">
          {transition.error.message} — We could not confirm the latest session state. Use Pause and return Home, then Continue to load the current activity.
        </p>
      )}
    </Card>
  )
}

function SessionBody({ sessionId, data, canNavigate }: { sessionId: string; data: SessionOut; canNavigate: () => boolean }) {
  const active = useRef(false)
  useEffect(() => {
    active.current = true
    return () => { active.current = false }
  }, [sessionId])
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
  const [assessmentEntered, setAssessmentEntered] = useState(phase === 'assess')
  const [hintCount, setHintCount] = useState(() => Math.max(0, Number(data.checkpoint?.hint_level) || 0))
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
    if (canNavigate() && blockIndex != null && (serverPhase === 'review' || serverPhase === 'recap')) nav(routeForPhase(st))
  }, [blockIndex, serverPhase, st, nav, canNavigate])

  if (blockIndex == null || !currentBlock) return <StartCard sessionId={sessionId} data={data} canNavigate={canNavigate} />

  const timerMinutes = currentBlock.planned_min ?? SOFT_TIMER_MIN[mode]

  function changePhase(p: Phase) {
    if (p === 'assess') setAssessmentEntered(true)
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
      /* A lost response may follow a committed change; the recovery notice is rendered. */
    }
  }

  async function doFinish(reason: 'finished' | 'save_and_stop' | 'switch_early' | 'skipped') {
    if (blockIndex == null) return
    if (reason === 'save_and_stop') {
      await stopSession.mutateAsync()
      return
    }
    const res = await transition.next({ from_index: blockIndex, reason, grasp_passed: graspPassed })
    if (!active.current || !canNavigate()) return
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
    <div className="grid grid-cols-1 gap-4">
      <div data-focus-secondary><AdaptationCards origin="planner" /></div>
      {stopSession.error && <p role="alert">{stopSession.error.message}</p>}
      <Card hidden={phase === 'teach' && !data.experiment && !blockNote && !transition.waitingLong && !transition.error}>
        {phase !== 'teach' && <CardTitle as={phase === 'practice' ? 'h1' : 'h2'} className="mb-2">
          {phase === 'practice'
            ? `${currentBlock.domain === 'language' ? 'Language' : currentBlock.domain === 'guitar' ? 'Guitar' : 'Movement'} block`
            : phase === 'assess' ? 'Check yourself' : 'Challenge'}
        </CardTitle>}
        {phase !== 'teach' && <p className="text-sm mt-2">
          {phase === 'assess'
            ? 'Read the context, use a hint if helpful, and try an answer when ready.'
            : phase === 'challenge'
              ? 'Apply the idea to a challenge, then continue the plan.'
              : 'Follow the activity below. When you finish or skip it, the next activity opens.'}
        </p>}
        {data.experiment && (
          <p className="text-sm mt-2" role="status">
            Experiment "{String(data.experiment.name)}":{' '}
            {data.experiment.arm
              ? `this session runs the "${String(data.experiment.arm)}" arm`
              : 'each skill keeps the arm it was assigned to (shown per turn)'}
            .
          </p>
        )}

        {skill && phase === 'assess' && (
          <div className="mt-2 text-sm">
            <ReadAloud
              key={skill.id}
              text={skill.description || skill.title}
              label="Listen to learning goal"
            />
          </div>
        )}
        {blockNote && (
          <p role="status" className="text-sm text-warn mt-2">
            {blockNote}
          </p>
        )}
        <TransitionWaitNotice visible={transition.waitingLong} />
        {transition.error && (
          <p role="alert" className="text-sm text-warn mt-2">
            {transition.error.message} — We could not confirm the latest session state. Use Pause and return Home, then Continue to load the current activity.
          </p>
        )}
      </Card>
      {(phase === 'teach' || phase === 'assess') && (
        <div hidden={phase !== 'teach'}>
          <TeachPanel
            key={JSON.stringify([sessionId, blockIndex, st?.block_started_at ?? null, activeSkillId])}
            recoveryScope={JSON.stringify([
              sessionId,
              blockIndex,
              st?.block_started_at ?? null,
              activeSkillId,
            ])}
            active={phase === 'teach'}
            hasQuestion={assessmentEntered}
            sessionId={sessionId}
            skillId={activeSkillId}
            learningGoal={skill ? skill.description || skill.title : undefined}
            onCheck={() => changePhase('assess')}
            onHintLevel={setHintCount}
            onSwitchEarly={() => void finishBlock('switch_early')}
          />
        </div>
      )}
      {assessmentEntered && (phase === 'teach' || phase === 'assess') && (
        <div hidden={phase !== 'assess'}>
          <AssessPanel
            key={JSON.stringify([sessionId, blockIndex, st?.block_started_at ?? null, activeSkillId])}
            recoveryScope={JSON.stringify([sessionId, blockIndex, st?.block_started_at ?? null, activeSkillId])}
            active={phase === 'assess'}
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
        </div>
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
          transitionPending={transition.pending}
          sessionId={sessionId}
          domain={currentBlock.domain === 'guitar' ? 'guitar' : 'movement'}
          plannedMin={currentBlock.planned_min}
          onDone={() => void finishBlock('finished')}
          onSkip={() => void finishBlock('skipped')}
        />
      )}
        <Disclosure data-focus-secondary className="mt-3" label="Session plan and energy settings">
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
        </Disclosure>
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
  recoveryScope,
  active,
  hasQuestion,
  sessionId,
  skillId,
  learningGoal,
  onCheck,
  onHintLevel,
  onSwitchEarly,
}: {
  recoveryScope: string
  hasQuestion: boolean
  sessionId: string
  skillId: string | null
  learningGoal?: string
  onCheck: () => void
  onHintLevel: (n: number) => void
  onSwitchEarly: () => void
  active: boolean
}) {
  const { input, setInput, error: draftError } = useLessonDraft(recoveryScope)
  const {
    text,
    meta,
    done,
    error,
    busy,
    run: runReply,
    stop,
    retry: retryReply,
    status,
    previous,
    startedAt,
    recovery,
    storageError,
    restored,
  } = useTutorStream(60_000, recoveryScope)
  useEffect(() => {
    if (!active) stop()
  }, [active, stop])
  const savedReading = useSavedReading(skillId)
  const kinds = useKinds(skillId)
  const render = useRender()
  const prefer = usePrefer()
  const preferenceLock = useRef(false)
  const matchesPreference = (a: string, b: string) => prefer.variables &&
    ((prefer.variables.chosenId === a && prefer.variables.rejectedId === b) ||
      (prefer.variables.chosenId === b && prefer.variables.rejectedId === a))
  function savePreference(chosenId: string, rejectedId: string) {
    if (!skillId || preferenceLock.current || (prefer.isSuccess && matchesPreference(chosenId, rejectedId))) return
    preferenceLock.current = true
    prefer.mutate({ skillId, sessionId, chosenId, rejectedId }, {
      onSettled: () => { preferenceLock.current = false },
    })
  }
  const [alt, setAlt] = useState<RenderOut | null>(null)
  const [prevAlt, setPrevAlt] = useState<RenderOut | null>(null)
  const representationLock = useRef(false)
  const [waysOpen, setWaysOpen] = useState(false)
  const [viewingAlt, setViewingAlt] = useState(false)
  const viewIntent = useRef(0)
  const run: typeof runReply = request => {
    viewIntent.current += 1
    setViewingAlt(false)
    return runReply(request)
  }
  const retry: typeof retryReply = () => {
    viewIntent.current += 1
    setViewingAlt(false)
    return retryReply()
  }
  const reportTurn = useReport()
  const prefs = usePreferences()
  const voiceOn = (prefs.data?.values as Record<string, unknown> | undefined)?.['voice.enabled'] === true
  const [talking, setTalking] = useState(false)
  const base = { session_id: sessionId, skill_id: skillId }
  useEffect(() => {
    if (meta && !meta.replayed && meta.session_id === sessionId && meta.skill_id === skillId)
      onHintLevel(meta.hint_level)
  }, [meta, onHintLevel, sessionId, skillId])
  // "Reported" belongs to one turn: a new answer starts clean.
  const reportedThisTurn =
    reportTurn.isSuccess && done != null && reportTurn.variables?.turn_id === done.turn_id

  async function showDifferently(kind: string) {
    if (!skillId || representationLock.current || busy) return
    representationLock.current = true
    const intent = ++viewIntent.current
    try {
      const out = await render.mutateAsync({ skillId, kind, sessionId })
      setPrevAlt(alt)
      setAlt(out)
      if (viewIntent.current === intent) setViewingAlt(true)
    } catch {
      // The mutation exposes the error beside the controls; keep current content.
    } finally {
      representationLock.current = false
    }
  }

  const helpActions = (
    <div className="flex gap-2 flex-wrap mt-2">
      <Button
        disabled={busy || input.length > 4000}
        onClick={() => void run({ ...base, text: input.trim() || 'I am stuck.', action: 'hint' })}
      >
        Hint
      </Button>
      <Button
        disabled={busy || input.length > 4000}
        onClick={() => void run({ ...base, text: input.trim() || 'Recap this skill.', action: 'summarize' })}
      >
        Summary of this skill
      </Button>
    </div>
  )
  return (
    <>
      <SavedLessonReading reading={savedReading} active={active} hasReply={!!text || !!alt || busy} />
      {busy && (
        <Card role="region" aria-label="Explanation in progress">
          <TutorResponseStatus status={status} startedAt={startedAt} />
          <Button variant="ghost" onClick={stop}>Stop explanation</Button>
        </Card>
      )}
      {alt && (
        <fieldset className="flex flex-wrap gap-3 border-0 p-0">
          <legend className="text-sm font-medium mb-2">Explanation to read</legend>
          {[
            { alternate: false, label: 'Original explanation' },
            { alternate: true, label: String((kinds.data?.kinds ?? []).find(k => k.kind === alt.kind)?.label ?? alt.kind.replaceAll('_', ' ')) },
          ].map(option => (
            <label key={String(option.alternate)} className="flex items-center gap-2 min-h-control-target text-sm">
              <input type="radio" name="lesson-explanation-view" checked={viewingAlt === option.alternate}
                onChange={() => { viewIntent.current += 1; setViewingAlt(option.alternate) }} />
              {option.label}
            </label>
          ))}
        </fieldset>
      )}
      {(text || busy || error || status === 'stopped') && (
        <Card aria-busy={busy} hidden={viewingAlt}>
          {meta && (
            <p className="text-xs text-muted mb-2">
              {meta.action}
              {meta.action === 'hint' ? ` · level ${meta.hint_level}` : ''} · {meta.questioning_style}
              {meta.experiment_arm ? ' · set by the experiment arm' : ''}
              {meta.arm_not_applied ? ' (representation kept: not yet at the mastery this arm needs)' : ''}
            </p>
          )}
          {error && (
            <p role="alert" className="text-warn">
              {error}
            </p>
          )}
          {status === 'complete' && done ? (
            <LessonReader
              key={done.turn_id}
              identity={`${sessionId}:${done.turn_id}`}
              text={text}
              sources={done.sources}
              active={active && !viewingAlt}
            />
          ) : (
            <Markdown text={text || (busy ? '…' : '')} />
          )}
          {active && status === 'complete' && done && (
            <Disclosure className="mt-4" label="Think deeper about this explanation">
              <p className="text-sm mt-2">
                Choose a direction to add to your question below. Your existing draft is kept. Edit it, then
                send it. This is optional practice, not a graded assessment.
              </p>
              <div className="flex flex-wrap gap-2 mt-3">
                {[
                  [
                    'Why does it work?',
                    'Choose one specific claim from this explanation. Explain the mechanism and the assumptions it relies on, using a small worked example.',
                  ],
                  [
                    'Find a counterexample',
                    'Choose one specific claim from this explanation and show a concrete case where it would fail or need qualification. Explain the limiting assumption.',
                  ],
                  [
                    'Try a changed situation',
                    'Create one small transfer exercise in a changed scenario based on this explanation. Give the necessary facts and one concrete next step to try without giving its solution.',
                  ],
                ].map(([label, request]) => (
                  <Button
                    key={label}
                    onClick={() => {
                      setInput(
                        (draft) =>
                          `${draft.trim() ? `${draft}\n\n` : ''}${request}\n\nExplanation to discuss (quoted material):\n${text.slice(0, 2800)}`,
                      )
                      document.getElementById('ask')?.focus()
                    }}
                  >
                    {label}
                  </Button>
                ))}
              </div>
              {text.length > 2800 && (
                <p className="text-sm text-muted">
                  The prepared request includes the first 2,800 characters. Replace it with the passage you
                  want to discuss if it is later in the explanation.
                </p>
              )}
            </Disclosure>
          )}
          {status === 'stopped' && <p role="status">Explanation stopped. Received text is kept.</p>}
          {status === 'complete' && (
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
            <Disclosure className="text-xs text-muted mt-1" label="About this answer">
              Model {done.registry_id} ({done.route ?? 'primary'})
              {done.usage_source === 'estimated' ? ' · token usage estimated' : ''}
            </Disclosure>
          )}
          {done && <TutorSources turn={done} />}
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
        <Card hidden={!viewingAlt} role="region" aria-label="Alternative explanation">
          <p className="text-xs text-muted mb-2">
            {alt.kind.replace('_', ' ')} · same learning object{alt.cached ? ' · from cache' : ''}
          </p>
          <Markdown text={alt.content} />
          <AnswerSaveStatus
            key={`save-${alt.representation_id}`}
            answerId={alt.answer_id}
            error={alt.save_error}
            receipt={alt.save_receipt}
            text={alt.content}
          />
          <RepresentationSources key={`sources-${alt.representation_id}`} value={alt} />
          {active && viewingAlt && <ReadAloud key={alt.representation_id} text={alt.content} />}
          {prevAlt && prevAlt.representation_id !== alt.representation_id && (
            <div className="mt-3">
              <p className="text-sm font-medium mb-1">Which explanation worked better?</p>
              <p className="text-sm text-muted">Optional feedback, not a learning score.</p>
              <div className="flex gap-2 flex-wrap">
                <Button size="sm" aria-disabled={prefer.isPending || (prefer.isSuccess && !!matchesPreference(alt.representation_id, prevAlt.representation_id))} aria-busy={prefer.isPending}
                  onClick={() => savePreference(alt.representation_id, prevAlt.representation_id)}>
                  This one ({alt.kind.replace('_', ' ')})
                </Button>
                <Button size="sm" aria-disabled={prefer.isPending || (prefer.isSuccess && !!matchesPreference(alt.representation_id, prevAlt.representation_id))} aria-busy={prefer.isPending}
                  onClick={() => savePreference(prevAlt.representation_id, alt.representation_id)}>
                  The previous one ({prevAlt.kind.replace('_', ' ')})
                </Button>
              </div>
              {matchesPreference(alt.representation_id, prevAlt.representation_id) && <>
                  {prefer.isPending && <p role="status">Saving your explanation preference…</p>}
                  {prefer.isError && <p role="alert">{prefer.error.message}</p>}
                  {prefer.isSuccess && <p role="status">Preference saved.</p>}
                </>}
            </div>
          )}
        </Card>
      )}
      {!busy && (done || alt || hasQuestion || savedReading.data) && (
        <Card>
          <p className="text-sm font-medium mb-2">
            {hasQuestion ? 'Your current question and any checked feedback are kept.' : 'Next: try one question about this idea.'}
          </p>
          <div className="flex gap-2 flex-wrap mb-3">
            <Button
              aria-expanded={waysOpen}
              aria-controls="lesson-explanation-choices"
              onClick={() => setWaysOpen(value => !value)}
            >
              Explain differently
            </Button>
            <Button
              disabled={render.isPending || !kinds.data?.kinds?.some(k => k.kind === 'worked_example' && k.allowed)}
              onClick={() => void showDifferently('worked_example')}
            >
              Give me an example
            </Button>
            <Button variant="primary" onClick={onCheck}>
              {hasQuestion ? 'Return to your question' : 'Let me try'}
            </Button>
          </div>
          {render.isPending && <p role="status">Preparing another explanation… Your current content is kept.</p>}
          {render.isError && <p role="alert">{(render.error as Error).message}</p>}
          {kinds.isPending && <p role="status">Loading explanation choices…</p>}
          {kinds.isSuccess && !kinds.data.kinds?.some(k => k.kind === 'worked_example' && k.allowed) && (
            <p className="text-sm text-muted">A worked example is not available for this concept.</p>
          )}
          {kinds.isError && <p role="alert">Explanation choices are unavailable. <Button onClick={() => void kinds.refetch()}>Retry choices</Button></p>}
          <Disclosure
            id="lesson-explanation-choices"
            label="More ways to explain"
            open={waysOpen}
            onToggle={event => setWaysOpen(event.currentTarget.open)}
          >
            {helpActions}
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
            <Button className="mt-3" variant="ghost" onClick={onSwitchEarly}>
              Request another activity (a check may be required)
            </Button>
          </Disclosure>
          <Disclosure className="mt-3" label="Full solution (explicit request, logged)">
            <Button
              className="mt-2"
              onClick={() => void run({ ...base, text: 'show the full solution', action: 'full_solution' })}
            >
              Show the full solution
            </Button>
          </Disclosure>
        </Card>
      )}
      <Card>
        <CardTitle>{text || alt || savedReading.data ? 'Ask the tutor' : 'Your explanation'}</CardTitle>
        <p className="text-sm mb-2">Start with the idea and a worked example. No question is required.</p>
        <div className="flex gap-2 flex-wrap mb-2">
          <Button
            variant={done || alt || savedReading.data || input.trim() ? 'secondary' : 'primary'}
            disabled={busy}
            onClick={() => void run({ ...base, text: 'Explain the next idea for this skill in three short sections with Markdown headings: The idea, A worked example, and Try one step. Give enough context to attempt that step. Keep code blocks complete. Do not require a confidence rating.', action: 'explain' })}
          >
            {busy ? 'Preparing explanation…' : text ? 'Explain again' : savedReading.data ? 'Ask for another explanation' : 'Start explanation'}
          </Button>
          {!(done || alt || hasQuestion) && <Disclosure label="More ways to learn">{helpActions}</Disclosure>}
        </div>
        {skillId && (
          <div className="mb-3">
            <Button asChild variant="ghost">
              <Link to={`/answers?skill_id=${encodeURIComponent(skillId)}&surface=tutor`}>Read saved explanations</Link>
            </Button>
            <p className="text-sm text-muted">Past replies for this concept. Opens without generating; sources may have changed.</p>
          </div>
        )}
        {input.trim() && <p className="text-sm mb-2">Starting an explanation keeps your draft below without sending it. Use Send lesson question to ask it.</p>}
        <label htmlFor="ask" className="text-sm font-medium">
          Ask about this lesson (optional)
        </label>
        <Textarea
          id="ask"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="What would you like explained about this lesson?"
          aria-describedby={input.length > 4000 ? 'lesson-question-limit' : undefined}
        />
        {input.length > 4000 && (
          <p id="lesson-question-limit" role="alert">
            Your draft is preserved. Shorten it to 4,000 characters before sending ({input.length} currently).
          </p>
        )}
        <div className="flex gap-2 flex-wrap mt-2">
          <Button
            variant={!done && !alt && input.trim() ? 'primary' : 'secondary'}
            disabled={busy || !input.trim() || input.length > 4000}
            onClick={() => void run({ ...base, text: input.trim(), action: 'explain' })}
          >
            Send lesson question
          </Button>
          {voiceOn && !talking && (
            <Button variant="ghost" onClick={() => setTalking(true)}>
              Talk instead
            </Button>
          )}
        </div>
        {!text && !savedReading.data && !savedReading.isFetching && !busy && !error && status !== 'stopped' && (
          <p className="mt-2">No explanation has been prepared yet.</p>
        )}
        <p className="text-sm text-muted mt-2">
          Read at your own pace or choose Listen when the explanation is ready. Audio never starts automatically.
        </p>
        {active && learningGoal && <ReadAloud key={skillId} text={learningGoal} label="Listen to learning goal" />}
        {!busy && <TutorResponseStatus status={status} startedAt={startedAt} />}
        {active && (
          <RequestRecoveryControls
            recovery={recovery}
            busy={busy}
            retry={() => void retry()}
            originalContext="lesson and question"
          />
        )}
        {draftError && <p role="alert">{draftError}</p>}
        {storageError && <p role="alert">{storageError}</p>}
        {restored && (
          <p role="status">
            {done
              ? 'Restored the completed reply and its source details from this tab. No new generation or checks.'
              : 'Restored text from this tab. No new generation or checks; open saved answers for source details.'}
          </p>
        )}
        {meta?.replayed && (
          <p role="status">Recovered the original reply. No new generation or learning progress.</p>
        )}
      </Card>
      {active && voiceOn && talking && (
        <VoicePanel sessionId={sessionId} skillId={skillId} onClose={() => setTalking(false)} />
      )}
      <div data-focus-secondary><SavedLessonNotes sessionId={sessionId} /></div>
      {previous && (
        <Disclosure data-focus-secondary label={`Previous answer · ${previous.status}`}>
          <Markdown text={previous.text} />
          {previous.done?.sources.map((source, index) => (
            <p className="text-sm" key={index}>
              {source.citation}
              {!source.cited && ' (not cited)'}
              {(source.flagged ?? []).length > 0 && (
                <span className="text-warn"> (flagged: {(source.flagged ?? []).join(', ')})</span>
              )}
            </p>
          ))}
          {previous.done && previous.done.sources.length === 0 && (
            <p className="text-sm">No course source for this previous answer.</p>
          )}
          {previous.done && withheldCount(previous.done.dropped) > 0 && (
            <p className="text-sm">Some sources were withheld as flagged or untrusted.</p>
          )}
          {!previous.done && (
            <p className="text-sm">This response did not finish; source references may be incomplete.</p>
          )}
        </Disclosure>
      )}

    </>
  )
}

function AssessPanel({
  recoveryScope,
  active,
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
  active: boolean
  recoveryScope: string
}) {
  const checked = useCheckedQuestion(recoveryScope, sessionId, skillId, active)
  const [round, setRound] = useState(0)
  const next = useNextItem(sessionId, skillId, round, active && !checked.saved && !checked.error)
  const [confidence, setConfidence] = useState<number | null>(null)
  const [answer, setAnswer] = useState('')
  const [localResult, setResult] = useState<AttemptResult | null>(null)
  const savedResult = localResult ?? checked.result.data ?? null
  const revision = useAssessmentRevision(recoveryScope, sessionId, savedResult?.attempt_id ?? null, active)
  const result = revision.editing ? null : savedResult
  const [startedAt, setStartedAt] = useState(() => Date.now())
  const [refreshedItem, setRefreshedItem] = useState<AssessmentView | null>(null)
  const [frozenItem, setFrozenItem] = useState<{ round: number; item: AssessmentView } | null>(null)
  const candidate = checked.saved?.item ?? next.data?.item
  if (candidate && frozenItem?.round !== round) setFrozenItem({ round, item: candidate })
  const item = revision.data?.item ?? refreshedItem ?? (frozenItem?.round === round ? frozenItem.item : candidate)
  const [previousChoice, setPreviousChoice] = useState('')
  const [practiceChanged, setPracticeChanged] = useState<string | null>(null)
  const displayedItem = useRef(item)
  useLayoutEffect(() => {
    displayedItem.current = item
  }, [item])
  const attempt = useAttempt(sessionId, (pending, outcome) => {
    if (displayedItem.current) checked.remember(pending, outcome, displayedItem.current)
  })
  const restoredAttempt = useRef<string | null>(null)
  useEffect(() => {
    const restored = checked.result.data
    if (restored && restoredAttempt.current !== restored.attempt_id) {
      restoredAttempt.current = restored.attempt_id
      onGraded(restored) // local continuation readiness only; no submission or learning write
    }
  }, [checked.result.data, onGraded])
  const answerKey = `audhs-answer:${sessionId}:${item?.id ?? ''}`
  const savedAnswer = item ? readDraft(answerKey).answer : ''
  const currentAnswer = revision.editing ? revision.answer : answer || savedAnswer
  const answerControls = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!revision.data || !active) return
    answerControls.current?.querySelector<HTMLElement>('textarea, button')?.focus()
  }, [revision.data, active])

  async function submit() {
    if (!item || (revision.editing && !revision.data)) return
    try {
      const res = await attempt.mutateAsync({
        ...(revision.editing ? { revision_of_attempt_id: revision.data!.root_attempt_id } : {}),
        session_id: sessionId,
        assessment_id: item.id,
        content_version: item.content_version,
        answer: currentAnswer,
        questionLabel: item.question,
        answerLabel: item.options?.[Number(currentAnswer)] ?? currentAnswer,
        confidence_pre: confidence,
        latency_ms: Date.now() - startedAt,
        hint_count: hintCount + readDraft(answerKey).hints,
      })
      if (
        displayedItem.current?.id !== item.id ||
        displayedItem.current?.content_version !== item.content_version
      )
        return
      clearDraft(answerKey)
      revision.clear(true)
      setResult(res)
      onGraded(res)
    } catch {
      // The mutation alert offers retry; preserve the answer and confidence.
    }
  }

  function nextItem() {
    if (!revision.clear() || !checked.clear()) return
    setPracticeChanged(null)
    setRefreshedItem(null)
    setPreviousChoice('')
    setStartedAt(Date.now())
    setResult(null)
    setAnswer('')
    setConfidence(null)
    setRound((r) => r + 1)
  }

  const recoveryPanel = active && (
    <AssessmentRecovery
      recovery={attempt.recovery}
      onRefresh={async (signal) => {
        if (attempt.recovery.pending?.body.assessment_id !== item?.id)
          throw new Error(
            'This saved answer belongs to another question. Return to that activity; the original answer is kept here.',
          )
        if (!item) throw new Error('The original question is unavailable.')
        const latest = await apiFetch<AssessmentView>(
          `/api/assess/items/${encodeURIComponent(item.id)}?session_id=${encodeURIComponent(sessionId)}`,
          { signal },
        )
        if (signal.aborted) throw new Error('Refresh cancelled.')
        if (latest.id !== item.id) throw new Error('The refreshed question does not match.')
        if (item.options) {
          setPreviousChoice(item.options[Number(currentAnswer)] ?? currentAnswer)
          setAnswer('')
          clearDraft(answerKey)
        }
        setRefreshedItem(latest)
        setResult(null)
      }}
      onUse={(saved, body) => {
        if (
          saved.assessment_id !== item?.id ||
          body.answer !== currentAnswer ||
          !body.content_version ||
          body.content_version !== item?.content_version
        )
          return false
        if (attempt.recovery.pending && item) checked.remember(attempt.recovery.pending, saved, item)
        revision.clear(true)
        setResult(saved)
        onGraded(saved)
        clearDraft(answerKey)
        return true
      }}
    />
  )
  if (!savedResult && (checked.saved || checked.error))
    return (
      <Card>
        <p role={checked.error || checked.result.isError ? 'alert' : 'status'}>
          {checked.error || (checked.result.error as Error | null)?.message || 'Restoring your checked question and feedback…'}
        </p>
        <p>No answer is submitted or graded by restoring feedback.</p>
        <div className="flex flex-wrap gap-2 mt-3">
          {checked.saved && <Button disabled={checked.result.isFetching} onClick={() => void checked.result.refetch()}>Retry feedback lookup</Button>}
          <Button onClick={onBack}>Back to explanation</Button>
          <Button variant="ghost" onClick={nextItem}>Choose another question</Button>
        </div>
        {recoveryPanel}
      </Card>
    )
  if (next.isLoading)
    return (
      <>
        {recoveryPanel}
        <Card>Loading item…</Card>
      </>
    )
  if (!item)
    return (
      <Card>
        {recoveryPanel}
        <p>No available questions for this skill.</p>
        <p className="mt-2"><Link to="/preferences#excluded-questions">Manage excluded questions</Link></p>
        <Button onClick={onBack}>Back to explanation</Button>
      </Card>
    )

  return (
    <>
      {recoveryPanel}
      {checked.error && <p role="alert">{checked.error}</p>}
      {checked.saved && result && <p role="status">Restored your checked feedback. No new grading or learning progress. Scores and review dates describe that attempt.</p>}
      <Card>
        <p className="text-sm text-muted mb-2">
          {result
            ? 'Question you answered'
            : item.kind === 'mcq'
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
            active={active}
            key={`help:${item.id}`}
            sessionId={sessionId}
            skillId={skillId}
            question={item.question}
            onHint={() => writeDraft(answerKey, { hints: readDraft(answerKey).hints + 1 })}
          />
        )}
        {previousChoice && (
          <p role="status">
            Previous choice: {previousChoice}. The question changed; choose an option again.
          </p>
        )}
        <QuestionFeedback key={`feedback:${item.id}`} target={{ assessment_id: item.id }} />
        <QuestionPractice assessmentId={item.id} onChanged={(id) => setPracticeChanged(id)} />
        {!result && practiceChanged === item.id && <div className="mt-3">
          <p role="status">Question choice changed. Your answer draft is kept. Choose another question to continue.</p>
          <Button onClick={nextItem}>Choose another question</Button>
        </div>}
        {revision.storageError && <p role="alert">{revision.storageError}</p>}
        {revision.editing && <section aria-label="Revise your answer" className="grid gap-2 mt-3">
          <h3 className="font-medium">Try this question again</h3>
          <p>Your previous answer and feedback are kept. This is practice; it will not add independent learning evidence or change the review schedule.</p>
          {revision.source.isFetching && <p role="status">Loading your submitted answer…</p>}
          {revision.source.isError && <p role="alert">{(revision.source.error as Error).message} <Button onClick={() => void revision.source.refetch()}>Retry loading answer</Button></p>}
          <Button onClick={() => { if (revision.clear()) setTimeout(() => document.getElementById('retry-assessment')?.focus(), 0) }} disabled={attempt.isPending || !!attempt.recovery.pending}>Cancel revision</Button>
          {savedResult && <Disclosure label="Previous feedback"><AssessmentEvidence result={savedResult} /></Disclosure>}
        </section>}
        {!result && (
          <>
            <div ref={answerControls}>
            {item.kind === 'mcq' && item.options ? (
              <Choice<string>
                label="Your answer"
                selectionTone="quiet"
                options={item.options.map((o, i) => ({ value: String(i), label: o }))}
                value={currentAnswer || null}
                onChange={(value) => {
                  if (revision.editing) revision.edit(value)
                  else { setAnswer(value); writeDraft(answerKey, { answer: value }) }
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
                    if (revision.editing) revision.edit(e.target.value)
                    else { setAnswer(e.target.value); writeDraft(answerKey, { answer: e.target.value }) }
                  }}
                />
              </>
            )}
            </div>
            {!revision.editing && draftStorageFailed(answerKey) && (
              <p role="alert" className="text-sm mt-2">
                This browser could not save your answer. It remains available while this page is open;
                copy it before refreshing or closing the tab. You can still check your answer.
              </p>
            )}
            <div className="mt-3">
              <OptionalConfidence value={confidence} onChange={setConfidence} />
            </div>
            <div className="flex gap-2 mt-3">
              <Button
                variant="primary"
                onClick={() => void submit()}
                disabled={!currentAnswer.trim() || attempt.isPending || practiceChanged === item.id || (revision.editing && !revision.data)}
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
          <AssessmentEvidence result={result} />
          <AssessmentSaveStatus
            key={result.attempt_id}
            result={result}
            onSaved={(answerId) => setResult({ ...result, answer_id: answerId, save_error: null, save_receipt: null })}
          />
          <Disclosure className="text-sm text-muted mt-2" label="Score and grading details">
            <p>
              Score {(result.score * 100).toFixed(0)}% · graded by {result.grader_level} · confidence{' '}
              {result.confidence_pre == null
                ? 'not supplied'
                : `${result.confidence_pre}/5: ${result.calibration}`}
            </p>
            <p>Mastery estimate after this attempt {(result.mastery * 100).toFixed(0)}%</p>
          </Disclosure>
          <p className="mt-2 text-sm text-muted">
            {result.review_updated === false ? 'Existing review schedule unchanged: ' : 'Review scheduled after this attempt '}{new Date(result.review.due as string).toLocaleString()}
          </p>
          <div className="flex gap-2 flex-wrap mt-3">
            <Button id="retry-assessment" variant={result.score < 0.85 ? 'primary' : 'secondary'} onClick={() => { revision.start(); setConfidence(null); setStartedAt(Date.now()) }} disabled={transitionPending || attempt.isPending}>
              Try again
            </Button>
            <Button variant={result.score >= 0.85 ? 'primary' : 'secondary'} onClick={onFinishBlock} disabled={transitionPending}>
              {transitionPending ? 'Opening next activity…' : 'Next'}
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
      {result && (
        <AssessmentDiscussion
          key={`discussion:${result.attempt_id}`}
          answerId={result.answer_id}
          sessionId={sessionId}
          active={active && !transitionPending}
        />
      )}
      {result && (
        <QuestionHelp
          key={`feedback-help:${result.attempt_id}`}
          afterAnswer
          assessmentAnswerId={result.answer_id ?? null}
          active={active && !transitionPending}
          sessionId={sessionId}
          skillId={skillId}
          question={item.question}
        />
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
  if (!exercise.data && !exercise.isError && !exercise.isFetching) return null
  return (
    <Disclosure className="mt-2" label={`Code exercise (optional${mastery < 0.6 ? ' — best after the worked example' : ''}): ${exercise.data?.title ?? (exercise.isFetching ? 'Loading exercise…' : 'Could not load exercise')}`}>
      <div className="mt-2">
        <CodeExercise sessionId={sessionId} skillId={skillId} />
      </div>
    </Disclosure>
  )
}
