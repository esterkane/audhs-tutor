import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { api, ApiError, type Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'
import { activationKey, parseActivation } from './activationRecovery'

type Props = {
  draftId: string
  version: number
  blocked: boolean
  onBusy: (busy: boolean) => void
  onRefresh: () => void
}
export function PrivateActivation(props: Props) {
  const learner = useQuery({ queryKey: ['learner'], queryFn: api.me })
  if (!learner.data)
    return (
      <div className="mt-4">
        <p role="status">
          {learner.isError ? 'Could not identify your private workspace.' : 'Loading private workspace…'}
        </p>
        {learner.isError && <Button onClick={() => void learner.refetch()}>Retry workspace</Button>}
      </div>
    )
  return (
    <ActivationPanel key={`${learner.data.id}:${props.draftId}`} {...props} learnerId={learner.data.id} />
  )
}
function ActivationPanel({
  learnerId,
  draftId,
  version,
  blocked,
  onBusy,
  onRefresh,
}: Props & { learnerId: string }) {
  const cache = useQueryClient()
  const storageKey = activationKey(learnerId, draftId)
  const [recovery, setRecovery] = useState(() => {
    try {
      const raw = localStorage.getItem(storageKey)
      return { request: raw ? parseActivation(raw, draftId) : null, error: '' }
    } catch {
      return {
        request: null,
        error: 'Saved activation recovery could not be read. Check the server status before replacing it.',
      }
    }
  })
  const [confirmed, setConfirmed] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [storageWarning, setStorageWarning] = useState('')
  const [rejected, setRejected] = useState(false)
  const [receipt, setReceipt] = useState<Schemas['LessonActivationReceipt'] | null>(null)
  const active = useRef(true)
  const locked = useRef(false)
  const completed = useRef<HTMLParagraphElement>(null)
  useEffect(() => {
    active.current = true
    return () => {
      active.current = false
      onBusy(false)
    }
  }, [onBusy])
  const preview = useQuery({
    queryKey: ['lesson-activation', learnerId, draftId, version],
    retry: false,
    queryFn: ({ signal }) =>
      boundedRead<Schemas['LessonActivationPreview']>(
        `/api/lesson-activations/drafts/${encodeURIComponent(draftId)}/preview`,
        signal,
        'Activation preview',
      ),
  })
  const result = receipt ?? preview.data?.receipt
  useEffect(() => {
    if (result) completed.current?.focus()
  }, [result])
  const command = preview.data?.command
  const identity = command ? JSON.stringify(command) : ''
  const current = preview.data?.draft_version === version

  function forget() {
    try {
      localStorage.removeItem(storageKey)
      setRecovery({ request: null, error: '' })
      setError('')
      setRejected(false)
      setConfirmed('')
      onRefresh()
      void preview.refetch()
    } catch {
      setError('Browser storage is unavailable. The saved request has been kept; nothing new was sent.')
    }
  }
  async function send() {
    if (locked.current || blocked || recovery.error || !preview.data || preview.isFetching) return
    let request = recovery.request
    if (!request && (!command || !current || confirmed !== identity)) return
    if (request && request.command.promotion_id !== preview.data.promotion_id) {
      setError('Saved request does not match this draft. Check its activation status.')
      return
    }
    locked.current = true
    setSending(true)
    onBusy(true)
    setError('')
    setRejected(false)
    try {
      if (!request) request = { version: 1, draftId, key: crypto.randomUUID(), command: command! }
      const raw = JSON.stringify(request)
      try {
        localStorage.setItem(storageKey, raw)
        if (localStorage.getItem(storageKey) !== raw) throw new Error('Not retained')
      } catch {
        throw new Error(
          'Could not save activation recovery in this browser. Nothing was sent. Enable storage and try again.',
        )
      }
      setRecovery({ request, error: '' })
      const value = await boundedRead<Schemas['LessonActivationReceipt']>(
        '/api/lesson-activations/commands',
        new AbortController().signal,
        'Activation request',
        {
          method: 'POST',
          headers: { 'Idempotency-Key': request.key },
          body: JSON.stringify(request.command),
        },
      )
      if (!active.current) return
      setReceipt(value)
      try {
        localStorage.removeItem(storageKey)
        setRecovery({ request: null, error: '' })
      } catch {
        setStorageWarning(
          'The lesson is active. Browser recovery could not be cleared; retrying that saved request remains safe.',
        )
      }
      for (const key of ['curriculum', 'skills', 'areas', 'session-current'])
        void cache.invalidateQueries({ queryKey: [key] })
      onRefresh()
    } catch (cause) {
      if (!active.current) return
      setError(cause instanceof Error ? cause.message : 'Activation response was not received.')
      setRejected(cause instanceof ApiError && cause.status >= 400 && cause.status < 500)
      void preview.refetch()
    } finally {
      locked.current = false
      if (active.current) {
        setSending(false)
        onBusy(false)
      }
    }
  }
  return (
    <section aria-label="Private lesson activation" className="border-t border-line mt-5 pt-4 space-y-3">
      {result ? (
        <>
          <p ref={completed} tabIndex={-1} role="status" className="font-medium">
            Your private lesson is active.
          </p>
          <p className="text-sm">
            {result.skill_ids.length} {result.skill_ids.length === 1 ? 'lesson' : 'lessons'} ·{' '}
            {result.assessment_ids.length}{' '}
            {result.assessment_ids.length === 1 ? 'practice question' : 'practice questions'}. Activation does
            not award learning evidence or mark the questions reviewed.
          </p>
          <Link className="underline text-accent" to="/">
            Choose a lesson on Home
          </Link>
        </>
      ) : (
        <>
          <h3 className="font-medium">Activate for your learning</h3>
          <p className="text-sm">
            Review the saved lesson above. Activation adds it to your private learning topics; it does not
            share it online.
          </p>
          {preview.isPending && <p role="status">Checking saved lesson and source history…</p>}
          {preview.isError && <p role="alert">Could not check activation status. {preview.error.message}</p>}
          {preview.data && (
            <>
              <p className="text-sm">
                Saved version {preview.data.draft_version}
                {command
                  ? ` · ${preview.data.skills} ${preview.data.skills === 1 ? 'lesson' : 'lessons'} · ${preview.data.assessments} ${preview.data.assessments === 1 ? 'practice question' : 'practice questions'}`
                  : ''}
              </p>
              {preview.data.warnings?.length ? (
                <details>
                  <summary className="cursor-pointer text-sm">Source and review limitations</summary>
                  <ul className="list-disc pl-5 text-sm space-y-1">
                    {preview.data.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </details>
              ) : null}
              {preview.data.issues?.map((issue, i) => (
                <p key={i} role="alert" className="text-sm">
                  {issue}
                </p>
              ))}
            </>
          )}
          {blocked && (
            <p className="text-sm">
              Save or discard any edits and resolve draft conflicts before activation.
            </p>
          )}
          {!current && preview.data && (
            <p className="text-sm">This view is out of date. Load the latest draft before activating.</p>
          )}
          {recovery.request ? (
            <>
              <p role="status" className="text-sm">
                An activation request is saved in this browser. No request is sent automatically. Retry uses
                the same request and cannot create a second copy.
              </p>
              <Button
                variant="primary"
                disabled={blocked || sending || preview.isFetching || !preview.data || !!recovery.error}
                onClick={() => void send()}
              >
                {sending ? 'Checking activation…' : 'Retry saved activation'}
              </Button>
              {rejected && (
                <Button disabled={sending || preview.isFetching} onClick={forget}>
                  Review latest draft instead
                </Button>
              )}
            </>
          ) : (
            command &&
            current && (
              <>
                <label className="flex items-start gap-3 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={confirmed === identity}
                    disabled={blocked || sending}
                    onChange={(e) => setConfirmed(e.target.checked ? identity : '')}
                  />
                  I reviewed this saved version and want these lessons available for practice. This is not an
                  assessment-quality review.
                </label>
                <Button
                  variant="primary"
                  disabled={
                    blocked || sending || preview.isFetching || confirmed !== identity || !!recovery.error
                  }
                  onClick={() => void send()}
                >
                  {sending ? 'Activating…' : 'Activate private lessons'}
                </Button>
              </>
            )
          )}
          {recovery.error && (
            <>
              <p role="alert" className="text-sm">
                {recovery.error}
              </p>
              {preview.isSuccess && !preview.isFetching && (
                <Button disabled={sending} onClick={forget}>
                  Replace unreadable recovery
                </Button>
              )}
            </>
          )}
          <Button
            disabled={sending || preview.isFetching}
            onClick={() => {
              onRefresh()
              void preview.refetch()
            }}
          >
            {preview.isFetching ? 'Checking status…' : 'Check activation status'}
          </Button>
        </>
      )}
      {storageWarning && (
        <p role="status" className="text-sm">
          {storageWarning}
        </p>
      )}
      {error && !result && (
        <p role="alert" className="text-sm">
          {error}
        </p>
      )}
    </section>
  )
}
