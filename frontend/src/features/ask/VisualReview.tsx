import { useEffect, useId, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import type { Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'
import { RequestRecoveryControls } from '../playground/RequestRecoveryControls'
import { useVisualReviewRecovery, type PendingTutorRequest, type VisualReviewBody } from '../playground/useRequestRecovery'
import { useLessonDraft } from '../tutor/useLessonDraft'

export function VisualReview({ documentId, learnerId, version }: {
  documentId: string; learnerId: string; version: Schemas['VisualVersionDetail']
}) {
  const scope = `visual-review:${learnerId}:${documentId}:${version.id}`
  const note = useLessonDraft(scope, 'diagram review')
  const recovery = useVisualReviewRecovery(scope)
  const fieldId = useId()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(true)
  const cache = useQueryClient()
  const key = ['visual-reviews', learnerId, documentId, version.id]
  const history = useQuery({ queryKey: key, retry: false, queryFn: ({ signal }) =>
    boundedRead<Schemas['VisualReviewRecord'][]>(`/api/authored-visuals/${encodeURIComponent(documentId)}/versions/${encodeURIComponent(version.id)}/reviews`, signal, 'Visual reviews'),
  })
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; active.current?.abort() } }, [])
  const canAccept = version.grounding_now === 'sources_recorded' || version.grounding_now === 'ungrounded'
  const disabled = busy || !!recovery.pending || recovery.needsDiscard || note.input.length > 4000

  async function save(decision: 'accept' | 'reject', previous?: PendingTutorRequest<VisualReviewBody>) {
    if (active.current || (!previous && disabled)) return
    const controller = new AbortController(); active.current = controller; setBusy(true); setError(''); setStatus('')
    const submittedNote = previous?.body.note ?? note.input
    try {
      let intent = previous
      if (!intent) {
        const doc = await boundedRead<Schemas['VisualDocumentSummary']>(`/api/authored-visuals/${encodeURIComponent(documentId)}`, controller.signal, 'Current diagram revision')
        if (!mounted.current || controller.signal.aborted) return
        if (doc.archived) throw new Error('This diagram is archived. Restore it before adding a review. Your note is kept.')
        intent = recovery.prepare({ action: 'review', document_id: documentId, expected_revision: doc.revision,
          version_id: version.id, content_sha256: version.content_sha256, snapshot_sha256: version.snapshot_sha256,
          decision, confirm: true, note: submittedNote,
        }, { display: `Version ${version.version}: ${decision === 'accept' ? 'Presentation reviewed' : 'Needs correction'}`, submitted: '', snapshot: '', mode: 'explicit' })
      }
      await boundedRead<Schemas['VisualReceipt']>('/api/authored-visuals/commands', controller.signal, 'Save diagram review', {
        method: 'POST', headers: { 'Idempotency-Key': intent.key }, body: JSON.stringify(intent.body),
      })
      if (!mounted.current || controller.signal.aborted) return
      recovery.accept(intent.key)
      // Keep the note after confirmation; later drafts must not be erased by a late reply.
      setStatus(`Review saved for version ${version.version}. Your note is kept below.`)
      await cache.invalidateQueries({ queryKey: key })
    } catch (reason) {
      if (mounted.current) setError(reason instanceof Error ? reason.message : 'Review could not be confirmed. Your note is kept.')
    } finally { if (mounted.current) { active.current = null; setBusy(false) } }
  }

  return <div className="space-y-2">
    {history.isPending && <p role="status">Loading your presentation reviews…</p>}
    {history.isError && <p role="alert">Review history is unavailable. <Button variant="secondary" onClick={() => void history.refetch()}>Retry review history</Button></p>}
    {history.data?.[0] && <p className="text-sm">Your recorded review of version {version.version}: <strong>{history.data[0].decision === 'reject' ? 'Needs correction' : 'Presentation reviewed'}</strong> · {new Date(history.data[0].created_at).toLocaleString()}. This is your presentation judgment, not a factual accuracy check.</p>}
    <Disclosure label={`Review this diagram · version ${version.version}`}>
      <div className="space-y-3">
        <p>Your review applies only to this version and its source snapshot. It does not verify factual accuracy or measure your learning. You can record a different review later.</p>
        <label className="block" htmlFor={fieldId}>What works or needs correction? (optional)</label>
        <textarea id={fieldId} className="w-full rounded border border-line bg-card p-3" rows={3} maxLength={4000} value={note.input} onChange={event => note.setInput(event.target.value)} />
        {note.error && <p role="alert">{note.error}</p>}
        {!canAccept && <p role="status">The source history is unavailable or changed. You can still flag a correction; a positive review needs current source checks.</p>}
        <RequestRecoveryControls saveOnly recovery={recovery} busy={busy} originalContext="diagram version, source snapshot, decision and note" retry={() => { if (recovery.pending) void save(recovery.pending.body.decision, recovery.pending) }} />
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" disabled={disabled || !canAccept || !history.isSuccess} onClick={() => void save('accept')}>I reviewed this presentation</Button>
          <Button variant="secondary" disabled={disabled || !history.isSuccess} onClick={() => void save('reject')}>Needs correction</Button>
          {busy && <Button variant="secondary" onClick={() => active.current?.abort()}>Stop waiting for review</Button>}
        </div>
        {busy && <p role="status">Saving review…</p>}
        {error && <p role="alert">{error}</p>}
        {status && <p role="status">{status}</p>}
        <p className="text-sm text-muted">Unsubmitted note kept in this browser tab. A confirmed review is saved in the local database.</p>
        {!!history.data?.length && <Disclosure label="Previous reviews of this version">
          <ol className="space-y-2">{history.data.map(review => <li key={review.id} className="break-words"><strong>{review.decision === 'reject' ? 'Needs correction' : 'Presentation reviewed'}</strong> · {new Date(review.created_at).toLocaleString()}<p>{review.note || 'No note.'}</p></li>)}</ol>
        </Disclosure>}
      </div>
    </Disclosure>
  </div>
}
