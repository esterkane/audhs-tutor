import { useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { Choice } from '../../components/ui/choice'
import { useAttempt } from '../assess/api'
import type { AttemptResult } from '../../lib/api'
import { useExercise, useHint, useSolution, type ExerciseView } from './api'
import { createPyodideRunner, type RunResult, type Runner } from './runner'
import { CodeEditor } from './CodeEditor'
import { readPlainPreference, writePlainPreference } from './editorPreference'

/**
 * One source-linked code exercise (P8). The learner's code runs in the browser sandbox only
 * (Pyodide in a worker: timeout, output cap, no network, no host files). Run ≠ attempt: Run only
 * executes and shows the deterministic checks; Submit records an assessed attempt after a
 * confidence rating, using the results of the *current* code. Hints one step at a time; the full
 * solution only on an explicit click, followed by a check question. The draft survives a reload.
 */
export function CodeExercise({
  sessionId,
  skillId,
  runner,
  onGraded,
}: {
  sessionId: string
  skillId: string
  runner?: Runner
  onGraded?: (r: AttemptResult) => void
}) {
  const exercise = useExercise(skillId)
  if (exercise.isLoading)
    return (
      <p className="text-sm" role="status">
        Loading the exercise…
      </p>
    )
  if (!exercise.data) return null
  return <Editor sessionId={sessionId} exercise={exercise.data} runner={runner} onGraded={onGraded} />
}

function draftKey(id: string) {
  return `code-draft:${id}`
}

function Editor({
  sessionId,
  exercise,
  runner: injected,
  onGraded,
}: {
  sessionId: string
  exercise: ExerciseView
  runner?: Runner
  onGraded?: (r: AttemptResult) => void
}) {
  const runner = useMemo(() => injected ?? createPyodideRunner(), [injected])
  // the draft is a per-viewer convenience: read once at mount, saved on every change
  const [initialDraft] = useState<string | null>(() => {
    try {
      return localStorage.getItem(draftKey(exercise.assessment_id))
    } catch {
      return null
    }
  })
  const [code, setCode] = useState<string>(initialDraft ?? exercise.starter_code)
  const draftRestored = initialDraft != null && initialDraft !== exercise.starter_code
  const [runtime, setRuntime] = useState<'idle' | 'loading' | 'ready' | 'failed'>('idle')
  const [runtimeError, setRuntimeError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [last, setLast] = useState<{ code: string; result: RunResult } | null>(null)
  const [hints, setHints] = useState<string[]>([])
  const [solution, setSolution] = useState<{ solution: string; check_question: string } | null>(null)
  const [confirmSolution, setConfirmSolution] = useState(false)
  const [confidence, setConfidence] = useState<number | null>(null)
  const [graded, setGraded] = useState<AttemptResult | null>(null)
  const hint = useHint()
  const solve = useSolution()
  const attempt = useAttempt()
  const startedAt = useRef(0)
  // per-viewer preference: the plain <textarea> instead of CodeMirror (also the mount fallback)
  const [plainEditor, setPlainEditor] = useState<boolean>(() => readPlainPreference())
  const [editorNote, setEditorNote] = useState<string | null>(null)
  const [checkAnswer, setCheckAnswer] = useState('')
  const [checkConfidence, setCheckConfidence] = useState<number | null>(null)
  const [checkResult, setCheckResult] = useState<AttemptResult | null>(null)

  useEffect(() => {
    try {
      localStorage.setItem(draftKey(exercise.assessment_id), code)
    } catch {
      /* per-viewer convenience only */
    }
  }, [code, exercise.assessment_id])
  useEffect(() => () => runner.dispose(), [runner])

  async function run() {
    if (startedAt.current === 0) startedAt.current = Date.now()
    setRunning(true)
    setGraded(null)
    setRuntimeError(null)
    try {
      if (runtime !== 'ready') {
        setRuntime('loading')
        await runner.load(exercise.packages)
        setRuntime('ready')
      }
      const result = await runner.run(code, exercise.checks, {
        timeoutMs: exercise.timeout_s * 1000,
        maxOutputChars: exercise.max_output_chars,
        packages: exercise.packages,
      })
      setLast({ code, result })
      if (result.timedOut) setRuntime('idle') // the worker was stopped; the next Run reloads it
    } catch (e) {
      setRuntime('failed')
      setRuntimeError((e as Error).message)
    } finally {
      setRunning(false)
    }
  }

  function reset() {
    setCode(exercise.starter_code)
    setLast(null)
    setGraded(null)
    try {
      localStorage.removeItem(draftKey(exercise.assessment_id))
    } catch {
      /* ignore */
    }
  }

  async function submit() {
    if (!last || last.code !== code || confidence == null) return
    const res = await attempt.mutateAsync({
      session_id: sessionId,
      assessment_id: exercise.assessment_id,
      answer: JSON.stringify({
        code,
        results: last.result.results,
        truncated: last.result.truncated,
        error: last.result.error,
        ms: last.result.ms,
        runtime: exercise.runtime,
        solution_shown: solution != null,
      }),
      confidence_pre: confidence,
      latency_ms: Date.now() - startedAt.current,
      hint_count: hints.length,
    })
    setGraded(res)
    onGraded?.(res)
  }

  async function submitCheck() {
    if (!exercise.check_assessment_id || checkConfidence == null || !checkAnswer.trim()) return
    const res = await attempt.mutateAsync({
      session_id: sessionId,
      assessment_id: exercise.check_assessment_id,
      answer: checkAnswer,
      confidence_pre: checkConfidence,
      latency_ms: 0,
      hint_count: 0,
    })
    setCheckResult(res)
  }

  const stale = last != null && last.code !== code
  const canSubmit = last != null && !stale && confidence != null && !attempt.isPending

  return (
    <Card>
      <CardTitle>Code exercise: {exercise.title}</CardTitle>
      <p className="text-sm mt-1">{exercise.prompt}</p>
      <ul className="text-sm text-muted mt-2 list-disc pl-5" aria-label="Success criteria">
        {exercise.success_criteria.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
      {exercise.sources.length > 0 && (
        <p className="text-xs text-muted mt-1">
          Sources: {exercise.sources.map((s) => s.citation).join(' ')}
        </p>
      )}
      <details className="mt-2 text-xs text-muted">
        <summary className="cursor-pointer">Where your code runs</summary>
        {exercise.policy.where as string}. Network: {exercise.policy.network as string}. Files:{' '}
        {exercise.policy.filesystem as string}. Stops after {exercise.timeout_s} s; output capped at{' '}
        {exercise.max_output_chars} characters. {exercise.policy.runtime_download as string}.
      </details>
      {draftRestored && (
        <p className="text-xs text-muted mt-2" role="status">
          Your saved draft was restored; Reset returns the starter code.
        </p>
      )}
      <label
        id="code-editor-label"
        htmlFor={plainEditor ? 'code-editor' : undefined}
        className="text-sm font-medium block mt-3"
      >
        {plainEditor
          ? 'Your code (Python; Tab inserts two spaces — Shift+Tab, or Esc then Tab, leaves the editor)'
          : 'Your code (Python; Tab indents — Esc then Tab leaves the editor)'}
      </label>
      <CodeEditor
        id="code-editor"
        value={code}
        onChange={setCode}
        plain={plainEditor}
        onPlainFallback={(reason) => {
          setPlainEditor(true)
          setEditorNote(`The code editor could not start (${reason}); using the plain editor.`)
        }}
      />
      {editorNote && (
        <p className="text-xs text-muted mt-1" role="status">
          {editorNote}
        </p>
      )}
      <button
        type="button"
        className="text-xs underline text-muted mt-1"
        onClick={() => {
          const next = !plainEditor
          setPlainEditor(next)
          setEditorNote(null)
          writePlainPreference(next)
        }}
      >
        {plainEditor ? 'Switch to the code editor' : 'Switch to the plain editor'}
      </button>
      <div className="flex flex-wrap gap-2 mt-2">
        <Button
          variant="primary"
          onClick={() => {
            if (runtime === 'failed') setRuntime('idle')
            void run()
          }}
          disabled={running}
        >
          {running
            ? runtime === 'loading'
              ? 'Loading Python runtime…'
              : 'Running…'
            : runtime === 'failed'
              ? 'Try loading the runtime again'
              : 'Run'}
        </Button>
        <Button variant="secondary" onClick={reset} disabled={running}>
          Reset to starter code
        </Button>
        <Button
          variant="ghost"
          disabled={hint.isPending || hints.length >= exercise.hints_available}
          onClick={() =>
            void hint
              .mutateAsync({ assessmentId: exercise.assessment_id, sessionId, level: hints.length + 1 })
              .then((h) => setHints((hs) => [...hs, h.text]))
          }
        >
          {hints.length >= exercise.hints_available
            ? 'No more hints'
            : `Hint ${hints.length + 1} of ${exercise.hints_available}`}
        </Button>
      </div>
      {runtime === 'loading' && (
        <p className="text-sm text-muted mt-2" role="status">
          Loading the Python runtime (Pyodide + {exercise.packages.join(', ')}) from this app — the first time
          takes a moment. Your code has not run yet.
        </p>
      )}
      {runtime === 'failed' && (
        <p className="text-sm text-warn mt-2" role="alert">
          The Python runtime could not be loaded ({runtimeError}). You can still read, edit and think through
          the exercise; running needs the runtime. If it is not installed, run `make pyodide` on the machine
          serving the app, then try again.
        </p>
      )}
      {hints.length > 0 && (
        <ol className="text-sm mt-3 list-decimal pl-5" aria-label="Hints">
          {hints.map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ol>
      )}
      <section className="mt-3" aria-label="Run result" aria-live="polite">
        {last && (
          <>
            {last.result.error ? (
              <pre className="text-sm text-warn whitespace-pre-wrap border border-line rounded-md p-2">
                {last.result.error}
              </pre>
            ) : (
              <ul className="text-sm grid gap-1" aria-label="Checks">
                {last.result.results.map((r) => (
                  <li key={r.name}>
                    <span aria-hidden="true">{r.passed ? '✓' : '✗'}</span>
                    <span className="sr-only">{r.passed ? 'passed:' : 'failed:'}</span>{' '}
                    {exercise.checks.find((c) => c.name === r.name)?.criterion ?? r.name}
                    {r.passed ? '' : ` — ${r.detail}`}
                  </li>
                ))}
              </ul>
            )}
            {last.result.stdout && (
              <pre className="text-xs whitespace-pre-wrap border border-line rounded-md p-2 mt-2 max-h-48 overflow-auto">
                {last.result.stdout}
                {last.result.truncated ? '\n… output cut at the limit' : ''}
              </pre>
            )}
            <p className="text-xs text-muted mt-1">
              Ran in {last.result.ms} ms in your browser. Running is not an attempt — nothing was recorded.
            </p>
          </>
        )}
      </section>
      {last && (
        <div className="mt-4 border-t border-line pt-3">
          <p className="text-sm font-medium">Submit for assessment</p>
          <p className="text-xs text-muted">
            Uses the checks of the code you last ran.
            {stale ? ' You changed the code since — run it again first.' : ''}
          </p>
          <div className="mt-2">
            <Choice<number>
              label="Before feedback: how confident are you? (1 = guessing, 5 = certain)"
              options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
              value={confidence ?? 0}
              onChange={setConfidence}
              columns={5}
            />
          </div>
          <Button className="mt-2" variant="primary" disabled={!canSubmit} onClick={() => void submit()}>
            Submit this attempt
          </Button>
          {attempt.isError && (
            <p role="alert" className="text-sm text-warn mt-2">
              {(attempt.error as Error).message}
            </p>
          )}
          {graded && (
            <div className="mt-3" role="status">
              <p className="text-sm">{graded.feedback}</p>
              <ul className="text-sm mt-1" aria-label="Criteria">
                {graded.criterion_results.map((c) => (
                  <li key={c.criterion}>
                    {c.passed ? '✓' : '✗'} {c.criterion}
                  </li>
                ))}
              </ul>
              <p className="text-sm text-muted mt-1">{graded.next_step}</p>
              <p className="text-xs text-muted mt-1">
                Recorded as application evidence ({graded.criterion_results.filter((c) => c.passed).length} of{' '}
                {graded.criterion_results.length} criteria{graded.confidence < 1 ? ', half weight' : ''}). A
                review of this node is due in at least two days.
              </p>
              {graded.correct === true && exercise.check_assessment_id && !checkResult && (
                <CheckQuestion
                  question={exercise.check_question}
                  answer={checkAnswer}
                  setAnswer={setCheckAnswer}
                  confidence={checkConfidence}
                  setConfidence={setCheckConfidence}
                  onSubmit={() => void submitCheck()}
                  pending={attempt.isPending}
                />
              )}
              {checkResult && (
                <p className="text-sm mt-2" role="status">
                  {checkResult.feedback} {checkResult.next_step}
                </p>
              )}
            </div>
          )}
        </div>
      )}
      {hints.length >= exercise.hints_available && (
        <div className="mt-4 border-t border-line pt-3">
          {!solution ? (
            !confirmSolution ? (
              <Button variant="ghost" size="sm" onClick={() => setConfirmSolution(true)}>
                Show the full solution
              </Button>
            ) : (
              <div className="flex flex-wrap gap-2 items-center">
                <span className="text-sm">
                  Show the whole solution now? It is logged, and a check question follows.
                </span>
                <Button
                  size="sm"
                  variant="primary"
                  disabled={solve.isPending}
                  onClick={() =>
                    void solve
                      .mutateAsync({ assessmentId: exercise.assessment_id, sessionId })
                      .then((s) => setSolution(s))
                  }
                >
                  Yes, show it
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setConfirmSolution(false)}>
                  Not yet
                </Button>
              </div>
            )
          ) : (
            <div>
              <pre className="text-sm font-mono whitespace-pre-wrap border border-line rounded-md p-2">
                {solution.solution}
              </pre>
              {exercise.check_assessment_id && !checkResult ? (
                <CheckQuestion
                  question={solution.check_question}
                  answer={checkAnswer}
                  setAnswer={setCheckAnswer}
                  confidence={checkConfidence}
                  setConfidence={setCheckConfidence}
                  onSubmit={() => void submitCheck()}
                  pending={attempt.isPending}
                />
              ) : (
                <p className="text-sm mt-2" role="status">
                  {checkResult ? `${checkResult.feedback} ${checkResult.next_step}` : solution.check_question}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

/** The check question is answered and graded as explain-back, not just shown. */
function CheckQuestion({
  question,
  answer,
  setAnswer,
  confidence,
  setConfidence,
  onSubmit,
  pending,
}: {
  question: string
  answer: string
  setAnswer: (v: string) => void
  confidence: number | null
  setConfidence: (v: number) => void
  onSubmit: () => void
  pending: boolean
}) {
  return (
    <div className="mt-3">
      <label htmlFor="check-answer" className="text-sm font-medium block">
        {question}
      </label>
      <p className="text-xs text-muted">Answer in one sentence; it is graded as explain-back on this node.</p>
      <textarea
        id="check-answer"
        className="w-full text-sm border border-line rounded-md p-2 min-h-16 mt-1"
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
      />
      <div className="mt-2">
        <Choice<number>
          label="Before feedback: how confident are you? (1 = guessing, 5 = certain)"
          options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
          value={confidence ?? 0}
          onChange={setConfidence}
          columns={5}
        />
      </div>
      <Button
        size="sm"
        className="mt-2"
        disabled={pending || confidence == null || !answer.trim()}
        onClick={onSubmit}
      >
        Check my answer
      </Button>
    </div>
  )
}
