import { useIsMutating } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Markdown } from '../components/Markdown'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Textarea } from '../components/ui/textarea'
import { CodeEditor } from '../features/code/CodeEditor'
import { createPyodideRunner, type Runner, type RunResult } from '../features/code/runner'
import { readPlainPreference, writePlainPreference } from '../features/code/editorPreference'
import { activities, type Activity } from '../features/playground/exercises'
import { askTutor, type TutorRequest } from '../features/playground/api'
import { useCurrentSession, useStartSession } from '../features/session/api'
import { useMode } from '../stores/mode'

type Chat = { role: 'user' | 'assistant'; text: string; codeSnapshot?: string }
type Draft = { code: string; prediction: string; chat: Chat[] }
const keyFor = (id: string) => `playground:v1:${id}`
function restore(activity: Activity): Draft {
  try {
    const value = JSON.parse(localStorage.getItem(keyFor(activity.id)) ?? 'null')
    if (
      value &&
      typeof value.code === 'string' &&
      typeof value.prediction === 'string' &&
      Array.isArray(value.chat)
    )
      return {
        code: value.code,
        prediction: value.prediction,
        chat: value.chat
          .filter((m: Chat) => m && ['user', 'assistant'].includes(m.role) && typeof m.text === 'string')
          .slice(-24),
      }
  } catch {
    /* absent or unusable browser storage */
  }
  return { code: activity.code, prediction: '', chat: [] }
}

export function Playground({ runnerFactory = createPyodideRunner }: { runnerFactory?: () => Runner }) {
  const [selected, setSelected] = useState('scratch')
  const activity = activities.find((a) => a.id === selected) ?? activities[0]
  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-xl font-semibold">Coding playground</h1>
        <p className="text-sm text-muted mt-1">
          Experiment with Python. Ask the tutor about your code. Practice here does not change mastery scores.
        </p>
      </div>
      <label className="text-sm font-medium">
        Workspace
        <select
          className="block border border-line bg-card rounded-md p-2 mt-1 w-full"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          {activities.map((a) => (
            <option value={a.id} key={a.id}>
              {a.title}
            </option>
          ))}
        </select>
      </label>
      <Workspace
        key={activity.id}
        activity={activity}
        runnerFactory={runnerFactory}
        onNext={() => setSelected(activity.id === 'worked' ? 'complete' : 'independent')}
      />
    </div>
  )
}

function Workspace({
  activity,
  runnerFactory,
  onNext,
}: {
  activity: Activity
  runnerFactory: () => Runner
  onNext: () => void
}) {
  const [draft, setDraft] = useState(() => restore(activity))
  const [saveError, setSaveError] = useState(false)
  const [plain, setPlain] = useState(readPlainPreference)
  const [running, setRunning] = useState(false)
  const [last, setLast] = useState<{ code: string; result: RunResult } | null>(null)
  const [runError, setRunError] = useState('')
  const [question, setQuestion] = useState('')
  const [tutorError, setTutorError] = useState('')
  const [busy, setBusy] = useState(false)
  const [tutorOpen, setTutorOpen] = useState(true)
  const [modelNote, setModelNote] = useState('')
  const [resetting, setResetting] = useState(false)
  const operation = useRef<{ runner: Runner; abort: AbortController } | null>(null)
  const tutorAbort = useRef<AbortController | null>(null)
  const current = useCurrentSession()
  const start = useStartSession()
  const { mode, energy, socratic, setSession } = useMode()
  const startingSession = useIsMutating({ mutationKey: ['session-start'] }) > 0
  const sessionId = current.data?.id ?? null
  const stale = !!last && last.code !== draft.code

  useEffect(() => {
    try {
      localStorage.setItem(keyFor(activity.id), JSON.stringify(draft))
      // External storage can fail independently of React state; reflect the write result.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSaveError(false)
    } catch {
      setSaveError(true)
    }
  }, [draft, activity.id])
  useEffect(
    () => () => {
      operation.current?.abort.abort()
      operation.current?.runner.dispose()
      tutorAbort.current?.abort()
    },
    [],
  )

  async function run() {
    if (operation.current) return
    const runner = runnerFactory()
    const abort = new AbortController()
    const op = { runner, abort }
    operation.current = op
    setRunning(true)
    setRunError('')
    const code = draft.code
    let timer: ReturnType<typeof setTimeout> | undefined
    try {
      const cancelled = new Promise<never>((_, reject) => {
        abort.signal.addEventListener('abort', () => reject(new Error('Run stopped. Your code is kept.')), {
          once: true,
        })
        timer = setTimeout(() => reject(new Error('Python took too long to load or run. Try again.')), 45000)
      })
      const result = await Promise.race([
        runner.run(code, activity.checks, { timeoutMs: 10000, maxOutputChars: 4000, packages: [] }),
        cancelled,
      ])
      if (operation.current === op) setLast({ code, result })
    } catch (e) {
      if (operation.current === op) setRunError((e as Error).message)
    } finally {
      clearTimeout(timer)
      runner.dispose()
      if (operation.current === op) {
        operation.current = null
        setRunning(false)
      }
    }
  }

  async function enableTutor() {
    try {
      const s = await start.mutateAsync({ mode, energy, socratic })
      setSession(s.id, s.state?.skill_id ?? null)
    } catch {
      /* rendered below */
    }
  }

  async function ask(intent: TutorRequest['intent']) {
    if (!sessionId || tutorAbort.current) return
    const defaults = {
      chat: '',
      explain: 'Explain how this code works.',
      hint: 'Give me one hint for the current task without solving it.',
      big_picture: 'Show how this task fits into a larger data workflow, and one tradeoff.',
    }
    const text = question.trim() || defaults[intent ?? 'chat']
    if (!text) return
    const submittedQuestion = question
    const codeSnapshot = draft.code
    const ctl = new AbortController()
    tutorAbort.current = ctl
    setBusy(true)
    setTutorError('')
    const timer = setTimeout(() => ctl.abort(), 90000)
    try {
      const reply = await askTutor(
        {
          session_id: sessionId,
          intent,
          question: text,
          exercise: activity.task,
          code: draft.code,
          output: last
            ? [
                last.result.stdout,
                last.result.error ?? '',
                ...last.result.results.map((r) => `${r.name}: ${r.passed ? 'passed' : r.detail}`),
              ]
                .join('\n')
                .slice(0, 4000)
            : 'Not run yet.',
          output_stale: stale,
          history: draft.chat.slice(-6).map((m) => ({ role: m.role, text: m.text.slice(0, 4000) })),
        },
        ctl.signal,
      )
      if (!ctl.signal.aborted) {
        setDraft((d) => ({
          ...d,
          chat: [
            ...d.chat,
            { role: 'user' as const, text, codeSnapshot },
            { role: 'assistant' as const, text: reply.text, codeSnapshot },
          ].slice(-24),
        }))
        setQuestion((currentQuestion) => (currentQuestion === submittedQuestion ? '' : currentQuestion))
        setModelNote(`${reply.model} · ${reply.route}. ${reply.source_note}`)
      }
    } catch (e) {
      setTutorError(
        ctl.signal.aborted
          ? 'Tutor request stopped. Your question is kept; you can retry.'
          : (e as Error).message,
      )
    } finally {
      clearTimeout(timer)
      if (tutorAbort.current === ctl) {
        tutorAbort.current = null
        setBusy(false)
      }
    }
  }

  return (
    <>
      <div className={`grid gap-4 ${tutorOpen ? 'lg:grid-cols-[minmax(0,3fr)_minmax(18rem,2fr)]' : ''}`}>
        <section className="min-w-0 grid gap-4 content-start" aria-label="Code workspace">
          <Card>
            <CardTitle>{activity.title}</CardTitle>
            <p className="mt-2 text-sm">{activity.task}</p>
            <details className="mt-3">
              <summary className="text-sm cursor-pointer">
                Big picture: input → transformation → output
              </summary>
              <ol className="grid gap-2 sm:grid-cols-3 mt-3 text-sm" aria-label="Pipeline building blocks">
                <li className="border border-line rounded p-2">
                  <strong>1. Input</strong>
                  <p>Records arrive as strings, including spaces or duplicates.</p>
                </li>
                <li className="border border-line rounded p-2">
                  <strong>2. Transform</strong>
                  <p>A function applies rules to each record and returns a new value.</p>
                </li>
                <li className="border border-line rounded p-2">
                  <strong>3. Output</strong>
                  <p>Inspect the result before passing it to another step.</p>
                </li>
              </ol>
              <p className="text-sm text-muted mt-2">
                Conceptual map for the guided exercises. LangChain and n8n also connect processing steps, but
                this is plain Python—not an execution of either framework.
              </p>
            </details>
          </Card>
          <Card>
            <label htmlFor="prediction" className="text-sm font-medium">
              Predict the output (optional)
            </label>
            <Textarea
              id="prediction"
              value={draft.prediction}
              onChange={(e) => setDraft((d) => ({ ...d, prediction: e.target.value }))}
              className="min-h-16"
            />
            <label
              id="playground-code-label"
              htmlFor={plain ? 'playground-code' : undefined}
              className="block text-sm font-medium mt-3"
            >
              Python code · Esc then Tab leaves the editor
            </label>
            <CodeEditor
              id="playground-code"
              value={draft.code}
              onChange={(code) => setDraft((d) => ({ ...d, code }))}
              plain={plain}
              onPlainFallback={() => setPlain(true)}
            />
            <p className="text-xs text-muted mt-2" role="status">
              {saveError
                ? 'Browser storage is unavailable. Copy your code before leaving.'
                : 'Code, prediction and recent chat saved in this browser. Run output is temporary.'}
            </p>
            <div className="flex flex-wrap gap-2 mt-3">
              <Button variant="primary" onClick={() => void run()} disabled={running}>
                {running ? 'Loading / running Python…' : 'Run code'}
              </Button>
              {running && <Button onClick={() => operation.current?.abort.abort()}>Stop run</Button>}
              <Button variant="ghost" onClick={() => setTutorOpen((v) => !v)}>
                {tutorOpen ? 'Hide tutor' : 'Show tutor'}
              </Button>
            </div>
            <details className="mt-3 text-sm">
              <summary className="cursor-pointer">Editor and runtime options</summary>
              <p className="text-muted mt-2">
                Python runs in a browser worker with temporary files and a 10-second execution limit. The
                runtime loads from this app. External packages and real service connections are not supported
                here.
              </p>
              <Button
                className="mt-2"
                onClick={() => {
                  setPlain(!plain)
                  writePlainPreference(!plain)
                }}
              >
                {plain ? 'Use code editor' : 'Use plain editor'}
              </Button>
              <Button className="mt-2 ml-2" disabled={running || busy} onClick={() => setResetting(true)}>
                Reset this workspace
              </Button>
              {resetting && (
                <div className="mt-2">
                  <p>Replace this workspace’s code with its starter? Your prediction and chat stay saved.</p>
                  <Button
                    onClick={() => {
                      setDraft((d) => ({ ...d, code: activity.code }))
                      setLast(null)
                      setResetting(false)
                    }}
                  >
                    Replace code
                  </Button>
                  <Button variant="ghost" onClick={() => setResetting(false)}>
                    Keep my code
                  </Button>
                </div>
              )}
            </details>
            {runError && (
              <p role="alert" className="text-warn mt-2">
                {runError}
              </p>
            )}
          </Card>
          <Card>
            <CardTitle>Output</CardTitle>
            {!last ? (
              <p className="text-sm text-muted">Run your code to see what it produces.</p>
            ) : (
              <div role="status">
                {stale && (
                  <p className="text-warn text-sm">
                    This output is from earlier code. Run again to update it.
                  </p>
                )}
                <pre className="text-sm whitespace-pre-wrap break-words mt-2 max-h-64 overflow-auto">
                  {last.result.stdout || '(No printed output)'}
                </pre>
                {last.result.truncated && <p className="text-sm">Output stopped at 4,000 characters.</p>}
                {last.result.error && (
                  <pre className="text-sm text-warn whitespace-pre-wrap break-words">{last.result.error}</pre>
                )}
                {last.result.results.length > 0 && (
                  <>
                    <p className="text-sm mt-3">Practice checks—not a mastery assessment:</p>
                    <ul className="text-sm">
                      {last.result.results.map((r) => (
                        <li key={r.name}>
                          {r.passed ? 'Pass' : 'Try again'}:{' '}
                          {activity.checks.find((c) => c.name === r.name)?.criterion} {!r.passed && r.detail}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {draft.prediction && (
                  <p className="mt-3 text-sm">Compare with your prediction: {draft.prediction}</p>
                )}
              </div>
            )}
          </Card>
          {(activity.id === 'worked' || activity.id === 'complete') && (
            <Button onClick={onNext}>Next guided step (optional)</Button>
          )}
        </section>
        {tutorOpen && (
          <aside className="min-w-0" aria-label="Playground tutor">
            <Card>
              <CardTitle>Tutor beside you</CardTitle>
              <p className="text-sm text-muted mt-2">
                On each request, the tutor receives this task, current code, last output and the last six chat
                messages. It cannot edit or run your code. Your configured model route is used.
              </p>
              {!sessionId && (
                <div className="mt-3">
                  <p className="text-sm">
                    Coding works without a session. Start one to save tutor activity; finish it through Recap.
                  </p>
                  <Button
                    onClick={() => void enableTutor()}
                    disabled={startingSession || current.isLoading || current.isError}
                  >
                    {startingSession ? 'Starting…' : 'Start session for tutor'}
                  </Button>
                </div>
              )}
              {current.isError && (
                <p role="alert">
                  Could not check your session.{' '}
                  <button className="underline" onClick={() => void current.refetch()}>
                    Retry
                  </button>
                </p>
              )}
              {start.isError && <p role="alert">{start.error.message}</p>}
              {sessionId && (
                <p className="text-sm mt-2">
                  Tutor activity uses your current session.{' '}
                  <Link to="/recap" onClick={() => setSession(sessionId, null)}>
                    Finish with recap
                  </Link>
                </p>
              )}
              <div className="grid gap-3 mt-4 max-h-[30rem] overflow-auto" aria-label="Tutor conversation">
                {draft.chat.map((m, i) => (
                  <div key={i} className="border-b border-line pb-2">
                    <p className="text-xs font-medium">{m.role === 'user' ? 'You' : 'Tutor'}</p>
                    {m.role === 'assistant' &&
                      typeof m.codeSnapshot === 'string' &&
                      m.codeSnapshot !== draft.code && (
                        <p className="text-xs text-warn">This answer refers to earlier code.</p>
                      )}
                    <Markdown text={m.text} />
                    {m.role === 'user' && typeof m.codeSnapshot === 'string' && (
                      <details className="mt-1 text-xs">
                        <summary className="cursor-pointer">Code shared with this request</summary>
                        <pre className="whitespace-pre-wrap break-words">{m.codeSnapshot}</pre>
                      </details>
                    )}
                  </div>
                ))}
              </div>
              <label htmlFor="playground-question" className="block text-sm font-medium mt-3">
                Ask about your code
              </label>
              <Textarea
                id="playground-question"
                maxLength={2000}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Why did this return an empty list?"
              />
              {draft.code.length > 16000 && (
                <p role="alert">
                  Tutor context supports up to 16,000 code characters. Shorten this experiment before sending.
                </p>
              )}
              <div className="flex flex-wrap gap-2 mt-2">
                <Button
                  variant="primary"
                  disabled={!sessionId || busy || !question.trim() || draft.code.length > 16000}
                  onClick={() => void ask('chat')}
                >
                  Send question
                </Button>
                {busy && <Button onClick={() => tutorAbort.current?.abort()}>Stop waiting</Button>}
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {(['hint', 'explain', 'big_picture'] as const).map((intent) => (
                  <Button
                    key={intent}
                    size="sm"
                    disabled={!sessionId || busy || draft.code.length > 16000}
                    onClick={() => void ask(intent)}
                  >
                    {{ hint: 'One hint', explain: 'Explain code', big_picture: 'Bigger picture' }[intent]}
                  </Button>
                ))}
              </div>
              {busy && (
                <p role="status" className="text-sm mt-2">
                  The tutor is reading your workspace…
                </p>
              )}
              {tutorError && (
                <p role="alert" className="text-warn mt-2">
                  {tutorError}
                </p>
              )}
              <p className="text-xs text-muted mt-3">
                {modelNote ||
                  'General coding guidance; no course sources retrieved. AI explanations can be wrong; verify them against run output.'}
              </p>
            </Card>
          </aside>
        )}
      </div>
    </>
  )
}
