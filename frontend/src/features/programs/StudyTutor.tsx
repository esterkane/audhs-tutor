import { useRequestRecovery, type PendingTutorRequest } from '../playground/useRequestRecovery'
import { RequestRecoveryControls } from '../playground/RequestRecoveryControls'
import { AnswerSaveStatus } from './AnswerSaveStatus'
import { GroupCounts } from './GroupCounts'
import { useQueryClient } from '@tanstack/react-query'
import { SavedContextAnswers } from './SavedContextAnswers'
import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Markdown } from '../../components/Markdown'
import { Button } from '../../components/ui/button'
import { askTutor, type TutorReply, type TutorRequest } from '../playground/api'
import { useCurrentSession } from '../session/api'
import { ReadAloud } from '../voice/ReadAloud'
import { DictationButton } from '../voice/DictationButton'
import { TutorResponseStatus } from '../tutor/TutorResponseStatus'

type Props = {
  courseId?: string
  sectionId?: string
  targetLabel?: string
  reviewOnly?: boolean
  context: string
  identity?: string
  code?: string
  checkCode?: string
  answer?: string
  output?: string
}
type Action = 'explain' | 'hint' | 'socratic' | 'review' | 'chat' | 'shorter' | 'steps' | 'example' | 'bins'
export function StudyTutor(props: Props) {
  const session = useCurrentSession()
  return (
    <section aria-label="Study tutor" className="border border-line rounded-lg p-4 mt-4">
      <h3 className="font-semibold">{props.reviewOnly ? 'Answer feedback' : 'Study tutor'}</h3>
      {props.identity && (
        <SavedContextAnswers
          key={JSON.stringify([props.courseId, props.sectionId, props.identity])}
          courseId={props.courseId}
          sectionId={props.sectionId}
          targetId={props.identity}
        />
      )}
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
  courseId,
  sectionId,
  targetLabel,
  reviewOnly = false,
  identity,
  code = '',
  checkCode = code,
  answer = '',
  output = '',
  sessionId,
}: Props & { sessionId: string }) {
  const queryClient = useQueryClient()
  const storageKey = `study-tutor:v1:${sessionId}:${identity ?? context}`
  const snapshot = JSON.stringify([context, code, answer, output, checkCode])
  const recovery = useRequestRecovery(storageKey)
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
  const [preferSaved, setPreferSaved] = useState(false)
  const [startedAt, setStartedAt] = useState(0)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')
  const operation = useRef<AbortController | null>(null)
  const focusGeneration = useRef(0)
  useEffect(
    () => () => {
      focusGeneration.current++
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
    focusGeneration.current++
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
    focusGeneration.current++
    operation.current?.abort()
    operation.current = null
    setBusy(false)
    setError(
      'Stopped. Your message is retained. Retry the original request, or discard its retry before sending changed work.',
    )
  }
  async function ask(action: Action) {
    if (
      operation.current ||
      (['shorter', 'steps', 'example'].includes(action) &&
        (!reply || replySnapshot !== snapshot || socratic)) ||
      (action === 'review' && !answer.trim()) ||
      (action === 'chat' && !question.trim())
    )
      return
    if (action === 'chat' && socratic && question.length > 1700) {
      setError('Please shorten this reply to 1,700 characters so the tutor receives your complete answer.')
      return
    }
    if (action === 'review' && context.length > 8000) {
      setError(
        'This step has more than 8,000 characters of material. Select a smaller step before checking your answer so no question or criteria are omitted. Your answer is retained.',
      )
      return
    }
    if (action === 'bins' && checkCode.length > 16000) {
      setError(
        'Select a code cell of at most 16,000 characters for a complete local boundary check. Your work is retained.',
      )
      return
    }
    const learnerAnswer =
      action === 'bins'
        ? null
        : action === 'chat' && socratic
          ? question
          : action === 'socratic' || (action === 'hint' && socratic)
            ? null
            : answer || null
    if (learnerAnswer && learnerAnswer.length > 8000) {
      setError(
        'Please shorten your task answer to 8,000 characters so the tutor receives it in full. Your work is retained.',
      )
      return
    }
    const requests = {
      bins: 'Check bin boundaries in the supplied code locally, without executing it or grading my written answer.',
      shorter:
        'Make your last response shorter while preserving its key reasoning, uncertainty and source limitations. Explicitly retain any missing-data or unverified-output caveat; do not introduce a new judgment of my answer. Stay on this same step; do not introduce a new question or claim new checks.',
      steps:
        'Break your last response into smaller numbered steps. Explain why each step matters and identify the first action I can try. Stay on the same task; do not claim code execution or new checks.',
      example:
        'Show one small worked example that clarifies your last response on this same step. Label invented numbers or scenarios as illustrative, not facts from the source. Prefer a tiny concrete example in plain language; include code only if I requested code. Check that totals, rates and conclusions agree. Connect it back to the task without claiming execution or new checks.',
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
    try {
      const pending = recovery.prepare(
        {
          session_id: sessionId,
          prefer_saved: preferSaved,
          questioning_style:
            action === 'socratic' || (socratic && (action === 'chat' || action === 'hint'))
              ? 'socratic'
              : 'explicit',
          learning_context: {
            course_id: courseId,
            section_id: sectionId,
            target_id: identity,
            target_label: targetLabel?.slice(0, 300),
          },
          learner_question: action === 'chat' ? question.trim().slice(0, 2000) : null,
          intent:
            action === 'bins'
              ? 'check_bins'
              : action === 'review'
                ? 'check_answer'
                : action === 'hint'
                  ? 'hint'
                  : action === 'explain'
                    ? 'explain'
                    : 'chat',
          question: requests[action].slice(0, 2000),
          exercise: action === 'review' ? context : context.slice(0, 1000),
          code: action === 'bins' ? checkCode : code.slice(0, 16000),
          learner_answer: learnerAnswer,
          output: output.slice(0, 4000),
          output_stale: false,
          history: replySnapshot === snapshot ? history.slice(-6) : [],
        },
        {
          snapshot,
          submitted: action === 'chat' ? question : '',
          display: action === 'chat' ? question : displayMessage(requests[action]),
          mode:
            action === 'socratic' || (socratic && (action === 'chat' || action === 'hint'))
              ? 'socratic'
              : 'explicit',
        },
      )
      await execute(pending)
    } catch (e) {
      setError((e as Error).message)
    }
  }
  async function execute(pending: PendingTutorRequest) {
    if (operation.current) return
    const ctl = new AbortController()
    const ownFocusGeneration = ++focusGeneration.current
    const requestFocus = document.activeElement
    operation.current = ctl
    setStartedAt(performance.now())
    setReady(false)
    setBusy(true)
    setError('')
    const timer = setTimeout(() => {
      if (operation.current === ctl) {
        ctl.abort()
        operation.current = null
        setBusy(false)
        setError('The tutor took too long. Your message is retained; try again.')
      }
    }, 90000)
    try {
      const next = await askTutor(pending.body, ctl.signal, pending.key)
      if (operation.current !== ctl || ctl.signal.aborted) return
      if (next.answer_id) void queryClient.invalidateQueries({ queryKey: ['answers'] })
      setReply(next)
      setReady(true)
      setReplySnapshot(pending.view.snapshot)
      setMode(pending.view.mode === 'socratic' ? 'socratic' : 'explain')
      setHistory(
        [
          ...(pending.body.history ?? []),
          { role: 'user' as const, text: (pending.body.question ?? '').slice(0, 4000) },
          { role: 'assistant' as const, text: next.text.slice(0, 4000) },
        ].slice(-6),
      )
      setConversation((old) =>
        [
          ...old,
          { role: 'user' as const, text: pending.view.display },
          { role: 'assistant' as const, text: next.text.slice(0, 4000) },
        ].slice(-40),
      )
      if (pending.view.submitted)
        setQuestion((current) => (current === pending.view.submitted ? '' : current))
      recovery.accept(pending.key)
      requestAnimationFrame(() => {
        // Disabling the sending button can return focus to body. Never replace another control's focus.
        if (
          focusGeneration.current === ownFocusGeneration &&
          (document.activeElement === requestFocus || document.activeElement === document.body)
        )
          messageInput.current?.focus()
      })
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
      {!reviewOnly && (
        <p className="text-sm mt-2">
          {socratic
            ? 'Guided questions: reply below, or switch back to an explanation.'
            : 'Explanation mode: ask about this step or describe where you are stuck.'}
        </p>
      )}
      <div className="flex flex-wrap gap-2 mt-3">
        {!reviewOnly && (
          <>
            <Button
              variant={socratic ? 'outline' : 'primary'}
              disabled={busy}
              onClick={() => void ask('explain')}
            >
              {socratic ? 'Explain instead' : 'Explain this step'}
            </Button>
            <Button disabled={busy} onClick={() => void ask('hint')}>
              Tutor: one hint
            </Button>
          </>
        )}
        {(reviewOnly || answer.trim()) && (
          <Button
            variant={reviewOnly ? 'primary' : 'secondary'}
            disabled={busy || !answer.trim()}
            onClick={() => void ask('review')}
          >
            {reviewOnly ? 'Check my answer' : 'Review my answer'}
          </Button>
        )}
      </div>
      {checkCode.trim() && (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm">Local code checks</summary>
          <p className="text-sm my-2">
            Check literal pandas.cut bin edges without a model or code execution. This does not grade your
            written answer or test your dataset. Unsupported code stays unchanged.
          </p>
          <Button disabled={busy} onClick={() => void ask('bins')}>
            Check bin boundaries
          </Button>
        </details>
      )}
      <details className="mt-3">
        <summary className="cursor-pointer text-sm">Compare group counts locally</summary>
        <GroupCounts key={storageKey} storageKey={`${storageKey}:group-counts`} />
      </details>
      <TutorResponseStatus
        status={busy ? 'streaming' : ready && replySnapshot === snapshot ? 'complete' : 'idle'}
        startedAt={startedAt}
      />
      {busy && (
        <div className="my-2">
          <Button type="button" onClick={stop}>
            {reviewOnly && !reply ? 'Stop answer check' : 'Stop tutor response'}
          </Button>
        </div>
      )}
      <p className="text-sm text-muted mt-2">
        Tutor feedback is guidance, not a verified grade. Answer checks send your work and study context to
        the selected feedback model (OpenAI by default). <Link to="/models">Choose models</Link>
      </p>
      <details className="text-sm text-muted mt-2">
        <summary>What is sent to the tutor?</summary>
        <p>
          Answer checks include your submitted answer, supplied material, code, output, recent conversation
          and relevant saved replies. Other tutor actions keep their existing models. Check bin boundaries
          runs locally without a model.
        </p>
        <p>
          Answer checks include the complete step material up to 8,000 characters; longer steps must be
          narrowed. Other tutor actions use the first 1,000 characters of material. Code is limited to 16,000
          characters and run output to 4,000. Task answers are sent in full, up to 8,000 characters.
        </p>
      </details>
      {reply && (
        <div className="mt-3 grid gap-3" aria-label="Tutor conversation">
          {conversation.length > 2 && (
            <details>
              <summary>Earlier messages ({conversation.length - 2})</summary>
              <ol className="grid gap-3 mt-2">
                {conversation.slice(0, -2).map((message, index) => (
                  <li key={index} className="border-l-2 border-line pl-3">
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
            {reply.reused && (
              <p role="status">
                Saved answer from {reply.saved_at}. To generate fresh, turn off saved-answer reuse and ask
                again.
              </p>
            )}
            <Markdown text={reply.text} />
            {!socratic && replySnapshot === snapshot && (
              <div role="group" aria-label="Adapt this explanation" className="flex flex-wrap gap-2 my-3">
                <Button disabled={busy} onClick={() => void ask('shorter')}>
                  Shorter
                </Button>
                <Button disabled={busy} onClick={() => void ask('steps')}>
                  Smaller steps
                </Button>
                <Button disabled={busy} onClick={() => void ask('example')}>
                  Show an example
                </Button>
              </div>
            )}
            <ReadAloud
              text={reply.text}
              label={reviewOnly ? 'Listen to feedback' : 'Listen to tutor response'}
            />
            <p className="text-sm text-muted">{reply.source_note}</p>
            {reply.memory_answers?.length ? (
              <ul aria-label="Previous answers used">
                {reply.memory_answers.map((id) => (
                  <li key={id}>
                    <Link to={`/answers/${id}`}>Open previous answer</Link>
                  </li>
                ))}
              </ul>
            ) : null}
            <AnswerSaveStatus
              key={reply.turn_id}
              answerId={reply.answer_id}
              receipt={reply.save_receipt}
              error={reply.save_error}
              text={reply.text}
              onSaved={(id) =>
                setReply((current) =>
                  current?.turn_id === reply.turn_id
                    ? { ...current, answer_id: id, save_error: null, save_receipt: null }
                    : current,
                )
              }
            />
            <details className="text-xs text-muted">
              <summary>Response details</summary>
              {reply.model} · {reply.route}.
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
            className="block w-full border rounded p-2 bg-card"
          />
          <DictationButton
            disabled={busy}
            onTranscript={(text) => setQuestion((old) => `${old}${old ? '\n' : ''}${text}`.slice(0, 2000))}
          />
          <Button type="submit" disabled={busy || !question.trim()}>
            {socratic ? 'Discuss my answer' : reviewOnly ? 'Send follow-up' : 'Send to tutor'}
          </Button>
        </form>
      )}
      {reviewOnly && !answer.trim() && <p>Write your explanation above, then check it for feedback.</p>}
      {!reviewOnly && !socratic && (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm">Practice with a guided question (optional)</summary>
          <p className="text-sm my-2">
            The tutor asks one question about this step. Reply in the same chat to discuss your reasoning. You
            can choose Explain instead at any time.
          </p>
          <Button disabled={busy} onClick={() => void ask('socratic')}>
            Ask me a Socratic question
          </Button>
        </details>
      )}
      <details className="mt-3">
        <summary className="cursor-pointer text-sm">
          Saved-answer reuse options{preferSaved ? ' · on' : ' · off'}
        </summary>
        <label className="flex gap-2 items-center text-sm my-2">
          <input
            type="checkbox"
            checked={preferSaved}
            disabled={busy}
            onChange={(event) => setPreferSaved(event.target.checked)}
          />
          Use a saved answer when this request matches (no new model call)
        </label>
      </details>
      <RequestRecoveryControls
        recovery={recovery}
        busy={busy}
        retry={() => {
          if (recovery.pending) void execute(recovery.pending)
        }}
      />
      {error && <p role="alert">{error}</p>}
      {storageError && <p role="alert">{storageError}</p>}
    </>
  )
}

function displayMessage(text: string): string {
  if (text.startsWith('Check bin boundaries in the supplied code')) return 'Check bin boundaries locally.'
  if (text.startsWith('Make your last response shorter')) return 'Make this explanation shorter.'
  if (text.startsWith('Break your last response')) return 'Explain this in smaller steps.'
  if (text.startsWith('Show one small worked example')) return 'Show me a worked example.'
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
