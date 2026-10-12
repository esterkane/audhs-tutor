import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { apiFetch, type Schemas } from '../../lib/api'
import { useAnswerCheckRecovery, type PendingTutorRequest } from '../playground/useRequestRecovery'
import { RequestRecoveryControls } from '../playground/RequestRecoveryControls'

type CheckRequest = Schemas['AnswerCheckRequest']
type Hit = Schemas['SearchHit']

export function AnswerChecks({ answerId, learnerId }: { answerId: string; learnerId: string }) {
  const [opened, setOpened] = useState(false)
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<Hit[]>([])
  const [selected, setSelected] = useState<Hit[]>([])
  const [searched, setSearched] = useState(false)
  const [busy, setBusy] = useState<'search' | 'check' | null>(null)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(true)
  const qc = useQueryClient()
  const recovery = useAnswerCheckRecovery(`ask-check:${learnerId}:${answerId}`)
  const historyKey = ['answer-checks', learnerId, answerId]
  const history = useQuery({
    queryKey: historyKey,
    enabled: opened,
    retry: false,
    queryFn: ({ signal }) =>
      apiFetch<Schemas['AnswerCheckPage']>(`/api/answer-checks/answer/${encodeURIComponent(answerId)}`, {
        signal,
      }),
  })
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      active.current?.abort()
    }
  }, [])

  async function search() {
    if (active.current || !query.trim()) return
    const controller = new AbortController()
    active.current = controller
    setBusy('search')
    setError('')
    setSearched(false)
    setHits([])
    try {
      const found = await apiFetch<Schemas['SearchOut']>('/api/corpus/search', {
        method: 'POST',
        body: JSON.stringify({ query: query.trim(), k: 6, tutor_view: true }),
        signal: controller.signal,
      })
      if (!mounted.current || active.current !== controller) return
      setHits(found.hits)
      setSearched(true)
    } catch (e) {
      if (mounted.current && !controller.signal.aborted)
        setError(e instanceof Error ? e.message : 'Search failed.')
    } finally {
      if (mounted.current && active.current === controller) {
        active.current = null
        setBusy(null)
      }
    }
  }

  async function check(pending?: PendingTutorRequest<CheckRequest>) {
    if (active.current || (!pending && !selected.length)) return
    const controller = new AbortController()
    active.current = controller
    setBusy('check')
    let request: PendingTutorRequest<CheckRequest>
    try {
      const hashes = pending
        ? pending.body.passage_hashes
        : Object.fromEntries(
            await Promise.all(
              selected.map(async (hit) => {
                const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(hit.text))
                return [
                  hit.chunk_id,
                  Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join(''),
                ]
              }),
            ),
          )
      if (!mounted.current || active.current !== controller) return
      request =
        pending ??
        recovery.prepare(
          { answer_id: answerId, passage_ids: selected.map((h) => h.chunk_id), passage_hashes: hashes },
          {
            display: `Check ${selected.length} selected passages`,
            snapshot: '',
            submitted: '',
            mode: 'explicit',
          },
        )
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Cannot preserve request.')
      active.current = null
      setBusy(null)
      return
    }
    setError('')
    setStatus('Reviewing selected passages with the local model…')
    try {
      await apiFetch<Schemas['AnswerCheckDetail']>('/api/answer-checks', {
        method: 'POST',
        headers: { 'Idempotency-Key': request.key },
        body: JSON.stringify(request.body),
        signal: controller.signal,
      })
      if (!mounted.current || active.current !== controller) return
      recovery.accept(request.key)
      setStatus('Review saved locally. Read its claim-specific findings below.')
      await qc.invalidateQueries({ queryKey: historyKey })
    } catch (e) {
      if (mounted.current && !controller.signal.aborted) {
        setError(e instanceof Error ? e.message : 'Review unavailable.')
        setStatus('Your original answer is unchanged.')
      }
    } finally {
      if (mounted.current && active.current === controller) {
        active.current = null
        setBusy(null)
      }
    }
  }

  function stop() {
    active.current?.abort()
    active.current = null
    setBusy(null)
    setStatus('Stopped waiting. A check may still finish; use its saved retry to recover it.')
  }

  return (
    <Disclosure
      label="Check against local sources"
      onToggle={(e) => setOpened(e.currentTarget.open)}
      className="mt-4"
    >
      <p className="text-sm text-muted mb-3">
        Choose passages from your local library. The model reviews only listed claims; this does not verify
        the whole answer. Nothing is searched on the web.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          void search()
        }}
        className="space-y-2"
      >
        <label className="block" htmlFor={`source-query-${answerId}`}>
          Find local source passages
        </label>
        <input
          id={`source-query-${answerId}`}
          value={query}
          maxLength={500}
          disabled={!!busy}
          onChange={(e) => {
            setQuery(e.target.value)
            setHits([])
            setSearched(false)
          }}
          className="w-full rounded-panel border border-line bg-card px-3 py-2"
        />
        <Button type="submit" disabled={!!busy || !query.trim()}>
          Search local library
        </Button>
      </form>
      {searched && !hits.length && (
        <p role="status">
          No local passages found. Try different search words. This answer remains unchecked.
        </p>
      )}
      <div className="space-y-3 my-3">
        {hits.map((hit) => (
          <div key={hit.chunk_id} className="rounded-panel border border-line p-3">
            <label className="flex gap-2 items-start">
              <input
                type="checkbox"
                checked={selected.some((h) => h.chunk_id === hit.chunk_id)}
                disabled={
                  !!busy ||
                  hit.quarantined ||
                  (!selected.some((h) => h.chunk_id === hit.chunk_id) && selected.length >= 6)
                }
                onChange={(e) =>
                  setSelected((old) =>
                    e.target.checked ? [...old, hit] : old.filter((h) => h.chunk_id !== hit.chunk_id),
                  )
                }
              />
              <span className="break-words">{hit.citation}</span>
            </label>
            <p className="whitespace-pre-wrap break-words text-sm mt-2">{hit.text}</p>
            {hit.quarantined && <p className="text-sm">Excluded by the source trust setting.</p>}
          </div>
        ))}
      </div>
      {selected.length > 0 && (
        <section aria-label="Selected passages" className="space-y-2 my-3">
          <p>{selected.length} of 6 passages selected</p>
          {selected.map((hit) => (
            <div key={hit.chunk_id} className="flex gap-2 flex-wrap items-center">
              <span className="break-words">{hit.citation}</span>
              <Button
                disabled={!!busy}
                onClick={() => setSelected((old) => old.filter((h) => h.chunk_id !== hit.chunk_id))}
              >
                Remove {hit.citation}
              </Button>
            </div>
          ))}
        </section>
      )}
      <div className="flex gap-2 flex-wrap">
        <Button
          disabled={!!busy || !selected.length || !!recovery.pending || recovery.needsDiscard}
          onClick={() => void check()}
        >
          Review selected sources
        </Button>
        {busy && <Button onClick={stop}>Stop waiting</Button>}
      </div>
      {status && (
        <p role="status" className="my-2">
          {status}
        </p>
      )}
      {error && (
        <p role="alert" className="my-2">
          {error}
        </p>
      )}
      <RequestRecoveryControls
        recovery={recovery}
        busy={!!busy}
        originalContext="answer and selected passage identities"
        retry={() => {
          if (recovery.pending) void check(recovery.pending)
        }}
      />
      <section aria-label="Saved source reviews" className="space-y-3 mt-4">
        {history.isPending && opened && <p role="status">Loading saved reviews…</p>}
        {history.isError && (
          <p role="alert">
            Saved reviews could not be loaded.{' '}
            <Button onClick={() => void history.refetch()}>Retry loading reviews</Button>
          </p>
        )}
        {history.data?.items.map((item) => (
          <article key={item.id} className="border border-line rounded-panel p-3 space-y-2">
            <h3 className="font-semibold">
              Local model review · {new Date(item.created_at).toLocaleString()}
            </h3>
            <p>{item.note}</p>
            {item.binding_status !== 'unchanged' && (
              <p>Historical or unreadable check — do not rely on it for the current answer.</p>
            )}
            {item.passages?.some((p) => p.newer_version_available) && (
              <p>A source has a newer local version. This review used the older version.</p>
            )}
            {item.proposal?.claims.map((claim, index) => (
              <section key={index} className="border-t border-line pt-2">
                <blockquote className="break-words">{claim.claim_quote}</blockquote>
                <p className="font-medium">
                  Model judgment: {claim.verdict === 'insufficient' ? 'insufficient evidence' : claim.verdict}
                </p>
                <p className="break-words">{claim.explanation}</p>
                {claim.evidence?.map((evidence, i) => (
                  <div key={i} className="text-sm mt-2">
                    <p>
                      {item.passages?.find((p) => p.passage_id === evidence.passage_id)?.title ??
                        'Source unavailable'}
                    </p>
                    <blockquote className="break-words">{evidence.quote}</blockquote>
                  </div>
                ))}
              </section>
            ))}
            {item.proposal?.limitations?.map((text, i) => (
              <p key={i} className="text-sm break-words">
                Limitation: {text}
              </p>
            ))}
          </article>
        ))}
        {history.data && !history.data.items.length && <p>No saved source reviews yet.</p>}
        {history.data?.has_more && <p>Showing the latest 10 reviews.</p>}
      </section>
    </Disclosure>
  )
}
