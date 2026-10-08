import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import type { Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'

export function CorrectionImpact({ id, revision, dirty, disabled = false, onPublish }: {
  id: string; revision: number; dirty: boolean; disabled?: boolean;
  onPublish?: (preview: Schemas['CorrectionImpact']) => void;
}) {
  const [confirmedToken, setConfirmedToken] = useState<string | null>(null)
  const [data, setData] = useState<Schemas['CorrectionImpact'] | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const active = useRef<AbortController | null>(null)
  useEffect(() => () => active.current?.abort(), [])
  async function load() {
    if (active.current) return
    const controller = new AbortController(); active.current = controller; setBusy(true); setError(''); setConfirmedToken(null)
    try {
      const result = await boundedRead<Schemas['CorrectionImpact']>(`/api/questions/correction-drafts/${encodeURIComponent(id)}/impact`, controller.signal, 'Correction impact')
      if (!controller.signal.aborted) setData(result)
    } catch { if (!controller.signal.aborted) setError('Could not load the impact preview. Your edits are kept. Try again.') }
    finally { if (!controller.signal.aborted) setBusy(false); if (active.current === controller) active.current = null }
  }
  return <section className="grid gap-3 min-w-0" aria-label="Correction impact">
    <h3 className="font-semibold">Review the impact and sources</h3>
    <p>This reads the saved draft. It does not replace questions or change progress.</p>
    <Button disabled={busy} onClick={() => void load()}>{data ? 'Refresh impact preview' : 'Load impact preview'}</Button>
    {busy && <p role="status">Loading impact and source passages…</p>}
    {error && <p role="alert">{error}</p>}
    {data && <>
      <p role="status">Saved draft version {data.revision}. {(dirty || data.revision !== revision) && 'This preview does not represent your current edits. Save and refresh before reviewing.'}</p>
      <p>{data.affected_reviews} active review card(s) refer to the original question. A replacement would exclude those cards from future practice; past answers and review history would remain.</p>
      <p>{data.linked_exercises} visible coding exercise(s) link to this question.</p>
      <p>A replacement would have a new question identity. Grades, mastery and review schedules would not transfer.</p>
      <p>Source status: {data.review.source_status.replaceAll('_', ' ')}. Available passages are evidence to inspect, not proof that the proposed answer is correct.</p>
      {(data.review.content_changed || data.review.question_state_changed) && <p role="alert">The original question or its practice status has changed since this draft began.</p>}
      <ul>{data.review.problems.map((problem, i) => <li key={i}>{problem.field}: {problem.message}</li>)}</ul>
      <h4 className="font-semibold">Current source passages</h4>
      {!data.passages.length && <p>No source passages could be resolved. Do not treat this as source verification.</p>}
      {data.passages.map(source => <details key={source.reference} className="min-w-0">
        <summary className="break-words">Source {source.reference} · {source.status}</summary>
        <p className="break-words">Document version: {source.document_version_id ?? 'unavailable'}</p>
        {typeof source.text === 'string' ? <p className="whitespace-pre-wrap break-words">{source.text}</p> : <p>Source text unavailable.</p>}
        {source.truncated && <p>Excerpt limited to 6,000 characters; this is not the complete passage.</p>}
      </details>)}
      {onPublish && <div className="grid gap-2">
        <ul>{data.publication_blockers?.map(reason => <li key={reason}>{reason}</li>)}</ul>
        <label className="flex gap-2 items-start"><input type="checkbox"
          checked={confirmedToken === data.preview_token && !dirty && data.revision === revision}
          disabled={disabled || dirty || busy || !!error || data.revision !== revision || !data.publication_available}
          onChange={event => setConfirmedToken(event.target.checked ? data.preview_token : null)} />
          I reviewed the proposed answer and sources. Replace the original question for my future practice.</label>
        <p>Past work stays unchanged. There is no one-click undo; you can exclude the replacement or create another correction.</p>
        <Button disabled={disabled || dirty || busy || !!error || data.revision !== revision || !data.publication_available || confirmedToken !== data.preview_token}
          onClick={() => { setConfirmedToken(null); onPublish(data) }}>Publish correction for my practice</Button>
      </div>}
    </>}
  </section>
}
