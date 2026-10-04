import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { SourceViewer } from '../features/curriculum/SourceViewer'
import type { Schemas } from '../lib/api'
import { boundedRead } from '../lib/boundedRead'

export function Sources() {
  const [params, setParams] = useSearchParams()
  const direct = params.get('chunk')
  const directRegion = useRef<HTMLElement>(null)
  useEffect(() => { if (direct !== null) directRegion.current?.focus() }, [direct])
  const applied = params.get('q')?.trim() ?? ''
  return <div className="grid gap-4">
    <h1 className="text-2xl font-semibold">Sources</h1>
    <p>Find passages in your indexed material and inspect their source details.</p>
    <p className="text-sm text-muted">Searches the local retrieval index, not the web or saved tutor answers. Up to 8 matching passages are shown; a match is not a verification of the source.</p>
    {direct !== null && <section ref={directRegion} tabIndex={-1} aria-label="Saved source passage">
      {/^[A-Za-z0-9_.:-]{1,128}$/.test(direct) ? <SourceViewer key={direct} chunkId={direct} citation="Saved source passage" onClose={() => { const next = new URLSearchParams(params); next.delete('chunk'); setParams(next) }} /> : <p role="alert">This saved passage identifier is invalid. Search your source material below.</p>}
      <p className="text-sm text-muted">If the passage has been removed or re-ingested, search your source material below.</p>
    </section>}
    <SourceSearch key={`search:${applied}`} initial={applied} onSearch={q => {
      const next = new URLSearchParams()
      if (q) next.set('q', q)
      setParams(next)
    }} />
    {applied.length > 500 ? <p role="alert">Use a search of 500 characters or fewer.</p> : <SourceResults key={`results:${applied}`} query={applied} passage={params.get('passage') ?? ''} onPassage={id => {
      const next = new URLSearchParams(params)
      if (id) next.set('passage', id)
      else next.delete('passage')
      setParams(next)
    }} />}
    <p className="text-sm"><Link className="underline" to="/answers">Search saved tutor answers</Link> · <Link className="underline" to="/corpus">Manage imports and source settings</Link></p>
  </div>
}

function SourceSearch({ initial, onSearch }: { initial: string; onSearch: (q: string) => void }) {
  const [value, setValue] = useState(initial)
  return <form className="flex flex-wrap items-end gap-2" onSubmit={event => { event.preventDefault(); onSearch(value.trim()) }}>
    <label className="min-w-0 grow">Search source material
      <input type="search" className="block w-full mt-1 min-h-10 rounded-md border border-control bg-card px-3 py-2" required maxLength={500} value={value} onChange={event => setValue(event.target.value)} />
    </label>
    <Button type="submit" disabled={!value.trim() || value.trim().length > 500}>Search sources</Button>
    {initial && <Button type="button" variant="secondary" onClick={() => onSearch('')}>Clear search</Button>}
  </form>
}

function SourceResults({ query, passage, onPassage }: { query: string; passage: string; onPassage: (id: string) => void }) {
  const results = useQuery({
    queryKey: ['library-sources', query],
    queryFn: ({ signal }) => boundedRead<Schemas['SearchOut']>('/api/corpus/search', signal, 'Source search', {
      method: 'POST', body: JSON.stringify({ query, k: 8, tutor_view: false } satisfies Schemas['SearchRequest']),
    }),
    enabled: !!query,
    retry: false,
    staleTime: 60_000,
  })
  const detail = useRef<HTMLDivElement>(null)
  const triggers = useRef(new Map<string, HTMLButtonElement>())
  const selected = results.data?.hits.find(hit => hit.chunk_id === passage)
  useEffect(() => { if (selected) detail.current?.focus() }, [selected])
  if (!query) return <p>Enter a topic or phrase to find source material.</p>
  if (results.isPending) return <p role="status">Searching source material…</p>
  if (results.isError) return <div role="alert">
    <p>Source search is temporarily unavailable. Retry or check your imports.</p>
    <p className="text-sm text-muted">If retrying fails, check that the local retrieval service and embedding model are running.</p>
    <Button onClick={() => void results.refetch()} disabled={results.isFetching}>Retry source search</Button>
  </div>
  return <div className="grid gap-3">
    <p role="status">{results.data.hits.length ? `Potentially relevant passages for “${query}”` : `No indexed passages matched “${query}”. Try another phrase or check your imports.`}</p>
    {passage && !selected && <p role="status">The selected passage is no longer in these search results. Choose a result below.</p>}
    {selected && <div ref={detail} tabIndex={-1} className="min-w-0 break-words" aria-label="Selected source passage">
      <SourceViewer key={selected.chunk_id} chunkId={selected.chunk_id} citation={selected.citation} onClose={() => {
        onPassage('')
        triggers.current.get(selected.chunk_id)?.focus()
      }} />
    </div>}
    <ol className="grid gap-3">
      {results.data.hits.map(hit => <li key={hit.chunk_id}>
        <Card className="min-w-0 break-words">
          <h2 className="font-medium">{hit.citation}</h2>
          <p className="text-sm text-muted">{hit.source_type}</p>
          {!!hit.flagged.length && <p className="text-sm">This passage has source warnings. Inspect it before relying on it.</p>}
          {hit.quarantined && <p className="text-sm">Withheld from tutor context.</p>}
          <p className="mt-2 whitespace-pre-wrap">{hit.text.slice(0, 500)}{hit.text.length > 500 ? '…' : ''}</p>
          <Button className="mt-2" asChild><button type="button" ref={element => { if (element) triggers.current.set(hit.chunk_id, element); else triggers.current.delete(hit.chunk_id) }} onClick={() => onPassage(hit.chunk_id)} aria-label={`Read passage: ${hit.citation}`}>Read passage</button></Button>
        </Card>
      </li>)}
    </ol>
  </div>
}
