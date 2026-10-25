import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { ApiError, apiFetch, type Schemas } from '../../lib/api'

type Preview = Schemas['TaskReviewPreview']
type Command = Schemas['TaskReviewCommand']

// Content is authoring data, never executable markup or model-generated code.
function Content({ value }: { value: unknown }): ReactNode {
  if (value === null || value === undefined) return <span>Not provided</span>
  if (Array.isArray(value)) return <ul className="list-disc pl-5 grid gap-2">{value.map((item, i) => <li key={i}><Content value={item} /></li>)}</ul>
  if (typeof value === 'object') return <dl className="grid gap-2">{Object.entries(value).map(([key, item]) => <div key={key}><dt className="font-medium">{key.replaceAll('_', ' ')}</dt><dd className="whitespace-pre-wrap"><Content value={item} /></dd></div>)}</dl>
  return <span className="whitespace-pre-wrap">{String(value)}</span>
}

export function TaskReview() {
  const [params] = useSearchParams()
  const assessment = params.get('assessment')
  const requestedReturn = params.get('returnTo') ?? ''
  const returnTo = requestedReturn.startsWith('/') && !requestedReturn.startsWith('//') && !requestedReturn.includes('\\') ? requestedReturn : '/progress'
  return <div className="grid gap-4 max-w-3xl min-w-0 break-words">
    <h1 className="text-page-title font-semibold">Review task and rubric</h1>
    <p>This records your review of the content. It is not an answer, a grade or evidence that you understand the topic. Past results stay unchanged.</p>
    <Link to={returnTo}>{returnTo === '/progress' ? 'Back to Progress' : 'Return to previous activity'}</Link>
    {assessment ? <Review key={assessment} assessment={assessment} /> : <p>Open a task’s Question practice options and choose Review task and rubric.</p>}
  </div>
}

function Review({ assessment }: { assessment: string }) {
  const [preview, setPreview] = useState<Preview | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [facet, setFacet] = useState<Command['facet']>('explanation')
  const [pending, setPending] = useState<Command | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(true)
  const heading = useRef<HTMLHeadingElement>(null)
  const reveal = useRef<HTMLButtonElement>(null)
  const feedback = useRef<HTMLParagraphElement>(null)
  const feedbackFocus = useRef<{ origin: Element | null } | null>(null)
  useLayoutEffect(() => {
    const intent = feedbackFocus.current
    feedbackFocus.current = null
    if (notice && intent && (document.activeElement === intent.origin || document.activeElement === document.body)) feedback.current?.focus()
  }, [notice])
  const path = `/api/questions/${encodeURIComponent(assessment)}/task-review`
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; active.current?.abort() } }, [])
  async function load() {
    if (active.current || pending) return
    const controller = new AbortController(); active.current = controller
    setBusy(true); setConfirmed(false); setError(''); setNotice('')
    try {
      const result = await apiFetch<Preview>(path, { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]) })
      if (!mounted.current) return
      setPreview(result); setFacet(result.current_review?.facet ?? 'explanation')
      requestAnimationFrame(() => { if (document.activeElement === reveal.current) heading.current?.focus() })
    } catch { if (mounted.current) { setPreview(null); setError('Could not load the task review. Try again.') } }
    finally { if (mounted.current) setBusy(false); if (active.current === controller) active.current = null }
  }
  async function save(decision: Command['decision']) {
    if (active.current || !preview || (!pending && !confirmed)) return
    const command = pending ?? { request_id: crypto.randomUUID(), expected_revision: preview.current_review?.revision ?? 0,
      content_version: preview.content_version, decision, facet: decision === 'revoke' ? preview.current_review!.facet : facet, confirmed: true }
    const controller = new AbortController(); active.current = controller
    const focusOrigin = document.activeElement
    let focusMoved = false
    const trackFocus = (event: FocusEvent) => { if (event.target !== focusOrigin) focusMoved = true }
    document.addEventListener('focusin', trackFocus)
    setBusy(true); setPending(command); setError(''); setNotice('')
    try {
      const receipt = await apiFetch<Schemas['TaskReviewReceipt']>(path, { method: 'POST', body: JSON.stringify(command), signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]) })
      if (!mounted.current) return
      setPending(null); setConfirmed(false); setPreview(null)
      feedbackFocus.current = focusMoved ? null : { origin: focusOrigin }
      setNotice(receipt.decision === 'approve' ? 'Task review saved. This does not change your grades or confirm understanding.' : 'Review revoked. Your review history and past answers are kept.')
    } catch (e) {
      if (!mounted.current) return
      if (e instanceof ApiError && e.status >= 400 && e.status < 500) {
        setPending(null); setPreview(null); setConfirmed(false)
        setError('This review could not be saved. Reload the current task and review it again.')
      } else setError('The save result is uncertain. Retry the same review to confirm it; it will not create a duplicate.')
    } finally { document.removeEventListener('focusin', trackFocus); if (mounted.current) setBusy(false); if (active.current === controller) active.current = null }
  }
  return <section className="grid gap-4 border border-line rounded p-4 min-w-0" aria-busy={busy}>
    <p>Opening this authoring preview reveals the task, grading criteria and any reference answers. Use it to review content, not to test your own understanding.</p>
    <Button aria-disabled={busy || !!pending} onClick={event => { reveal.current = event.currentTarget; void load() }}>{preview ? 'Reload task and rubric' : 'Show task and rubric'}</Button>
    {busy && <p role="status">{pending ? 'Saving review…' : 'Loading task and rubric…'}</p>}
    {error && <p role="alert">{error}</p>}
    {notice && <p ref={feedback} tabIndex={-1} role="status">{notice}</p>}
    {preview && <>
      <h2 ref={heading} tabIndex={-1} className="text-lg font-semibold">Content to review</h2>
      <section><h3 className="font-semibold">Learning objective</h3><Content value={preview.content.objective} /></section>
      <section><h3 className="font-semibold">Task and reference content</h3><Content value={preview.content.item} /></section>
      <section><h3 className="font-semibold">Rubric criteria</h3><Content value={preview.content.criteria} /></section>
      <p>{preview.current_review ? `Latest review: ${preview.current_review.decision === 'approve' ? 'approved' : 'revoked'} · ${new Date(preview.current_review.reviewed_at).toLocaleString()}.` : 'No review recorded for this task.'} {preview.approval_matches_content ? 'Approval matches this content.' : preview.current_review?.decision === 'approve' ? 'Content changed; the previous approval does not cover this version.' : ''}</p>
      {!preview.reviewable && <p>{preview.unavailable_reason}</p>}
      <label className="grid gap-1">What does this task assess?
        <select value={facet} disabled={busy || !!pending || !preview.reviewable} onChange={e => { setFacet(e.target.value as Command['facet']); setConfirmed(false) }} className="border border-line rounded bg-surface p-2">
          <option value="explanation">Explanation of an idea</option><option value="application">Application to a task</option>
        </select>
      </label>
      <label className="flex gap-2 items-start"><input type="checkbox" checked={confirmed} disabled={busy || !!pending} onChange={e => setConfirmed(e.target.checked)} /><span>I reviewed the objective, task and rubric and confirm the review action below. This is not a claim of independent work.</span></label>
      <div className="flex flex-wrap gap-2">
        {preview.reviewable && <Button disabled={busy || !!pending || !confirmed} onClick={() => void save('approve')}>Approve this task review</Button>}
        {preview.current_review?.decision === 'approve' && <Button variant="secondary" disabled={busy || !!pending || !confirmed} onClick={() => void save('revoke')}>Revoke previous approval</Button>}
        <Button variant="ghost" disabled={busy || !!pending} onClick={() => { setPreview(null); setConfirmed(false); reveal.current?.focus() }}>Close without changing review</Button>
      </div>
    </>}
    {pending && !busy && <Button onClick={() => void save(pending.decision)}>Retry same review</Button>}
  </section>
}
