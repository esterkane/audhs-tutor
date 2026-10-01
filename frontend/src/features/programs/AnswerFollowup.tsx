import {
  useFollowupRequestRecovery,
  type PendingTutorRequest,
  type FollowupRetryBody,
} from '../playground/useRequestRecovery'
import { RequestRecoveryControls } from '../playground/RequestRecoveryControls'
import { AnswerSaveStatus } from './AnswerSaveStatus'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { Markdown } from '../../components/Markdown'
import { apiFetch, type Schemas } from '../../lib/api'
import { useCurrentSession } from '../session/api'
import { ReadAloud } from '../voice/ReadAloud'
import { DictationButton } from '../voice/DictationButton'

export function AnswerFollowup({ answerId }: { answerId: string }) {
  const session = useCurrentSession()
  return (
    <section className="border border-line rounded p-4 grid gap-3" aria-label="Continue this explanation">
      <h2 className="font-semibold">Continue this explanation</h2>
      <p className="text-sm text-muted">
        Sending a question generates a new reply using the saved request, answer and available workspace
        material. Long answers may be shortened; earlier chat and original source passages are not supplied.
        No code is run or source freshly checked.
      </p>
      {session.isPending ? (
        <p role="status">Checking session…</p>
      ) : session.isError ? (
        <p role="alert">
          Could not check your session. <Button onClick={() => void session.refetch()}>Retry session</Button>
        </p>
      ) : session.data?.id ? (
        <Conversation
          key={`${answerId}:${session.data.id}`}
          answerId={answerId}
          sessionId={session.data.id}
        />
      ) : (
        <p>
          <Link to="/">Start or resume a session</Link> to ask a follow-up. This saved answer remains
          available.
        </p>
      )}
    </section>
  )
}

function Conversation({ answerId, sessionId }: { answerId: string; sessionId: string }) {
  const key = `saved-answer-followup:v1:${answerId}`
  const recovery = useFollowupRequestRecovery(`${key}:${sessionId}`)
  const [restored] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(key) ?? 'null')
      if (
        saved &&
        (typeof saved.draft !== 'string' ||
          typeof saved.parentId !== 'string' ||
          !saved.parentId ||
          saved.parentId.length > 128)
      )
        throw new Error('Invalid draft')
      return { draft: (saved?.draft ?? '').slice(0, 2000), parentId: saved?.parentId ?? answerId, error: '' }
    } catch {
      return {
        draft: '',
        parentId: answerId,
        error: 'Draft storage is unavailable. Keep a copy before leaving.',
      }
    }
  })
  const [draft, setDraft] = useState(restored.draft)
  const [storageError, setStorageError] = useState(restored.error)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [parentId, setParentId] = useState<string>(restored.parentId)
  const [replies, setReplies] = useState<Array<{ question: string; reply: Schemas['PlaygroundReply'] }>>([])
  const request = useRef<AbortController | null>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  const qc = useQueryClient()
  const parentFeedback = useQuery({
    queryKey: ['answer-feedback', parentId],
    queryFn: ({ signal }) =>
      apiFetch<Schemas['AnswerFeedbackState']>(`/api/answers/${encodeURIComponent(parentId)}/feedback`, {
        signal,
      }),
  })
  useEffect(
    () => () => {
      request.current?.abort()
      request.current = null
    },
    [],
  )
  function edit(value: string, savedParent = parentId) {
    setDraft(value.slice(0, 2000))
    try {
      localStorage.setItem(key, JSON.stringify({ draft: value.slice(0, 2000), parentId: savedParent }))
      setStorageError('')
    } catch {
      setStorageError('Draft could not be saved. Keep a copy before leaving.')
    }
  }
  function stop() {
    request.current?.abort()
    request.current = null
    setBusy(false)
    setError(
      'Stopped waiting. Your draft is kept. The server may still finish; retry the original request to check for its result.',
    )
    input.current?.focus()
  }
  async function send() {
    if (request.current || !draft.trim() || !parentFeedback.isSuccess) return
    try {
      const pending = recovery.prepare(
        { session_id: sessionId, question: draft.trim(), parent_answer_id: parentId },
        { snapshot: parentId, submitted: draft, display: draft.trim(), mode: 'explicit' },
      )
      await execute(pending)
    } catch (e) {
      setError((e as Error).message)
    }
  }
  async function execute(pending: PendingTutorRequest<FollowupRetryBody>) {
    if (request.current) return
    const { question, parent_answer_id: originalParent, session_id: originalSession } = pending.body
    const ctl = new AbortController()
    request.current = ctl
    setBusy(true)
    setError('')
    const timer = setTimeout(() => {
      if (request.current === ctl) stop()
    }, 120_000)
    try {
      const reply = await apiFetch<Schemas['PlaygroundReply']>(
        `/api/answers/${encodeURIComponent(originalParent)}/followup`,
        {
          method: 'POST',
          body: JSON.stringify({ session_id: originalSession, question }),
          signal: ctl.signal,
          headers: { 'Idempotency-Key': pending.key },
        },
      )
      if (request.current !== ctl || ctl.signal.aborted) return
      setReplies((old) => [...old, { question, reply }])
      if (reply.answer_id) {
        setParentId(reply.answer_id)
        void qc.invalidateQueries({ queryKey: ['answers'] })
      }
      edit(draft === pending.view.submitted ? '' : draft, reply.answer_id ?? originalParent)
      recovery.accept(pending.key)
      input.current?.focus()
    } catch (e) {
      if (request.current === ctl && !ctl.signal.aborted)
        setError(
          `${(e as Error).message} Your draft is kept. Retry the previous request to check for its original result.`,
        )
    } finally {
      clearTimeout(timer)
      if (request.current === ctl) {
        request.current = null
        setBusy(false)
      }
    }
  }
  const unsaved = replies.some(({ reply }) => !reply.answer_id)
  return (
    <div className="grid gap-3">
      {parentId !== answerId && (
        <p className="text-sm">
          Continuing from your{' '}
          <Link className="underline" to={`/answers/${encodeURIComponent(parentId)}`}>
            latest saved follow-up
          </Link>
          .
        </p>
      )}
      {parentFeedback.isPending && <p role="status">Checking feedback for the reply you will continue…</p>}
      {parentFeedback.isError && (
        <p role="alert">
          Could not check feedback for this reply.{' '}
          <Button onClick={() => void parentFeedback.refetch()}>Retry continuation feedback</Button>
        </p>
      )}
      {(parentFeedback.data?.verdict === 'incorrect' || parentFeedback.data?.verdict === 'outdated') && (
        <p role="alert">
          The reply you will continue from is marked {parentFeedback.data.verdict}. Your report will be
          included with the follow-up.
        </p>
      )}
      {replies.map(({ question, reply }, index) => (
        <div key={index} className="border-t border-line pt-3">
          <h3 className="font-medium">Your follow-up</h3>
          <p className="whitespace-pre-wrap">{question}</p>
          <Markdown text={reply.text} />
          <ReadAloud text={`Your question: ${question}\n\n${reply.text}`} />
          <AnswerSaveStatus
            answerId={reply.answer_id}
            receipt={reply.save_receipt}
            error={
              reply.save_error ||
              (!reply.answer_id ? 'This reply was not saved. Keep a copy before leaving.' : null)
            }
            text={reply.text}
            linkLabel="Open saved follow-up"
            onSaved={(id) => {
              setReplies((old) =>
                old.map((entry) =>
                  entry.reply.turn_id === reply.turn_id
                    ? {
                        ...entry,
                        reply: { ...entry.reply, answer_id: id, save_error: null, save_receipt: null },
                      }
                    : entry,
                ),
              )
              setParentId(id)
              edit(draft, id)
            }}
          />
        </div>
      ))}
      {unsaved && (
        <p role="alert">
          Save failed for the latest reply. Keep a copy; further follow-ups are paused so they do not silently
          lose that context.
        </p>
      )}
      <label>
        Your follow-up question
        <textarea
          ref={input}
          className="block w-full border border-line rounded p-2 bg-card"
          rows={3}
          maxLength={2000}
          value={draft}
          disabled={busy || unsaved}
          onChange={(event) => edit(event.target.value)}
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <Button
          onClick={() => void send()}
          disabled={busy || unsaved || !draft.trim() || !parentFeedback.isSuccess}
        >
          Send follow-up
        </Button>
        <DictationButton
          disabled={busy || unsaved}
          onTranscript={(text) => edit([draft, text].filter(Boolean).join(' '))}
        />
        {busy && <Button onClick={stop}>Stop</Button>}
      </div>
      {busy && <p role="status">Preparing a follow-up…</p>}
      <RequestRecoveryControls
        originalContext="parent answer and question"
        recovery={recovery}
        busy={busy}
        retry={() => {
          if (recovery.pending) void execute(recovery.pending)
        }}
      />
      {error && <p role="alert">{error}</p>}
      {storageError && <p role="alert">{storageError}</p>}
    </div>
  )
}
