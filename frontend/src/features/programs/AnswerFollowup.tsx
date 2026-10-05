import {
  useFollowupRequestRecovery,
  type PendingTutorRequest,
  type FollowupRetryBody,
} from '../playground/useRequestRecovery'
import { streamAnswerFollowup } from '../playground/streamTutor'
import { readTextCache, writeTextCache } from '../tutor/streamCache'
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

export function AnswerFollowup({
  answerId,
  expectedSessionId,
  active = true,
}: {
  answerId: string
  expectedSessionId?: string
  active?: boolean
}) {
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
      ) : expectedSessionId && session.data?.id !== expectedSessionId ? (
        <p role="status">
          This activity is no longer the current session. <Link to="/">Return Home</Link> to resume it. Your
          saved feedback and discussion draft remain available.
        </p>
      ) : session.data?.id ? (
        <Conversation
          key={`${answerId}:${session.data.id}`}
          answerId={answerId}
          sessionId={session.data.id}
          active={active}
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

function Conversation({
  answerId,
  sessionId,
  active,
}: {
  answerId: string
  sessionId: string
  active: boolean
}) {
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
          saved.parentId.length > 128 ||
          (saved.purpose !== undefined && !['followup', 'correction'].includes(saved.purpose)))
      )
        throw new Error('Invalid draft')
      return {
        draft: (saved?.draft ?? '').slice(0, 2000),
        parentId: saved?.parentId ?? answerId,
        purpose: (saved?.purpose ?? 'followup') as 'followup' | 'correction',
        error: '',
      }
    } catch {
      return {
        draft: '',
        purpose: 'followup' as const,
        parentId: answerId,
        error: 'Draft storage is unavailable. Keep a copy before leaving.',
      }
    }
  })
  const [draft, setDraft] = useState(restored.draft)
  const [purpose, setPurpose] = useState<'followup' | 'correction'>(restored.purpose)
  const [storageError, setStorageError] = useState(restored.error)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [parentId, setParentId] = useState<string>(restored.parentId)
  const [replies, setReplies] = useState<
    Array<{ question: string; purpose: 'followup' | 'correction'; reply: Schemas['PlaygroundReply'] }>
  >([])
  const previewKey = `answer-followup-preview:${key}:${sessionId}`
  const [initialPreview] = useState(() => readTextCache(previewKey))
  const [preview, setPreview] = useState(initialPreview.value?.text ?? '')
  const [previousPreview, setPreviousPreview] = useState(initialPreview.value?.previousText ?? '')
  const previewRef = useRef({ text: preview, previousText: previousPreview })
  const [previewError, setPreviewError] = useState(initialPreview.error)
  function flushPreview() {
    try {
      setPreviewError(writeTextCache(previewKey, { ...previewRef.current, status: 'partial' }))
    } catch {
      setPreviewError('Unfinished text could not be saved in this tab. Copy it before leaving.')
    }
  }
  useEffect(() => {
    const save = () => {
      try {
        writeTextCache(previewKey, { ...previewRef.current, status: 'partial' })
      } catch {
        /* Stop/error paths surface storage failure while the page is mounted. */
      }
    }
    window.addEventListener('pagehide', save)
    return () => {
      window.removeEventListener('pagehide', save)
      save()
    }
  }, [previewKey])
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
  function edit(value: string, savedParent = parentId, nextPurpose = purpose) {
    setPurpose(nextPurpose)
    setDraft(value.slice(0, 2000))
    try {
      localStorage.setItem(
        key,
        JSON.stringify({ draft: value.slice(0, 2000), parentId: savedParent, purpose: nextPurpose }),
      )
      setStorageError('')
    } catch {
      setStorageError('Draft could not be saved. Keep a copy before leaving.')
    }
  }
  function stop() {
    flushPreview()
    request.current?.abort()
    request.current = null
    setBusy(false)
    setError(
      'Stopped waiting. Your draft is kept. The server may still finish; retry the original request to check for its result.',
    )
    input.current?.focus()
  }
  useEffect(() => {
    if (active || !request.current) return
    request.current.abort()
    request.current = null
    setBusy(false)
    setError('Stopped waiting. Your draft is kept. Retry the original request to check for its result.')
  }, [active])
  async function send() {
    if (!active || request.current || !draft.trim() || !parentFeedback.isSuccess) return
    try {
      const pending = recovery.prepare(
        {
          session_id: sessionId,
          question: draft.trim(),
          parent_answer_id: parentId,
          ...(purpose === 'correction' ? { purpose } : {}),
        },
        { snapshot: parentId, submitted: draft, display: draft.trim(), mode: 'explicit' },
      )
      await execute(pending)
    } catch (e) {
      setError((e as Error).message)
    }
  }
  async function execute(pending: PendingTutorRequest<FollowupRetryBody>) {
    if (!active || request.current) return
    const { question, parent_answer_id: originalParent, session_id: originalSession } = pending.body
    const ctl = new AbortController()
    request.current = ctl
    setBusy(true)
    setError('')
    if (previewRef.current.text) {
      previewRef.current.previousText = [previewRef.current.previousText, previewRef.current.text]
        .filter(Boolean)
        .join('\n\n---\n\n')
      setPreviousPreview(previewRef.current.previousText)
    }
    previewRef.current.text = ''
    setPreview('')
    flushPreview()
    const timer = setTimeout(() => {
      if (request.current === ctl) stop()
    }, 120_000)
    try {
      const reply = await streamAnswerFollowup(
        originalParent,
        { session_id: originalSession, question, purpose: pending.body.purpose ?? 'followup' },
        ctl.signal,
        pending.key,
        (token) => {
          if (request.current !== ctl || ctl.signal.aborted) return
          previewRef.current.text += token
          setPreview(previewRef.current.text)
        },
      )
      if (request.current !== ctl || ctl.signal.aborted) return
      previewRef.current.text = ''
      setPreview('')
      flushPreview()
      setReplies((old) => [...old, { question, purpose: pending.body.purpose ?? 'followup', reply }])
      if (reply.answer_id) {
        setParentId(reply.answer_id)
        void qc.invalidateQueries({ queryKey: ['answers'] })
      }
      edit(
        draft === pending.view.submitted ? '' : draft,
        reply.answer_id ?? originalParent,
        draft === pending.view.submitted ? 'followup' : purpose,
      )
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
        flushPreview()
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
      {replies.map(({ question, reply, purpose: replyPurpose }, index) => (
        <div key={index} className="border-t border-line pt-3">
          <h3 className="font-medium">
            {replyPurpose === 'correction'
              ? 'Proposed correction — review before relying on it'
              : 'Your follow-up'}
          </h3>
          <p className="whitespace-pre-wrap">{question}</p>
          <Markdown text={reply.text} />
          {active && <ReadAloud text={`Your question: ${question}\n\n${reply.text}`} />}
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
      {previewError && <p role="alert">{previewError}</p>}
      {preview && (
        <section aria-label="Unfinished follow-up" className="border border-line rounded p-3">
          <p className="text-sm text-muted">
            {busy ? 'Reply arriving' : 'Unfinished reply retained · your question may have changed'} · not
            checked or saved as an answer. Final wording and source notes may change.
          </p>
          <Markdown text={preview} />
        </section>
      )}
      {previousPreview && (
        <details>
          <summary>Earlier unfinished follow-ups · questions may have changed</summary>
          <Markdown text={previousPreview} />
        </details>
      )}
      {unsaved && (
        <p role="alert">
          Save failed for the latest reply. Keep a copy; further follow-ups are paused so they do not silently
          lose that context.
        </p>
      )}
      <label>
        Request type
        <select
          className="block"
          value={purpose}
          disabled={busy || unsaved}
          onChange={(event) => edit(draft, parentId, event.target.value as 'followup' | 'correction')}
        >
          <option value="followup">Continue the explanation</option>
          <option value="correction">Request a proposed correction</option>
        </select>
      </label>
      <Button
        disabled={busy || unsaved || !!draft.trim()}
        onClick={() => {
          edit(
            'Please reconsider the previous answer and my saved feedback. Explain what should change and why, or why the earlier reasoning still holds. State what evidence is missing.',
            parentId,
            'correction',
          )
          input.current?.focus()
        }}
      >
        Prepare correction request
      </Button>
      {!!draft.trim() && (
        <p className="text-sm text-muted">
          To keep your draft, choose Request a proposed correction above. Preparing a template is available
          when the draft is empty.
        </p>
      )}
      {purpose === 'correction' && (
        <p role="status">
          Sending asks for a proposed correction to the reply you are continuing from. It does not replace the
          original, verify the result or change your feedback. Only saved feedback is supplied; save any
          edited report first.
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
        {active && (
          <DictationButton
            disabled={busy || unsaved}
            onTranscript={(text) => edit([draft, text].filter(Boolean).join(' '))}
          />
        )}
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
