import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch, type Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'

async function boundedRequest<T>(url: string, init: RequestInit = {}): Promise<T> {
  const abort = new AbortController()
  const cancel = () => abort.abort()
  init.signal?.addEventListener('abort', cancel, { once: true })
  if (init.signal?.aborted) abort.abort()
  let timer: ReturnType<typeof setTimeout> | undefined
  try {
    return await Promise.race([
      apiFetch<T>(url, { ...init, signal: abort.signal }),
      new Promise<never>((_, reject) => { timer = setTimeout(() => { abort.abort(); reject(new Error('Request timed out')) }, 15000) }),
    ])
  } finally { clearTimeout(timer); init.signal?.removeEventListener('abort', cancel) }
}

export function AnswerReplacement({ answerId, candidateId }: { answerId: string; candidateId?: string }) {
  const [open, setOpen] = useState(false)
  const [reviewed, setReviewed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const active = useRef<AbortController | null>(null)
  const alive = useRef(true)
  useEffect(() => { alive.current = true; return () => { alive.current = false; active.current?.abort(); active.current = null } }, [])
  const qc = useQueryClient()
  const query = useQuery({
    queryKey: ['answer-replacement', answerId],
    queryFn: ({ signal }) => boundedRequest<Schemas['AnswerReplacementState']>(`/api/answers/${encodeURIComponent(answerId)}/replacement`, { signal }),
    enabled: open,
  })
  async function choose(replacementId: string | null) {
    if (!query.data || active.current || busy || (replacementId && !reviewed)) return
    const attempt = new AbortController()
    active.current = attempt
    setBusy(true); setError(''); setStatus('')
    try {
      const value = await boundedRequest<Schemas['AnswerReplacementState']>(`/api/answers/${encodeURIComponent(answerId)}/replacement`, {
        method: 'PUT', signal: attempt.signal, body: JSON.stringify({ replacement_id: replacementId, revision: query.data.revision }),
      })
      if (!alive.current || active.current !== attempt) return
      qc.setQueryData(['answer-replacement', answerId], value)
      void qc.invalidateQueries({ queryKey: ['answers'] })
      if (alive.current) { setReviewed(false); setStatus(replacementId ? 'Preferred correction saved. Both answers remain in history.' : 'Preference removed. Existing feedback still applies.') }
    } catch {
      if (alive.current && active.current === attempt) setError('The choice could not be confirmed. Retry the same choice, or review the latest saved choice before changing it. No answer text was removed.')
    } finally { if (alive.current && active.current === attempt) { active.current = null; setBusy(false) } }
  }
  return <details onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>{candidateId ? 'Review this correction as your preferred reply' : 'Preferred correction for this answer'}</summary>
    <p className="text-sm my-2">Choosing a correction excludes the original from automatic suggestions and reuse. Both remain readable. This is your preference, not verified correctness or a learning score. It does not bypass source, context or feedback checks for the correction.</p>
    {candidateId && <p><Link className="underline" to={`/answers/${encodeURIComponent(answerId)}`}>Compare with the original answer</Link> before choosing.</p>}
    {open && (query.isPending ? <p role="status">Loading preferred correction…</p>
      : query.isError ? <p role="alert">Could not load the saved choice. <Button onClick={() => void query.refetch()}>Retry preferred correction</Button></p>
      : <div className="grid gap-2">
        {query.data.replacement_id ? <p>Current preference: <Link className="underline" to={`/answers/${encodeURIComponent(query.data.replacement_id)}`}>Open preferred correction</Link>. Check its current feedback before relying on it.</p> : <p>No preferred correction selected.</p>}
        {candidateId && query.data.replacement_id !== candidateId && <>
          <label><input type="checkbox" checked={reviewed} disabled={busy} onChange={(event) => setReviewed(event.target.checked)} /> I reviewed both answers and want to prefer this correction.</label>
          <Button disabled={busy || !reviewed} onClick={() => void choose(candidateId)}>Prefer this correction</Button>
        </>}
        {query.data.replacement_id && <Button disabled={busy} onClick={() => void choose(null)}>Undo preferred correction</Button>}
        <Button disabled={busy} onClick={async () => { setReviewed(false); setStatus(''); await query.refetch() }}>Review latest saved choice</Button>
      </div>)}
    {busy && <p role="status">Saving preferred correction…</p>}
    {status && <p role="status">{status}</p>}
    {error && <p role="alert">{error}</p>}
  </details>
}
