import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Markdown } from '../../components/Markdown'
import { Button } from '../../components/ui/button'
import { askTutor, type TutorReply, type TutorRequest } from '../playground/api'
import { useCurrentSession } from '../session/api'
import { ReadAloud } from '../voice/ReadAloud'
import { DictationButton } from '../voice/DictationButton'

type Props = {
  targetLabel?: string
  reviewOnly?: boolean
  context: string
  identity?: string
  code?: string
  answer?: string
  output?: string
}
type Action = 'explain' | 'hint' | 'socratic' | 'review' | 'chat'
export function StudyTutor(props: Props) {
  const session = useCurrentSession()
  return (
    <section aria-label="Study tutor" className="border border-border rounded-lg p-4 mt-4">
      <h3 className="font-semibold">{props.reviewOnly ? 'Answer feedback' : 'Study tutor'}</h3>
      {props.targetLabel && <p className="font-medium mt-2">Discussing: {props.targetLabel}</p>}
      {!props.reviewOnly && <p>Start with an explanation, then try one step. Questions are optional.</p>}
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
  reviewOnly = false,
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
      conversation: [] as NonNullable<TutorRequest['history']>,
      replySnapshot: '',
      error: '',
      mode: 'explain' as 'explain' | 'socratic',
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
        conversation: (Array.isArray(value.conversation) &&
        value.conversation.every(
          (m: { role?: unknown; text?: unknown }) =>
            ['user', 'assistant'].includes(String(m?.role)) && typeof m?.text === 'string',
        )
          ? value.conversation
          : value.history
        )
          .slice(-40)
          .map((m: { role: 'user' | 'assistant'; text: string }) => ({
            role: m.role,
            text: m.text.slice(0, 4000),
          })),
        replySnapshot: value.replySnapshot,
        mode: value.mode === 'socratic' ? ('socratic' as const) : ('explain' as const),
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
  const [conversation, setConversation] = useState<NonNullable<TutorRequest['history']>>(
    restored.conversation,
  )
  const [replySnapshot, setReplySnapshot] = useState<string>(restored.replySnapshot)
  const [mode, setMode] = useState<'explain' | 'socratic'>(restored.mode)
  const messageInput = useRef<HTMLTextAreaElement>(null)
  const socratic = mode === 'socratic' && replySnapshot === snapshot
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
      localStorage.setItem(
        storageKey,
        JSON.stringify({ question, reply, history, conversation, replySnapshot, mode }),
      )
    } catch {
      // Storage is external state: surface a failed write without losing the in-memory draft.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStorageError('Tutor conversation could not be saved. Copy your message before leaving.')
    }
  }, [storageKey, question, reply, history, conversation, replySnapshot, mode])
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
    if (
      operation.current ||
      (action === 'review' && !answer.trim()) ||
      (action === 'chat' && !question.trim())
    )
      return
    if (action === 'chat' && socratic && question.length > 1700) {
      setError('Please shorten this reply to 1,700 characters so the tutor receives your complete answer.')
      return
    }
    const requests = {
      explain:
        'Explain the supplied material before asking questions. Switch back to direct explanation if we were using Socratic questions. Give a small worked example, why each step matters, and one concrete next action.',
      hint: socratic
        ? 'Give one small hint for your last question. Do not replace it with another question or reveal the solution.'
        : 'Give one small hint for the supplied task without revealing the solution.',
      socratic:
        'I explicitly choose Socratic questioning for this turn. Ask just one focused question about the supplied material, with enough context to answer. Wait for my response.',
      review:
        'Check the learner answer against the supplied question and criteria. Give formative feedback under: What is correct, What needs revision or is missing, and One next step. Explain why, and distinguish an incorrect claim from an incomplete answer. If the evidence is insufficient, say so. Do not claim code execution, an official grade, mastery, or course completion. Do not give a full replacement answer unless requested.',
      chat: socratic
        ? `My answer to your last question: ${question.trim()}\nGive direct feedback on my answer first and explain any gap. Then ask at most one focused follow-up question with enough context. Do not restart the exercise.`
        : question.trim(),
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
      setMode(
        action === 'socratic' || (socratic && (action === 'chat' || action === 'hint'))
          ? 'socratic'
          : 'explain',
      )
      setHistory((old) =>
        [
          ...(replySnapshot === snapshot ? old : []),
          { role: 'user' as const, text: requests[action].slice(0, 4000) },
          { role: 'assistant' as const, text: next.text.slice(0, 4000) },
        ].slice(-6),
      )
      setConversation((old) =>
        [
          ...old,
          { role: 'user' as const, text: action === 'chat' ? submitted : displayMessage(requests[action]) },
          { role: 'assistant' as const, text: next.text.slice(0, 4000) },
        ].slice(-40),
      )
      if (action === 'chat') setQuestion((current) => (current === submitted ? '' : current))
      requestAnimationFrame(() => messageInput.current?.focus())
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
        {!reviewOnly && (
          <>
            <Button disabled={busy} onClick={() => void ask('explain')}>
              {socratic ? 'Explain instead' : 'Explain this step'}
            </Button>
            <Button disabled={busy} onClick={() => void ask('hint')}>
              Tutor: one hint
            </Button>
            <Button disabled={busy || socratic} onClick={() => void ask('socratic')}>
              Ask me a Socratic question
            </Button>
          </>
        )}
        <Button disabled={busy || !answer.trim()} onClick={() => void ask('review')}>
          {reviewOnly ? 'Check my answer' : 'Review my answer'}
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
      {reply && (
        <div className="mt-3 grid gap-3" aria-label="Tutor conversation">
          {conversation.length > 2 && (
            <details>
              <summary>Earlier messages ({conversation.length - 2})</summary>
              <ol className="grid gap-3 mt-2">
                {conversation.slice(0, -2).map((message, index) => (
                  <li key={index} className="border-l-2 border-border pl-3">
                    <p className="font-semibold">{message.role === 'user' ? 'You' : 'Tutor'}</p>
                    <Markdown text={displayMessage(message.text)} />
                  </li>
                ))}
              </ol>
              <p className="text-xs text-muted">
                Up to 20 exchanges are saved here; older responses may be shortened or refer to earlier edits.
                The tutor receives the latest three exchanges for the current work.
              </p>
            </details>
          )}
          {conversation.at(-2)?.role === 'user' && (
            <div>
              <p className="font-semibold">You</p>
              <Markdown text={displayMessage(conversation.at(-2)!.text)} />
            </div>
          )}
          <div aria-label="Tutor response">
            <p className="font-semibold">Tutor</p>
            <p className="text-sm">
              {replySnapshot !== snapshot
                ? 'Earlier feedback: your code, answer or output has changed. Ask again to review your current work.'
                : socratic
                  ? 'Your turn: answer this question below, or choose Explain instead.'
                  : 'You can ask a follow-up below.'}
            </p>
            <Markdown text={reply.text} />
            <ReadAloud
              text={reply.text}
              label={reviewOnly ? 'Listen to feedback' : 'Listen to tutor response'}
            />
            <details className="text-xs text-muted">
              <summary>Response details</summary>
              {reply.model} · {reply.route}. {reply.source_note}
            </details>
          </div>
        </div>
      )}
      {socratic && (
        <p className="mt-3">
          Guided questions: one question at a time. After you reply, the tutor discusses your reasoning before
          continuing.
        </p>
      )}
      {(!reviewOnly || reply) && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            void ask('chat')
          }}
          className="mt-3"
        >
          <label htmlFor={id}>
            {socratic
              ? 'Your answer to the tutor’s question'
              : reviewOnly
                ? 'Ask about this feedback'
                : 'Your tutor message or response'}
          </label>
          <textarea
            ref={messageInput}
            id={id}
            value={question}
            maxLength={socratic ? 1700 : 2000}
            onChange={(event) => setQuestion(event.target.value)}
            rows={3}
            className="block w-full border rounded p-2 bg-surface"
          />
          <DictationButton
            disabled={busy}
            onTranscript={(text) => setQuestion((old) => `${old}${old ? '\n' : ''}${text}`.slice(0, 2000))}
          />
          <Button type="submit" disabled={busy || !question.trim()}>
            {socratic ? 'Discuss my answer' : reviewOnly ? 'Send follow-up' : 'Send to tutor'}
          </Button>
          {busy && (
            <Button type="button" onClick={stop}>
              Stop tutor response
            </Button>
          )}
        </form>
      )}
      {reviewOnly && busy && !reply && <Button onClick={stop}>Stop answer check</Button>}
      {reviewOnly && !answer.trim() && <p>Write your explanation above, then check it for feedback.</p>}
      {busy && <p role="status">Tutor is preparing a response…</p>}
      {error && <p role="alert">{error}</p>}
      {storageError && <p role="alert">{storageError}</p>}
    </>
  )
}

function displayMessage(text: string): string {
  if (text.startsWith('Explain the supplied material')) return 'Explain this step.'
  if (text.startsWith('Give one small hint')) return 'Give me one hint.'
  if (text.startsWith('I explicitly choose Socratic')) return 'Ask me one guided question about this step.'
  if (text.startsWith('Check the learner answer')) return 'Check my answer.'
  if (text.startsWith('My answer to your last question: '))
    return text
      .slice('My answer to your last question: '.length)
      .split('\nGive direct feedback on my answer first')[0]
  return text
}
