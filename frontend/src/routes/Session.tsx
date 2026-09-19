import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Markdown } from '../components/Markdown'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Choice } from '../components/ui/choice'
import { Textarea } from '../components/ui/textarea'
import { useAttempt, useNextItem } from '../features/assess/api'
import { useSession } from '../features/session/api'
import { SoftTimer } from '../features/session/SoftTimer'
import { useTutorStream } from '../features/tutor/useTutorStream'
import type { AttemptResult } from '../lib/api'
import { SOFT_TIMER_MIN, useMode } from '../stores/mode'

type Phase = 'teach' | 'assess'
const REPRESENTATIONS = [
  { value: 'analogy', label: 'Analogy' },
  { value: 'derivation', label: 'Derivation' },
  { value: 'code', label: 'Code' },
  { value: 'worked example', label: 'Worked example' },
]

export function Session() {
  const { sessionId, skillId, setSkill, mode } = useMode()
  const nav = useNavigate()
  const session = useSession(sessionId)
  const [phase, setPhase] = useState<Phase>('teach')
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
  const skill = session.data?.next_skill
  const currentSkillId = skillId ?? skill?.id ?? null
  if (skill && !skillId) setSkill(skill.id)

  return (
    <div className="grid gap-4">
      <SoftTimer
        minutes={SOFT_TIMER_MIN[mode]}
        onSaveStop={() => nav('/recap')}
        onFinishBlock={() => setPhase('assess')}
      />
      <Card>
        <CardTitle>
          {phase === 'teach' ? 'Learn' : 'Check yourself'}: {skill?.title ?? '…'}
        </CardTitle>
        {skill && phase === 'teach' && (
          <p className="text-sm text-muted">
            Goal: {skill.description} · mastery {(skill.mastery * 100).toFixed(0)}%
          </p>
        )}
      </Card>
      {phase === 'teach' ? (
        <TeachPanel sessionId={sessionId} skillId={currentSkillId} onCheck={() => setPhase('assess')} />
      ) : (
        <AssessPanel sessionId={sessionId} skillId={currentSkillId} onBack={() => setPhase('teach')} />
      )}
    </div>
  )
}

function TeachPanel({
  sessionId,
  skillId,
  onCheck,
}: {
  sessionId: string
  skillId: string | null
  onCheck: () => void
}) {
  const [input, setInput] = useState('')
  const { text, meta, done, error, busy, run, stop } = useTutorStream()
  const base = { session_id: sessionId, skill_id: skillId }

  return (
    <>
      <Card>
        <label htmlFor="ask" className="text-sm font-medium">
          What do you want explained? (or leave empty for the next idea)
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
            onClick={() =>
              void run({
                ...base,
                text: input.trim() || 'I am stuck.',
                action: 'hint',
              })
            }
          >
            Hint
          </Button>
          <Button
            disabled={busy}
            onClick={() =>
              void run({
                ...base,
                text: input.trim() || 'Recap this skill.',
                action: 'summarize',
              })
            }
          >
            Recap
          </Button>
          {busy && (
            <Button variant="ghost" onClick={stop}>
              Stop
            </Button>
          )}
        </div>
      </Card>
      {(text || busy || error) && (
        <Card aria-live="polite" aria-busy={busy}>
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
          {done && done.sources.length > 0 && (
            <div className="mt-3 text-sm text-muted">
              <p className="font-medium">Sources</p>
              <ul className="list-disc ml-5">
                {done.sources.map((s) => (
                  <li key={s.chunk_id}>
                    {s.citation}
                    {(s.flagged ?? []).length > 0 && (
                      <span className="text-warn"> (flagged: {(s.flagged ?? []).join(', ')})</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {done && done.sources.length === 0 && (
            <p className="text-sm text-muted mt-2">no course source for this</p>
          )}
        </Card>
      )}
      {done && (
        <Card>
          <p className="text-sm font-medium mb-2">Which next?</p>
          <div className="flex gap-2 flex-wrap">
            <Button variant="primary" onClick={onCheck}>
              Check yourself
            </Button>
            <Choice<string>
              label="Show it differently"
              options={REPRESENTATIONS}
              value={done.representation ?? null}
              onChange={(r) =>
                void run({
                  ...base,
                  text: `Explain this again as a ${r}.`,
                  action: 'explain',
                  representation: r,
                })
              }
              columns={4}
            />
          </div>
          <details className="mt-3">
            <summary className="cursor-pointer text-sm">Full solution (explicit request, logged)</summary>
            <Button
              className="mt-2"
              onClick={() =>
                void run({
                  ...base,
                  text: 'show the full solution',
                  action: 'full_solution',
                })
              }
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
  onBack,
}: {
  sessionId: string
  skillId: string | null
  onBack: () => void
}) {
  const [round, setRound] = useState(0)
  const next = useNextItem(sessionId, skillId, round)
  const attempt = useAttempt()
  const [confidence, setConfidence] = useState<number | null>(null)
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState<AttemptResult | null>(null)
  const [startedAt] = useState(() => Date.now())
  const nav = useNavigate()
  const item = next.data?.item

  async function submit() {
    if (!item || confidence == null) return
    const res = await attempt.mutateAsync({
      session_id: sessionId,
      assessment_id: item.id,
      answer,
      confidence_pre: confidence,
      latency_ms: Date.now() - startedAt,
      hint_count: 0,
    })
    setResult(res)
  }

  function nextItem() {
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
                options={item.options.map((o, i) => ({
                  value: String(i),
                  label: o,
                }))}
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
                options={[1, 2, 3, 4, 5].map((n) => ({
                  value: n,
                  label: String(n),
                }))}
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
            Score {(result.score * 100).toFixed(0)}% · graded by {result.grader_level} · you were{' '}
            {result.calibration}
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
            <Button onClick={() => nav('/review')}>Go to review</Button>
            <Button onClick={() => nav('/recap')}>Finish session</Button>
          </div>
        </Card>
      )}
    </>
  )
}
