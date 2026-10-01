import { OptionalConfidence } from '../../components/OptionalConfidence'
import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { Choice } from '../../components/ui/choice'
import { Textarea } from '../../components/ui/textarea'
import type { AttemptResult } from '../../lib/api'
import {
  useChallengeModes,
  useChallengeStart,
  useChallengeSubmit,
  type ChallengeMode,
  type ChallengeView,
} from './api'

/** Opt-in critical-thinking block: choose one of four concrete modes, answer, get criterion feedback. */
export function ChallengePanel({
  sessionId,
  skillId,
  onDone,
}: {
  sessionId: string
  skillId: string | null
  onDone: () => void
}) {
  const modes = useChallengeModes()
  const start = useChallengeStart()
  const submit = useChallengeSubmit()
  const [mode, setMode] = useState<ChallengeMode | null>(null)
  const [item, setItem] = useState<ChallengeView | null>(null)
  const [answer, setAnswer] = useState('')
  const [confidence, setConfidence] = useState<number | null>(null)
  const [result, setResult] = useState<AttemptResult | null>(null)
  const [startedAt, setStartedAt] = useState(() => Date.now())

  async function begin(m: ChallengeMode) {
    setMode(m)
    setResult(null)
    setAnswer('')
    setConfidence(null)
    const it = await start.mutateAsync({ session_id: sessionId, mode: m, skill_id: skillId })
    setItem(it)
    setStartedAt(Date.now())
  }

  async function send() {
    if (!item) return
    try {
      const res = await submit.mutateAsync({
        session_id: sessionId,
        assessment_id: item.assessment_id,
        answer,
        confidence_pre: confidence,
        latency_ms: Date.now() - startedAt,
        hint_count: 0,
      })
      setResult(res)
    } catch {
      // The mutation alert offers retry; preserve the answer and confidence.
    }
  }

  if (!item) {
    return (
      <Card>
        <CardTitle>Challenge (optional)</CardTitle>
        <Choice<ChallengeMode>
          label="Which kind?"
          options={(modes.data?.modes ?? []).map((m) => ({
            value: m.mode as ChallengeMode,
            label: m.mode.replace('_', ' '),
            hint: m.hint,
          }))}
          value={mode}
          onChange={(m) => void begin(m)}
          columns={2}
        />
        {start.isPending && <p className="text-sm text-muted mt-2">Generating the challenge…</p>}
        {start.isError && (
          <p role="alert" className="text-warn mt-2">
            {(start.error as Error).message}
          </p>
        )}
        <Button variant="ghost" className="mt-3" onClick={onDone}>
          Skip the challenge
        </Button>
      </Card>
    )
  }

  return (
    <Card>
      <p className="text-xs text-muted">
        {item.mode.replace('_', ' ')}
        {item.cached ? ' · reused item' : ''}
      </p>
      <p className="mt-2 whitespace-pre-wrap">{item.prompt}</p>
      {item.criteria.length > 0 && (
        <p className="text-sm text-muted mt-2">A complete answer: {item.criteria.join('; ')}.</p>
      )}
      {!result ? (
        <>
          <label htmlFor="challenge-answer" className="text-sm font-medium mt-3 block">
            Your answer
          </label>
          <Textarea id="challenge-answer" value={answer} onChange={(e) => setAnswer(e.target.value)} />
          <div className="mt-3">
            <OptionalConfidence value={confidence} onChange={setConfidence} />
          </div>
          <div className="flex gap-2 mt-3">
            <Button variant="primary" disabled={!answer || submit.isPending} onClick={() => void send()}>
              {submit.isPending ? 'Grading…' : 'Submit'}
            </Button>
            <Button variant="ghost" onClick={onDone}>
              Stop here
            </Button>
          </div>
          {submit.isError && (
            <p role="alert" className="text-warn mt-2">
              {submit.error.message}
            </p>
          )}
        </>
      ) : (
        <div role="status" className="mt-3">
          <p className="font-medium">
            Score {(result.score * 100).toFixed(0)}% · graded by {result.grader_level} · confidence{' '}
            {result.confidence_pre == null
              ? 'not supplied'
              : `${result.confidence_pre}/5: ${result.calibration}`}
          </p>
          <p className="mt-2">{result.feedback}</p>
          <p className="mt-1 text-sm">{result.next_step}</p>
          <ul className="mt-2 text-sm list-disc ml-5">
            {result.criterion_results.map((c) => (
              <li key={c.criterion}>
                {c.passed ? '✓' : '✗'} {c.criterion}
              </li>
            ))}
          </ul>
          <p className="text-sm text-muted mt-2">
            A delayed review of this challenge is scheduled for{' '}
            {new Date(result.review.due as string).toLocaleDateString()}.
          </p>
          <div className="flex gap-2 mt-3">
            <Button variant="primary" onClick={onDone}>
              Continue
            </Button>
            <Button onClick={() => setItem(null)}>Another mode</Button>
          </div>
        </div>
      )}
    </Card>
  )
}
