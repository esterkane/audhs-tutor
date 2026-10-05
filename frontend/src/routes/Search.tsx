import { SkillSearch } from '../features/skills/SkillSearch'
import { ProjectSearch } from '../features/programs/ProjectSearch'
import { useAreas } from '../features/areas/api'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../components/ui/button'
import type { Schemas } from '../lib/api'
import { boundedRead } from '../lib/boundedRead'

export function Search() {
  const [params, setParams] = useSearchParams()
  const query = params.get('q')?.trim() ?? ''
  return <div className="grid gap-4 min-w-0">
    <h1 className="text-page-title font-semibold">Search material</h1>
    <p>Find knowledge areas, skills, project guides, saved tutor explanations and passages in your indexed sources.</p>
    <p className="text-sm text-muted">Searches local material, not the web. Notebook edits, unsaved chats, project notes and saved thoughts are not searched here.</p>
    <SearchForm key={`form:${query}`} initial={query} onSearch={q => setParams(q ? { q } : {})} />
    {!query ? <p>Enter a phrase to search your local material.</p> : query.length > 200 ? <p role="alert">Use a search of 200 characters or fewer.</p> : <Results key={`results:${query}`} query={query} />}
    <p className="text-sm">Browse instead: <Link className="underline" to="/areas">Learning areas</Link> · <Link className="underline" to="/programs">Project study</Link> · <Link className="underline" to="/map">Skill map</Link></p>
  </div>
}
function SearchForm({ initial, onSearch }: { initial: string; onSearch: (q: string) => void }) {
  const [value, setValue] = useState(initial)
  return <form className="flex flex-wrap items-end gap-2" onSubmit={event => { event.preventDefault(); onSearch(value.trim()) }}>
    <label className="grow min-w-0">Search phrase
      <input type="search" className="block w-full min-h-10 mt-1 rounded-md border border-control bg-card px-3 py-2" value={value} onChange={event => setValue(event.target.value)} maxLength={200} required />
    </label>
    <Button disabled={!value.trim() || value.trim().length > 200} type="submit">Search</Button>
    {initial && <Button variant="secondary" type="button" onClick={() => onSearch('')}>Clear search</Button>}
  </form>
}
function Results({ query }: { query: string }) {
  const areas = useAreas()
  const matchingAreas = (areas.data?.areas ?? []).filter(area => [area.title, area.description, ...area.terms].some(text => text.toLocaleLowerCase().includes(query.toLocaleLowerCase())))
  const answers = useQuery({
    queryKey: ['material-search', 'answers', query],
    queryFn: ({ signal }) => boundedRead<Schemas['AnswerPage']>(`/api/answers?${new URLSearchParams({ q: query, limit: '8' })}`, signal, 'Saved answer search'),
    retry: false,
  })
  const sources = useQuery({
    queryKey: ['material-search', 'sources', query],
    queryFn: ({ signal }) => boundedRead<Schemas['SearchOut']>('/api/corpus/search', signal, 'Source search', { method: 'POST', body: JSON.stringify({ query, k: 8, tutor_view: false } satisfies Schemas['SearchRequest']) }),
    retry: false,
  })
  return <div className="grid gap-4 min-w-0">
    <nav aria-label="Search result groups" className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
      <span className="font-semibold">Jump to:</span>
      {([['areas', 'Knowledge areas'], ['skills', 'Skills'], ['projects', 'Project guides'], ['answers', 'Saved explanations'], ['sources', 'Indexed sources']] as const).map(([id, label]) =>
        <a key={id} className="underline py-1" href={`#search-${id}`}>{label}</a>)}
    </nav>
    <section aria-labelledby="search-areas" className="rounded-md border border-line p-3 min-w-0 break-words">
      <h2 tabIndex={-1} id="search-areas" className="text-panel-heading font-semibold">Knowledge areas</h2>
      <p className="text-sm text-muted">Names, descriptions and topic terms matching your phrase. Opening an area does not start or switch a learning session.</p>
      {areas.isError && <div role="alert">Knowledge areas could not be refreshed. <Button disabled={areas.isFetching} onClick={() => void areas.refetch()}>Retry area search</Button>{areas.data && <p>Showing previously loaded results; they may be out of date.</p>}</div>}
      {areas.isPending ? <p role="status">Searching knowledge areas…</p> : areas.data ? <>
        <p role="status">{matchingAreas.length ? `${Math.min(8, matchingAreas.length)} of ${matchingAreas.length} matching areas shown.` : 'No knowledge areas matched.'}</p>
        <ul className="grid gap-3 my-2">{matchingAreas.slice(0, 8).map(area => <li key={area.id}>
          <Link className="underline" to={`/areas?${new URLSearchParams({ area: area.id })}`}>{area.title}</Link>
          {area.description && <p className="text-sm">{area.description}</p>}
        </li>)}</ul>
        {matchingAreas.length > 8 && <Link className="underline" to="/areas">Browse all knowledge areas</Link>}
      </> : null}
    </section>
    <SkillSearch phrase={query} />
    <ProjectSearch phrase={query} />
    <section aria-labelledby="search-answers" className="rounded-md border border-line p-3 min-w-0 break-words">
      <h2 tabIndex={-1} id="search-answers" className="text-panel-heading font-semibold">Saved explanations</h2>
      <p className="text-sm text-muted">Past answers matching your words, newest first. They have not been checked again.</p>
      {answers.isError && <div role="alert">Saved explanations could not be searched. <Button disabled={answers.isFetching} onClick={() => void answers.refetch()}>Retry explanation search</Button>{answers.data && <p>Showing previously loaded results; they may be out of date.</p>}</div>}
      {answers.isPending ? <p role="status">Searching saved explanations…</p> : answers.data ? <>
        <p role="status">{answers.data.items.length ? `${answers.data.items.length} matching saved explanations shown.` : 'No saved explanations matched.'}</p>
        <ul className="grid gap-3 my-2">{answers.data.items.map(answer => <li key={answer.id}>
          <Link className="underline" to={`/answers/${encodeURIComponent(answer.id)}?${new URLSearchParams({ q: query })}`}>{answer.request_text || 'Saved explanation'}</Link>
          <p className="text-sm">{answer.preview}</p>
        </li>)}</ul>
        {answers.data.next_cursor && <Link className="underline" to={`/answers?${new URLSearchParams({ q: query })}`}>See all matching saved explanations</Link>}
      </> : null}
    </section>
    <section aria-labelledby="search-sources" className="rounded-md border border-line p-3 min-w-0 break-words">
      <h2 tabIndex={-1} id="search-sources" className="text-panel-heading font-semibold">Indexed sources</h2>
      <p className="text-sm text-muted">Up to 8 potentially relevant passages. A match is not verification of the source.</p>
      {sources.isError && <div role="alert">Source search is unavailable. Check the local retrieval service and embedding model. <Button disabled={sources.isFetching} onClick={() => void sources.refetch()}>Retry source search</Button>{sources.data && <p>Showing previously loaded results; they may be out of date.</p>}</div>}
      {sources.isPending ? <p role="status">Searching indexed sources…</p> : sources.data ? <>
        <p role="status">{sources.data.hits.length ? `${sources.data.hits.length} source passages shown.` : 'No indexed passages matched.'}</p>
        <ul className="grid gap-3 my-2">{sources.data.hits.map(hit => <li key={hit.chunk_id}>
          <Link className="underline" to={`/sources?${new URLSearchParams({ chunk: hit.chunk_id })}`}>{hit.citation}</Link>
          <p className="text-sm text-muted">{hit.source_type}</p>
          {!!hit.flagged.length && <p className="text-sm">Source warnings — inspect before relying on this passage.</p>}
          {hit.quarantined && <p className="text-sm">Withheld from tutor context.</p>}
          <p className="text-sm whitespace-pre-wrap">{hit.text.slice(0, 500)}{hit.text.length > 500 ? '…' : ''}</p>
        </li>)}</ul>
      </> : null}
    </section>
  </div>
}
