import { QuestionPractice } from '../questions/QuestionPractice'
import { readDraft, writeDraft, clearDraft } from '../assess/draft'
import { boundedRead } from '../../lib/boundedRead'
import { Link } from 'react-router-dom'
import { AssessmentRecovery } from '../assess/AssessmentRecovery'
import { AssessmentSaveStatus } from '../programs/AssessmentSaveStatus'
import { OptionalConfidence } from '../../components/OptionalConfidence'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { Choice } from '../../components/ui/choice'
import { Textarea } from '../../components/ui/textarea'
import { apiFetch, type AssessmentView, type AttemptResult } from '../../lib/api'
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
  const [practiceChanged, setPracticeChanged] = useState(false)
  const [practiceRestored, setPracticeRestored] = useState(false)
  const [refreshingPractice, setRefreshingPractice] = useState(false)
  const [practiceError, setPracticeError] = useState('')
  const refreshRequest = useRef<AbortController | null>(null)
  const practicePanel = useRef<HTMLDivElement>(null)
  const beginning = useRef(false)
  useEffect(() => () => refreshRequest.current?.abort(), [])
  const draftKey = (id: string) => `challenge:${sessionId}:${id}`
  const modes = useChallengeModes()
  const start = useChallengeStart()
  const submit = useChallengeSubmit(sessionId)
  const [mode, setMode] = useState<ChallengeMode | null>(null)
  const [item, setItem] = useState<ChallengeView | null>(null)
  const displayedItem = useRef(item)
  useLayoutEffect(() => {
    displayedItem.current = item
  }, [item])
  const [answer, setAnswer] = useState('')
  const [confidence, setConfidence] = useState<number | null>(null)
  const [result, setResult] = useState<AttemptResult | null>(null)
  const [startedAt, setStartedAt] = useState(() => Date.now())

  function cancelPracticeRefresh() {
    refreshRequest.current?.abort()
    refreshRequest.current = null
    setRefreshingPractice(false)
  }

  async function begin(m: ChallengeMode) {
    if (beginning.current) return
    beginning.current = true
    cancelPracticeRefresh()
    setMode(m)
    try {
      const it = await start.mutateAsync({ session_id: sessionId, mode: m, skill_id: skillId })
      setItem(it)
      setAnswer(readDraft(draftKey(it.assessment_id)).answer)
      setResult(null)
      setConfidence(null)
      setPracticeChanged(false)
      setPracticeRestored(false)
      setPracticeError('')
      setStartedAt(Date.now())
    } catch {
      // Keep drafts and show the mutation error; an excluded item is not silently regenerated.
    } finally {
      beginning.current = false
    }
  }

  async function refreshPractice() {
    if (!item || !practiceRestored || refreshRequest.current) return
    const controller = new AbortController()
    refreshRequest.current = controller
    setRefreshingPractice(true)
    setPracticeError('')
    try {
      const latest = await boundedRead<AssessmentView>(
        `/api/assess/items/${encodeURIComponent(item.assessment_id)}?session_id=${encodeURIComponent(sessionId)}`,
        controller.signal, 'Challenge',
      )
      if (controller.signal.aborted || displayedItem.current?.assessment_id !== item.assessment_id) return
      if (latest.id !== item.assessment_id) throw new Error('Different question')
      setItem({ ...item, prompt: latest.question, criteria: latest.criteria ?? [], content_version: latest.content_version })
      setPracticeChanged(false)
      setPracticeRestored(false)
      requestAnimationFrame(() => practicePanel.current?.focus())
    } catch {
      if (!controller.signal.aborted) setPracticeError('Could not refresh the challenge. Your answer is kept. Try again.')
    } finally {
      if (!controller.signal.aborted) setRefreshingPractice(false)
      if (refreshRequest.current === controller) refreshRequest.current = null
    }
  }

  async function send() {
    if (!item || practiceChanged) return
    try {
      const res = await submit.mutateAsync({
        session_id: sessionId,
        assessment_id: item.assessment_id,
        content_version: item.content_version,
        answer,
        questionLabel: item.prompt,
        confidence_pre: confidence,
        latency_ms: Date.now() - startedAt,
        hint_count: 0,
      })
      if (
        displayedItem.current?.assessment_id !== item.assessment_id ||
        displayedItem.current?.content_version !== item.content_version
      )
        return
      clearDraft(draftKey(item.assessment_id))
      setResult(res)
    } catch {
      // The mutation alert offers retry; preserve the answer and confidence.
    }
  }

  const recoveryPanel = (
    <AssessmentRecovery
      recovery={submit.recovery}
      onRefresh={async (signal) => {
        if (submit.recovery.pending?.body.assessment_id !== item?.assessment_id)
          throw new Error(
            'This saved answer belongs to another question. Return to that activity; the original answer is kept here.',
          )
        if (!item) throw new Error('The original challenge is unavailable.')
        const latest = await apiFetch<AssessmentView>(
          `/api/assess/items/${encodeURIComponent(item.assessment_id)}?session_id=${encodeURIComponent(sessionId)}`,
          { signal },
        )
        if (signal.aborted) throw new Error('Refresh cancelled.')
        if (latest.id !== item.assessment_id) throw new Error('The refreshed challenge does not match.')
        setItem({
          ...item,
          prompt: latest.question,
          criteria: latest.criteria ?? [],
          content_version: latest.content_version,
        })
        setResult(null)
      }}
      onUse={(saved, body) => {
        if (
          saved.assessment_id !== item?.assessment_id ||
          body.answer !== answer ||
          !body.content_version ||
          body.content_version !== item?.content_version
        )
          return false
        clearDraft(draftKey(saved.assessment_id))
        setResult(saved)
        return true
      }}
    />
  )
  if (!item) {
    return (
      <Card>
        {recoveryPanel}
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
            {(start.error as Error).message}{' '}
            <Link to="/preferences#excluded-questions">Manage excluded questions</Link>
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
      {recoveryPanel}
      <p className="text-xs text-muted">
        {item.mode.replace('_', ' ')}
        {item.cached ? ' · reused item' : ''}
      </p>
      <p className="mt-2 whitespace-pre-wrap">{item.prompt}</p>
      <div ref={practicePanel} tabIndex={-1} aria-label="Challenge practice choices">
        {!submit.recovery.pending && !submit.recovery.error && <fieldset disabled={submit.isPending || refreshingPractice}>
          <QuestionPractice assessmentId={item.assessment_id} onChanged={(id, state) => {
            if (displayedItem.current?.assessment_id !== id) return
            setPracticeChanged(true)
            setPracticeRestored(state.state === 'active')
            setPracticeError('')
          }} />
        </fieldset>}
        {practiceChanged && <div className="mt-2 grid gap-2 text-sm">
          <p role="status">{practiceRestored
            ? 'Challenge restored. Refresh the question before submitting your answer.'
            : 'This challenge is excluded. Your answer is kept in this tab. Restore the question before submitting.'}</p>
          {practiceRestored && <Button disabled={refreshingPractice} onClick={() => void refreshPractice()}>
            {refreshingPractice ? 'Refreshing challenge…' : 'Refresh restored challenge'}
          </Button>}
          {practiceError && <p role="alert">{practiceError}</p>}
        </div>}
      </div>
      {item.criteria.length > 0 && (
        <p className="text-sm text-muted mt-2">A complete answer: {item.criteria.join('; ')}.</p>
      )}
      {!result ? (
        <>
          <label htmlFor="challenge-answer" className="text-sm font-medium mt-3 block">
            Your answer
          </label>
          <Textarea id="challenge-answer" value={answer} onChange={(e) => {
            setAnswer(e.target.value)
            writeDraft(draftKey(item.assessment_id), { answer: e.target.value })
          }} />
          <div className="mt-3">
            <OptionalConfidence value={confidence} onChange={setConfidence} />
          </div>
          <div className="flex gap-2 mt-3">
            <Button variant="primary" disabled={practiceChanged || !answer || submit.isPending} onClick={() => void send()}>
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
          <AssessmentSaveStatus key={result.attempt_id} result={result} />
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
            <Button onClick={() => { cancelPracticeRefresh(); setItem(null) }}>Another mode</Button>
          </div>
        </div>
      )}
    </Card>
  )
}
