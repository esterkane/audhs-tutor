import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Markdown } from '../../components/Markdown'
import { Button } from '../../components/ui/button'
import { askTutor, type TutorReply, type TutorRequest } from '../playground/api'
import { useCurrentSession } from '../session/api'
import { ReadAloud } from '../voice/ReadAloud'
import { DictationButton } from '../voice/DictationButton'

type Props = { context: string; identity?: string; code?: string; answer?: string; output?: string }
type Action = 'explain' | 'hint' | 'socratic' | 'review' | 'chat'
export function StudyTutor(props: Props) {
  const session = useCurrentSession()
  return (
    <section aria-label="Study tutor" className="border border-border rounded-lg p-4 mt-4">
      <h3 className="font-semibold">Study tutor</h3>
      <p>Start with an explanation, then try one step. Questions are optional.</p>
      {session.isPending ? (
        <p role="status">Checking tutor session…</p>
      ) : session.isError ? (
        <p role="alert">
          Cannot check your session.{' '}
          <Button onClick={() => void session.refetch()}>Retry session check</Button>
        </p>
      ) : session.data?.id ? (
        <Conversation
          key={`${session.data.id}:${props.identity ?? props.context}`}
          {...props}
          sessionId={session.data.id}
        />
      ) : (
        <p>
          <Link to="/">Start or resume a session from Home</Link> to use the tutor here. Your material remains
          available.
        </p>
      )}
    </section>
  )
}
function Conversation({
  context,
  identity,
  code = '',
  answer = '',
  output = '',
  sessionId,
}: Props & { sessionId: string }) {
  const storageKey = `study-tutor:v1:${sessionId}:${identity ?? context}`
  const snapshot = JSON.stringify([context, code, answer, output])
  const workspaceOutput =
    `Learner answer (not execution output):\n${answer.slice(0, 1950)}\n\nActual run output (not verified by tutor):\n${output.slice(0, 1950)}`.slice(
      0,
      4000,
    )
  const [restored] = useState(() => {
    const fresh = {
      question: '',
      reply: null as TutorReply | null,
      history: [] as NonNullable<TutorRequest['history']>,
      replySnapshot: '',
      error: '',
    }
    try {
      const raw = localStorage.getItem(storageKey)
      if (!raw) return fresh
      const value = JSON.parse(raw)
      if (
        typeof value.question !== 'string' ||
        typeof value.replySnapshot !== 'string' ||
        !Array.isArray(value.history) ||
        !value.history.every(
          (m: { role?: unknown; text?: unknown }) =>
            ['user', 'assistant'].includes(String(m?.role)) && typeof m?.text === 'string',
        )
      )
        throw new Error('Invalid saved conversation')
      if (
        value.reply !== null &&
        (!value.reply ||
          !['text', 'model', 'route', 'turn_id', 'source_note'].every(
            (k) => typeof value.reply[k] === 'string',
          ))
      )
        throw new Error('Invalid saved reply')
      return {
        ...fresh,
        question: value.question.slice(0, 2000),
        reply: value.reply as TutorReply | null,
        history: value.history
          .slice(-6)
          .map((m: { role: 'user' | 'assistant'; text: string }) => ({ ...m, text: m.text.slice(0, 4000) })),
        replySnapshot: value.replySnapshot,
      }
    } catch {
      return {
        ...fresh,
        error: 'Saved tutor conversation could not be restored. Keep a copy before leaving.',
      }
    }
  })
  const id = useId()
  const [question, setQuestion] = useState<string>(restored.question)
  const [reply, setReply] = useState<TutorReply | null>(restored.reply)
  const [history, setHistory] = useState<NonNullable<TutorRequest['history']>>(restored.history)
  const [replySnapshot, setReplySnapshot] = useState<string>(restored.replySnapshot)
  const [storageError, setStorageError] = useState(restored.error)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const operation = useRef<AbortController | null>(null)
  useEffect(
    () => () => {
      operation.current?.abort()
      operation.current = null
    },
    [],
  )
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify({ question, reply, history, replySnapshot }))
    } catch {
      // Storage is external state: surface a failed write without losing the in-memory draft.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStorageError('Tutor conversation could not be saved. Copy your message before leaving.')
    }
  }, [storageKey, question, reply, history, replySnapshot])
  useEffect(() => {
    if (operation.current) {
      operation.current.abort()
      operation.current = null
      setBusy(false)
      setError(
        'Your code, answer or output changed. The previous request was stopped; ask again for current feedback.',
      )
    }
  }, [snapshot])
  function stop() {
    operation.current?.abort()
    operation.current = null
    setBusy(false)
    setError('Stopped. Your message is retained; edit or retry it.')
  }
  async function ask(action: Action) {
    if (operation.current || (action === 'review' && !answer.trim())) return
    const requests = {
      explain:
        'Explain the supplied material before asking questions. Give a small worked example, why each step matters, and one concrete next action.',
      hint: 'Give one small hint for the supplied task without revealing the solution.',
      socratic:
        'I explicitly choose Socratic questioning for this turn. Ask just one focused question about the supplied material, with enough context to answer. Wait for my response.',
      review:
        'Review my answer in workspace output as formative feedback. Identify what is supported, what needs revision and one concrete next step. Do not claim verified correctness, code execution, grades or mastery.',
      chat: question.trim(),
    }
    if (!requests[action]) return
    const ctl = new AbortController()
    operation.current = ctl
    setBusy(true)
    setError('')
    const submitted = question
    const timer = setTimeout(() => {
      if (operation.current === ctl) {
        ctl.abort()
        operation.current = null
        setBusy(false)
        setError('The tutor took too long. Your message is retained; try again.')
      }
    }, 90000)
    try {
      const next = await askTutor(
        {
          session_id: sessionId,
          intent: action === 'hint' ? 'hint' : action === 'explain' ? 'explain' : 'chat',
          question: requests[action].slice(0, 2000),
          exercise: context.slice(0, 1000),
          code: code.slice(0, 16000),
          output: workspaceOutput,
          output_stale: false,
          history: replySnapshot === snapshot ? history.slice(-6) : [],
        },
        ctl.signal,
      )
      if (operation.current !== ctl || ctl.signal.aborted) return
      setReply(next)
      setReplySnapshot(snapshot)
      setHistory((old) =>
        [
          ...(replySnapshot === snapshot ? old : []),
          { role: 'user' as const, text: requests[action].slice(0, 4000) },
          { role: 'assistant' as const, text: next.text.slice(0, 4000) },
        ].slice(-6),
      )
      if (action === 'chat') setQuestion((current) => (current === submitted ? '' : current))
    } catch (e) {
      if (operation.current === ctl && !ctl.signal.aborted)
        setError(`${(e as Error).message} Your message is retained.`)
    } finally {
      clearTimeout(timer)
      if (operation.current === ctl) {
        operation.current = null
        setBusy(false)
      }
    }
  }
  return (
    <>
      <div className="flex flex-wrap gap-2 mt-3">
        <Button disabled={busy} onClick={() => void ask('explain')}>
          Explain this step
        </Button>
        <Button disabled={busy} onClick={() => void ask('hint')}>
          Tutor: one hint
        </Button>
        <Button disabled={busy} onClick={() => void ask('socratic')}>
          Ask me a Socratic question
        </Button>
        <Button disabled={busy || !answer.trim()} onClick={() => void ask('review')}>
          Review my answer
        </Button>
      </div>
      <p className="text-xs text-muted mt-2">
        Feedback is guidance, not a verified grade. Uses your configured explanation/hint model; this does not
        change routing.
      </p>
      {(context.length > 1000 || code.length > 16000 || answer.length > 1950 || output.length > 1950) && (
        <p role="status">
          Only the first 1,000 characters of material, 16,000 of code, 1,950 of your answer and 1,950 of run
          output fit this tutor request. Focus on one smaller step for complete feedback.
        </p>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault()
          void ask('chat')
        }}
        className="mt-3"
      >
        <label htmlFor={id}>Your tutor message or response</label>
        <textarea
          id={id}
          value={question}
          maxLength={2000}
          onChange={(event) => setQuestion(event.target.value)}
          rows={3}
          className="block w-full border rounded p-2 bg-surface"
        />
        <DictationButton
          disabled={busy}
          onTranscript={(text) => setQuestion((old) => `${old}${old ? '\n' : ''}${text}`.slice(0, 2000))}
        />
        <Button type="submit" disabled={busy || !question.trim()}>
          Send to tutor
        </Button>
        {busy && (
          <Button type="button" onClick={stop}>
            Stop tutor response
          </Button>
        )}
      </form>
      {busy && <p role="status">Tutor is preparing a response…</p>}
      {error && <p role="alert">{error}</p>}
      {storageError && <p role="alert">{storageError}</p>}
      {reply && (
        <div className="mt-3" aria-label="Tutor response">
          <p className="text-sm">
            {replySnapshot !== snapshot
              ? 'Earlier feedback: your code, answer or output has changed. Ask again to review your current work.'
              : 'Feedback on the work you sent.'}
          </p>
          <Markdown text={reply.text} />
          <ReadAloud text={reply.text} />
          <p className="text-xs text-muted">
            {reply.model} · {reply.route}. {reply.source_note}
          </p>
        </div>
      )}
    </>
  )
}
