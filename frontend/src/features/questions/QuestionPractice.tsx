import { useId, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ApiError, apiFetch, type Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'
import { Textarea } from '../../components/ui/textarea'

type Preview = Schemas['QuestionPracticeView']
type State = Schemas['QuestionStateOut']
type Intent = Schemas['QuestionTransitionIn']
const key = (id: string) => ['question-practice', id]

export function QuestionPractice(props: { assessmentId: string; onChanged?: (id: string, state: State) => void | Promise<void> }) {
  return <PracticeControl key={props.assessmentId} {...props} />
}

function PracticeControl({ assessmentId, onChanged }: { assessmentId: string; onChanged?: (id: string, state: State) => void | Promise<void> }) {
  const id = useId()
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  const intent = useRef<Intent | null>(null)
  const [pendingIntent, setPendingIntent] = useState<Intent | null>(null)
  const [error, setError] = useState('')
  const [needsRefresh, setNeedsRefresh] = useState(false)
  const [message, setMessage] = useState('')
  const path = `/api/questions/${encodeURIComponent(assessmentId)}/practice`
  const query = useQuery({ queryKey: key(assessmentId), enabled: open, retry: false,
    queryFn: ({ signal }) => apiFetch<Preview>(path, { signal: AbortSignal.any([signal, AbortSignal.timeout(12000)]) }) })
  const status = query.data?.status
  async function change() {
    if (busyRef.current || !status || needsRefresh || query.isFetching || query.isError) return
    busyRef.current = true
    setBusy(true)
    setError('')
    intent.current ??= { request_id: crypto.randomUUID(), expected_revision: status.revision,
      action: status.state === 'active' ? 'suspend' : 'restore', reason }
    setPendingIntent(intent.current)
    try {
      const result = await apiFetch<State>(path, { method: 'POST', body: JSON.stringify(intent.current), signal: AbortSignal.timeout(15000) })
      qc.setQueryData<Preview>(key(assessmentId), old => old ? { ...old, status: result } : old)
      intent.current = null
      setPendingIntent(null)
      setMessage(result.state === 'active' ? 'Restored. This question may appear in practice again.' : 'Excluded from future practice. Your past answers are kept.')
      await onChanged?.(assessmentId, result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not confirm the action.')
      if (e instanceof ApiError && e.status === 409) {
        intent.current = null
      setPendingIntent(null)
        setNeedsRefresh(true)
      }
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }
  async function reload() {
    if (busyRef.current) return
    intent.current = null
    setPendingIntent(null)
    setError('')
    setNeedsRefresh(false)
    await query.refetch()
  }
  return <div className="mt-3 text-sm">
    <Button variant="ghost" aria-expanded={open} aria-controls={`${id}-panel`} onClick={() => setOpen(!open)}>Question practice options</Button>
    {open && <div id={`${id}-panel`} className="mt-2 grid gap-2" aria-busy={busy || query.isFetching}>
      {query.isFetching && <p role="status">Loading question status…</p>}
      {query.error && <p role="alert">Could not load current status: {query.error.message}</p>}
      {status && <>
        <p>{status.state === 'active' ? 'Available for practice.' : status.state === 'suspended' ? 'Excluded from practice.' : `Question is ${status.state}.`}</p>
        <p>{query.data?.affected_reviews} existing review card(s) affected. Exclusion stops future questions and reviews; it does not delete past answers or change mastery.</p>
        {status.state === 'active' && <>
          <label htmlFor={`${id}-reason`}>Reason (optional)</label>
          <Textarea id={`${id}-reason`} value={reason} maxLength={1500} disabled={busy || Boolean(pendingIntent)} onChange={e => setReason(e.target.value)} />
        </>}
        {(status.state === 'active' || status.state === 'suspended') && <Button onClick={() => void change()} disabled={busy || query.isFetching || query.isError || needsRefresh}>
          {busy ? 'Saving question choice…' : error && pendingIntent ? 'Retry same action' : status.state === 'active' ? 'Exclude this question' : 'Restore this question'}
        </Button>}
        {status.state === 'suspended' && <p>Restoring keeps the previous review schedule. Previously shown questions need a fresh view.</p>}
      </>}
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error} {needsRefresh ? 'Reload status before choosing again.' : 'The result is uncertain. Retry the same action or reload its status; nothing is retried automatically.'}</p>}
      {(query.isError || error || needsRefresh) && <Button disabled={busy || query.isFetching} onClick={() => void reload()}>Reload question status</Button>}
      <Link to="/preferences#excluded-questions">Manage excluded questions</Link>
    </div>}
  </div>
}

export function ExcludedQuestions() {
  const heading = useRef<HTMLHeadingElement>(null)
  const [notice, setNotice] = useState('')
  const [open, setOpen] = useState(false)
  const [offset, setOffset] = useState(0)
  const query = useQuery({ queryKey: ['excluded-questions', offset], enabled: open, retry: false,
    queryFn: ({ signal }) => apiFetch<Schemas['ExcludedQuestions']>(`/api/questions/excluded?offset=${offset}&limit=20`, { signal: AbortSignal.any([signal, AbortSignal.timeout(12000)]) }) })
  return <section id="excluded-questions" className="border border-line rounded p-4">
    <h2 ref={heading} tabIndex={-1} className="text-lg font-semibold">Manage question exclusions</h2>
    <p className="text-sm text-muted">Find questions you stopped practicing and restore them. Past answers remain in your history.</p>
    <Button className="mt-2" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? 'Hide excluded questions' : 'Show excluded questions'}</Button>
    {notice && <p role="status" className="mt-2">{notice}</p>}
    {open && <div className="mt-3 grid gap-3">
      <Button disabled={query.isFetching} onClick={() => void query.refetch()}>Refresh exclusions</Button>
      {query.isFetching && <p role="status">Loading excluded questions…</p>}
      {query.error && <p role="alert">Could not load exclusions: {query.error.message}</p>}
      {query.data && <>
        <p>{query.data.total} excluded question(s).</p>
        {query.data.items.map(item => <article key={item.status.assessment_id} className="border border-line rounded p-3 min-w-0 break-words">
          <h3 className="font-medium">{item.skill_title}</h3><p>{item.question}</p>
          {item.status.reason && <p className="text-sm text-muted">Reason: {item.status.reason}</p>}
          <QuestionPractice assessmentId={item.status.assessment_id} onChanged={async (_id, state) => {
            await query.refetch()
            setNotice(state.state === 'active' ? 'Restored. This question may appear in practice again.' : 'Question excluded from practice.')
            heading.current?.focus()
          }} />
        </article>)}
        <div className="flex flex-wrap gap-2">
          {offset > 0 && <Button onClick={() => setOffset(Math.max(0, offset - 20))}>Previous questions</Button>}
          {offset + query.data.items.length < query.data.total && <Button onClick={() => setOffset(offset + 20)}>More questions</Button>}
        </div>
      </>}
    </div>}
  </section>
}
