import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { apiFetch, type Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'

const labels = {
  unchanged: 'Text matches the saved source',
  changed: 'Source text has changed',
  missing: 'Source passage is no longer available',
  unverifiable: 'No valid saved fingerprint to compare',
}

export function AnswerSourceStatus({ answerId }: { answerId: string }) {
  const [enabled, setEnabled] = useState(false)
  const query = useQuery({
    queryKey: ['answer-source-status', answerId],
    queryFn: ({ signal }) => apiFetch<Schemas['SavedSourceCheck']>(
      `/api/answers/${encodeURIComponent(answerId)}/source-status`, { signal },
    ),
    enabled,
  })
  return <section className="space-y-2 text-sm" aria-label="Saved source check">
    <Button disabled={query.isFetching} onClick={() => {
      if (enabled) void query.refetch()
      else setEnabled(true)
    }}>{query.isFetching ? 'Checking local sources…' : 'Check saved source text'}</Button>
    <p className="text-muted">Compares local source text only. Matching text does not establish that the answer is correct or that the source is up to date online.</p>
    <div aria-live="polite">
      {query.isError && <p>Could not check sources. Use the button to retry.</p>}
      {!query.isError && query.data && <>
        {query.data.sources.length === 0 && <p>No saved source references to compare. This answer has not been verified.</p>}
        <ul>{query.data.sources.map((source) => <li key={source.chunk_id}>
          <span className="break-all">{source.chunk_id}</span>: {labels[source.status]}
          {source.newer_version && ' — a newer local document version exists'}
        </li>)}</ul>
        {query.data.omitted > 0 && <p>{query.data.omitted} additional references were not checked.</p>}
      </>}
    </div>
  </section>
}
