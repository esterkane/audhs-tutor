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
import { useBlockEnd, useBlockStart, type Block } from '../features/plan/api'
import { useKinds, usePrefer, useRender, type RenderOut } from '../features/representations/api'
import { useCheckpoint, useSession } from '../features/session/api'
import { SoftTimer } from '../features/session/SoftTimer'
import { useTutorStream } from '../features/tutor/useTutorStream'
import type { AttemptResult, SessionOut } from '../lib/api'
import { SOFT_TIMER_MIN, useMode } from '../stores/mode'

type Phase = 'teach' | 'assess' | 'challenge'
const PHASE_FOR_BLOCK: Record<string, Phase | 'review' | 'recap' | 'skip'> = {
  movement_primer: 'skip',
  retrieval: 'review',
  new_material: 'teach',
  challenge: 'challenge',
  interleaved_review: 'review',
  domain_switch: 'skip',
  recap: 'recap',
}

type Checkpoint = { phase?: string; skill_id?: string; block_index?: number } | null | undefined

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
  // keyed by session id so a resumed session initialises its state from the server checkpoint
  return <SessionBody key={session.data.id} sessionId={sessionId} data={session.data} />
}

function SessionBody({ sessionId, data }: { sessionId: string; data: SessionOut }) {
  const { skillId, setSkill, mode } = useMode()
  const nav = useNavigate()
  const checkpoint = useCheckpoint()
  const blockStart = useBlockStart()
  const blockEnd = useBlockEnd()
  const cp = data.checkpoint as Checkpoint
  const [phase, setPhase] = useState<Phase>(() =>
    cp?.phase === 'assess' || cp?.phase === 'challenge' ? cp.phase : 'teach',
  )
  const [hintCount, setHintCount] = useState(0)
  const [blockIndex, setBlockIndex] = useState<number | null>(() =>
    typeof cp?.block_index === 'number' ? cp.block_index : null,
  )
  const [graspPassed, setGraspPassed] = useState(false)
  const [blockNote, setBlockNote] = useState<string | null>(null)
  const skill = data.next_skill
  const plan = (data.plan ?? []) as Block[]

  // Zustand is an external store: syncing it from an effect is the intended pattern.
  useEffect(() => {
    const wanted = cp?.skill_id ?? skill?.id ?? null
    if (wanted && !skillId) setSkill(wanted)
  }, [cp?.skill_id, skill, skillId, setSkill])

  const currentSkillId = skillId ?? cp?.skill_id ?? skill?.id ?? null
  const current = blockIndex ?? plan.findIndex((b) => b.type === 'new_material')
  const currentBlock = current >= 0 ? plan[current] : undefined
  const timerMinutes = currentBlock?.planned_min ?? SOFT_TIMER_MIN[mode]

  function changePhase(p: Phase) {
    setPhase(p)
    void checkpoint.mutateAsync({
      id: sessionId!,
      body: { phase: p, skill_id: currentSkillId, block_index: current >= 0 ? current : undefined },
    })
  }

  async function finishBlock(reason: 'finished' | 'save_and_stop' | 'switch_early') {
    if (current < 0 || !currentBlock) {
      nav('/recap')
      return
    }
    const res = await blockEnd.mutateAsync({
      session_id: sessionId!,
      index: current,
      switched_early: reason !== 'finished',
      reason,
      grasp_passed: graspPassed,
    })
    if (!res.allowed) {
      setBlockNote(res.message)
      changePhase('assess')
      return
    }
    setBlockNote(null)
    if (reason === 'save_and_stop' || res.next_index == null) {
      nav('/recap')
      return
    }
    // advance through the plan; skip blocks that have no screen yet
    let idx: number | null = res.next_index
    while (idx != null && idx < plan.length && PHASE_FOR_BLOCK[plan[idx].type] === 'skip')
      idx = idx + 1 < plan.length ? idx + 1 : null
    if (idx == null) {
      nav('/recap')
      return
    }
    setBlockIndex(idx)
    await blockStart.mutateAsync({ session_id: sessionId!, index: idx, switched_early: false })
    const next = PHASE_FOR_BLOCK[plan[idx].type]
    if (next === 'review') nav('/review')
    else if (next === 'recap') nav('/recap')
    else changePhase(next as Phase)
  }

  return (
    <div className="grid gap-4">
      <SoftTimer
        minutes={timerMinutes}
        onSaveStop={() => void finishBlock('save_and_stop')}
        onFinishBlock={() => void finishBlock('finished')}
      />
      <Card>
        <PlanStrip blocks={plan} current={current} />
        <CardTitle className="mt-3">
          {phase === 'teach' ? 'Learn' : phase === 'assess' ? 'Check yourself' : 'Challenge'}:{' '}
          {skill?.title ?? '…'}
        </CardTitle>
        {skill && phase === 'teach' && (
          <p className="text-sm text-muted">
            Goal: {skill.description} · mastery {(skill.mastery * 100).toFixed(0)}%
          </p>
        )}
        {blockNote && (
          <p role="status" className="text-sm text-warn mt-2">
            {blockNote}
          </p>
        )}
      </Card>
      {phase === 'teach' && (
        <TeachPanel
          sessionId={sessionId}
          skillId={currentSkillId}
          onCheck={() => changePhase('assess')}
          onHintLevel={setHintCount}
          onSwitchEarly={() => void finishBlock('switch_early')}
        />
      )}
      {phase === 'assess' && (
        <AssessPanel
          sessionId={sessionId}
          skillId={currentSkillId}
          hintCount={hintCount}
          onBack={() => changePhase('teach')}
          onGraded={(r) => {
            setHintCount(0)
            if (r.score >= 0.85) setGraspPassed(true)
          }}
          onFinishBlock={() => void finishBlock('finished')}
        />
      )}
      {phase === 'challenge' && (
        <ChallengePanel
          sessionId={sessionId}
          skillId={currentSkillId}
          onDone={() => void finishBlock('finished')}
        />
      )}
    </div>
  )
}

function TeachPanel({
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
}) {
  const [input, setInput] = useState('')
  const { text, meta, done, error, busy, run, stop } = useTutorStream()
  const kinds = useKinds(skillId)
  const render = useRender()
  const prefer = usePrefer()
  const [alt, setAlt] = useState<RenderOut | null>(null)
  const [prevAlt, setPrevAlt] = useState<RenderOut | null>(null)
  const base = { session_id: sessionId, skill_id: skillId }
  useEffect(() => {
    if (meta) onHintLevel(meta.hint_level)
  }, [meta, onHintLevel])

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
          Question for the tutor (optional). Empty + Explain = the next idea for this skill.
        </label>
        <Textarea
          id="ask"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. why divide by sqrt(d_k)?"
        />
        <div className="flex gap-2 flex-wrap mt-2">
          <Button
            variant="primary"
            disabled={busy}
            onClick={() =>
              void run({
                ...base,
                text: input.trim() || 'Explain the next idea for this skill.',
                action: 'explain',
              })
            }
          >
            Explain
          </Button>
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
          {busy && (
            <Button variant="ghost" onClick={stop}>
              Stop
            </Button>
          )}
        </div>
      </Card>
      {(text || busy || error) && (
        <Card aria-busy={busy}>
          {meta && (
            <p className="text-xs text-muted mb-2">
              {meta.action}
              {meta.action === 'hint' ? ` · level ${meta.hint_level}` : ''} · {meta.questioning_style}
            </p>
          )}
          {error ? (
            <p role="alert" className="text-warn">
              {error}
            </p>
          ) : (
            <Markdown text={text || '…'} />
          )}
          {done && (
            <p role="status" className="sr-only">
              Answer complete.
            </p>
          )}
          {done && done.sources.length > 0 && (
            <div className="mt-3 text-sm text-muted">
              <p className="font-medium">
                Sources (cited in the answer as [n]; others were retrieved but not cited)
              </p>
              <ol className="list-decimal ml-5">
                {done.sources.map((s) => (
                  <li key={s.chunk_id}>
                    {s.citation}
                    {s.cited ? '' : ' — not cited'}
                    {(s.flagged ?? []).length > 0 && (
                      <span className="text-warn"> (flagged: {(s.flagged ?? []).join(', ')})</span>
                    )}
                  </li>
                ))}
              </ol>
            </div>
          )}
          {done && done.sources.length === 0 && (
            <p className="text-sm text-muted mt-2">no course source for this</p>
          )}
        </Card>
      )}
      {alt && (
        <Card>
          <p className="text-xs text-muted mb-2">
            {alt.kind.replace('_', ' ')} · same learning object{alt.cached ? ' · from cache' : ''}
          </p>
          <Markdown text={alt.content} />
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
      {(done || alt) && (
        <Card>
          <p className="text-sm font-medium mb-2">Which next?</p>
          <div className="flex gap-2 flex-wrap mb-3">
            <Button variant="primary" onClick={onCheck}>
              Check yourself
            </Button>
            <Button variant="ghost" onClick={onSwitchEarly}>
              Switch early (grasp check first)
            </Button>
          </div>
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
}: {
  sessionId: string
  skillId: string | null
  hintCount: number
  onBack: () => void
  onGraded: (r: AttemptResult) => void
  onFinishBlock: () => void
}) {
  const [round, setRound] = useState(0)
  const next = useNextItem(sessionId, skillId, round)
  const attempt = useAttempt()
  const [confidence, setConfidence] = useState<number | null>(null)
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState<AttemptResult | null>(null)
  const [startedAt, setStartedAt] = useState(() => Date.now())
  const item = next.data?.item

  async function submit() {
    if (!item || confidence == null) return
    const res = await attempt.mutateAsync({
      session_id: sessionId,
      assessment_id: item.id,
      answer,
      confidence_pre: confidence,
      latency_ms: Date.now() - startedAt,
      hint_count: hintCount,
    })
    setResult(res)
    onGraded(res)
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
        <p className="text-xs text-muted mb-1">{item.kind.replace('_', ' ')}</p>
        <p className="text-base mb-3">{item.question}</p>
        {!result && (
          <>
            {item.kind === 'mcq' && item.options ? (
              <Choice<string>
                label="Your answer"
                options={item.options.map((o, i) => ({ value: String(i), label: o }))}
                value={answer || null}
                onChange={setAnswer}
                columns={1}
              />
            ) : (
              <>
                <label htmlFor="answer" className="text-sm font-medium">
                  Your answer
                </label>
                <Textarea id="answer" value={answer} onChange={(e) => setAnswer(e.target.value)} />
              </>
            )}
            <div className="mt-3">
              <Choice<number>
                label="Before feedback: how confident are you? (1 = guessing, 5 = certain)"
                options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
                value={confidence}
                onChange={setConfidence}
                columns={5}
              />
            </div>
            <div className="flex gap-2 mt-3">
              <Button
                variant="primary"
                onClick={() => void submit()}
                disabled={!answer || confidence == null || attempt.isPending}
              >
                {attempt.isPending ? 'Grading…' : 'Submit'}
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
          <p className="font-medium">
            Score {(result.score * 100).toFixed(0)}% · graded by {result.grader_level} · confidence{' '}
            {result.confidence_pre}/5: {result.calibration}
          </p>
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
            <Button variant="primary" onClick={nextItem}>
              Next item
            </Button>
            <Button onClick={onBack}>Back to explanation</Button>
            <Button onClick={onFinishBlock}>Finish this block</Button>
          </div>
        </Card>
      )}
    </>
  )
}
