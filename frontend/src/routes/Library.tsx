import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '../components/ui/button'
import { useDrafts } from '../features/curriculum/api'
import { useSkills } from '../features/skills/api'
import { SourceViewer } from '../features/curriculum/SourceViewer'
import { boundedRead } from '../lib/boundedRead'
import type { Schemas } from '../lib/api'

function displayCitation(value: string) {
  const characters = Array.from(value)
  return characters.length > 120
    ? characters.slice(0, 96).join('') + '…' + characters.slice(-20).join('')
    : value
}

const linkStyle =
  'inline-flex max-w-full min-w-0 min-h-11 items-center whitespace-normal [overflow-wrap:anywhere] underline'
export function Library() {
  const [params, setParams] = useSearchParams()
  const query = params.get('q')?.trim() ?? ''
  const passage = params.get('passage') ?? params.get('chunk')
  const detail = useRef<HTMLElement>(null)
  const previous = useRef<string | null>(null)
  const cache = useQueryClient()
  useEffect(() => {
    if (passage !== null) detail.current?.focus()
    else if (previous.current) document.getElementById('library-source-' + previous.current)?.focus()
    previous.current = passage
  }, [passage])
  function search(value: string) {
    if (value && value === query) {
      for (const key of [
        ['curriculum', 'drafts'],
        ['skills'],
        ['library-search', 'answers', query],
        ['library-search', 'sources', query],
      ])
        void cache.invalidateQueries({ queryKey: key })
    }
    setParams(value ? { q: value } : {})
  }
  return (
    <div className="grid gap-4 min-w-0">
      <h1 className="text-page-title font-semibold">Library</h1>
      <div hidden={passage !== null} className="grid gap-4">
        <p>Search local material, saved answers and source passages in one place.</p>
        <SearchForm key={'form:' + query} initial={query} onSearch={search} />
        <Link className={linkStyle + ' font-semibold'} to="/curriculum">
          Create or continue knowledge material
        </Link>
        {query.length > 200 ? (
          <p role="alert">Use a search of 200 characters or fewer.</p>
        ) : query ? (
          <Results
            key={'results:' + query}
            query={query}
            onOpen={(id) => {
              const next = new URLSearchParams(params)
              next.delete('chunk')
              next.set('passage', id)
              setParams(next)
            }}
          />
        ) : (
          <RecentMaterial />
        )}
        <details>
          <summary className="cursor-pointer">Import and other library views</summary>
          <p className="text-sm mt-3">
            Search includes saved knowledge drafts, lesson titles, saved answers and indexed passages. Project
            and notebook edits, unsaved writing and the web are not included.
          </p>
          <nav aria-label="Other library views" className="grid gap-2 mt-3">
            <Link className={linkStyle} to="/corpus">
              Import and manage source files
            </Link>
            <Link className={linkStyle} to="/answers">
              Browse saved answers
            </Link>
            <Link className={linkStyle} to="/areas">
              Learning areas
            </Link>
            <Link className={linkStyle} to="/explore">
              Explore material by area
            </Link>
          </nav>
        </details>
      </div>
      {passage !== null && (
        <section ref={detail} tabIndex={-1} aria-label="Selected source passage" className="min-w-0 break-words [overflow-wrap:anywhere]">
          {/^[A-Za-z0-9_.:-]{1,128}$/.test(passage) ? (
            <SourceViewer
              key={passage}
              chunkId={passage}
              citation="Source passage"
              onClose={() => {
                const next = new URLSearchParams(params)
                next.delete('passage')
                next.delete('chunk')
                setParams(next)
              }}
            />
          ) : (
            <p role="alert">This saved passage identifier is invalid.</p>
          )}
          <Link
            className={linkStyle}
            to={query ? `/library?${new URLSearchParams({ q: query })}` : '/library'}
          >
            Back to Library results
          </Link>
        </section>
      )}
    </div>
  )
}
function SearchForm({ initial, onSearch }: { initial: string; onSearch: (query: string) => void }) {
  const [value, setValue] = useState(initial)
  return (
    <form
      className="flex flex-wrap items-end gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        onSearch(value.trim())
      }}
    >
      <label className="grow min-w-0">
        Search phrase
        <input
          type="search"
          value={value}
          maxLength={200}
          required
          onChange={(event) => setValue(event.target.value)}
          className="block w-full min-h-control-target mt-1 rounded-md border border-control bg-card px-3 py-2"
        />
      </label>
      <Button type="submit" disabled={!value.trim() || value.trim().length > 200}>
        Search
      </Button>
      {initial && (
        <Button type="button" variant="secondary" onClick={() => onSearch('')}>
          Clear search
        </Button>
      )}
    </form>
  )
}
function RecentMaterial() {
  const drafts = useDrafts()
  const recent = (drafts.data?.drafts ?? [])
    .filter((row) => row.origin === 'knowledge_authored' && row.status !== 'published')
    .slice(0, 5)
  return (
    <section aria-label="Recent material">
      <h2 className="text-panel-heading font-semibold">Continue writing</h2>
      {drafts.isPending && <p role="status">Loading your material…</p>}
      {drafts.isError && (
        <p role="alert">
          Your material could not load.{' '}
          <Button disabled={drafts.isFetching} onClick={() => void drafts.refetch()}>
            Retry material
          </Button>
        </p>
      )}
      {recent.length ? (
        <ul>
          {recent.map((row) => (
            <li key={row.id}>
              <Link className={linkStyle} to={`/curriculum?${new URLSearchParams({ draft: row.id })}`}>
                {row.title}
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        !drafts.isPending &&
        !drafts.isError && <p>Start with your notes or an optional upload. Saved drafts will appear here.</p>
      )}
    </section>
  )
}
function Results({ query, onOpen }: { query: string; onOpen: (id: string) => void }) {
  const drafts = useDrafts(),
    skills = useSkills()
  const term = query.toLocaleLowerCase()
  const own = (drafts.data?.drafts ?? []).filter(
    (row) =>
      row.origin === 'knowledge_authored' &&
      row.status !== 'published' &&
      (row.title + ' ' + JSON.stringify(row.payload)).toLocaleLowerCase().includes(term),
  )
  const lessons = (skills.data?.skills ?? []).filter((row) =>
    (row.title + ' ' + row.description).toLocaleLowerCase().includes(term),
  )
  const answers = useQuery({
    queryKey: ['library-search', 'answers', query],
    retry: false,
    queryFn: ({ signal }) =>
      boundedRead<Schemas['AnswerPage']>(
        `/api/answers?${new URLSearchParams({ q: query, limit: '8' })}`,
        signal,
        'Saved answer search',
      ),
  })
  const sources = useQuery({
    queryKey: ['library-search', 'sources', query],
    retry: false,
    queryFn: ({ signal }) =>
      boundedRead<Schemas['SearchOut']>('/api/corpus/search', signal, 'Source search', {
        method: 'POST',
        body: JSON.stringify({ query, k: 8, tutor_view: false } satisfies Schemas['SearchRequest']),
      }),
  })
  return (
    <div className="grid gap-4 min-w-0">
      <p className="text-sm text-muted">
        Local results. Saved answers and source matches are references, not new factual checks.
      </p>
      <nav aria-label="Search result groups" className="flex flex-wrap gap-3">
        {[
          ['material', 'My material'],
          ['answers', 'Saved answers'],
          ['sources', 'Source passages'],
        ].map(([id, label]) => (
          <a key={id} className={linkStyle} href={'#search-' + id}>
            {label}
          </a>
        ))}
      </nav>
      <section
        aria-labelledby="search-material"
        className="rounded border border-line p-3 min-w-0 break-words"
      >
        <h2 id="search-material" tabIndex={-1} className="font-semibold">
          My material
        </h2>
        {(drafts.isError || skills.isError) && (
          <div role="alert">
            Some material could not refresh.{' '}
            <Button
              disabled={drafts.isFetching || skills.isFetching}
              onClick={() => {
                void drafts.refetch()
                void skills.refetch()
              }}
            >
              Retry material search
            </Button>
            {(drafts.data || skills.data) && (
              <p>Showing previously loaded results; they may be out of date.</p>
            )}
          </div>
        )}
        {(drafts.isPending || skills.isPending) && <p role="status">Searching your material…</p>}
        {!drafts.isPending &&
          !skills.isPending &&
          !drafts.isError &&
          !skills.isError &&
          !own.length &&
          !lessons.length && <p>No material matched.</p>}
        <ul className="grid gap-2">
          {own.slice(0, 8).map((row) => (
            <li key={'draft:' + row.id}>
              <span className="text-sm text-muted">
                {row.status === 'rejected' ? 'Inactive draft' : 'Draft'} ·{' '}
              </span>
              <Link className={linkStyle} to={`/curriculum?${new URLSearchParams({ draft: row.id })}`}>
                {row.title}
              </Link>
            </li>
          ))}
          {lessons.slice(0, 8).map((row) => (
            <li key={'lesson:' + row.id}>
              <span className="text-sm text-muted">Lesson · </span>
              <Link className={linkStyle} to={`/?${new URLSearchParams({ lesson: row.id })}`}>
                {row.title}
              </Link>
              {!row.unlocked && <p className="text-sm text-muted">Prerequisites are not yet met.</p>}
            </li>
          ))}
        </ul>
        {(own.length > 8 || lessons.length > 8) && (
          <p>Showing up to eight drafts and eight lessons. Refine the search to narrow them.</p>
        )}
      </section>
      <section
        aria-labelledby="search-answers"
        className="rounded border border-line p-3 min-w-0 break-words"
      >
        <h2 id="search-answers" tabIndex={-1} className="font-semibold">
          Saved answers
        </h2>
        {answers.isPending && <p role="status">Searching saved answers…</p>}
        {answers.isError && (
          <div role="alert">
            Saved answers could not refresh.{' '}
            <Button disabled={answers.isFetching} onClick={() => void answers.refetch()}>
              Retry answer search
            </Button>
            {answers.data && <p>Showing previously loaded results; they may be out of date.</p>}
          </div>
        )}
        {answers.data && (
          <>
            <p>{answers.data.items.length} found</p>
            <ul>
              {answers.data.items.map((row) => (
                <li key={row.id}>
                  <Link
                    className={linkStyle}
                    to={`/answers/${encodeURIComponent(row.id)}?${new URLSearchParams({ q: query })}`}
                  >
                    {row.request_text || 'Saved answer'}
                  </Link>
                  <p>{row.preview}</p>
                </li>
              ))}
            </ul>
            {answers.data.next_cursor && (
              <Link className={linkStyle} to={`/answers?${new URLSearchParams({ q: query })}`}>
                All matching saved answers
              </Link>
            )}
          </>
        )}
      </section>
      <section
        aria-labelledby="search-sources"
        className="rounded border border-line p-3 min-w-0 break-words"
      >
        <h2 id="search-sources" tabIndex={-1} className="font-semibold">
          Source passages
        </h2>
        {sources.isPending && <p role="status">Searching source passages…</p>}
        {sources.isError && (
          <div role="alert">
            Source search is unavailable.{' '}
            <Button disabled={sources.isFetching} onClick={() => void sources.refetch()}>
              Retry source search
            </Button>
            {sources.data && <p>Showing previously loaded results; they may be out of date.</p>}
          </div>
        )}
        {sources.data && (
          <>
            <p>
              {sources.data.hits.length
                ? `${sources.data.hits.length} found`
                : 'No indexed passages matched.'}
            </p>
            <ul className="grid gap-3">
              {sources.data.hits.map((hit) => (
                <li key={hit.chunk_id}>
                  <Button
                    className="max-w-full min-w-0 whitespace-normal [overflow-wrap:anywhere] text-left"
                    id={'library-source-' + hit.chunk_id}
                    variant="ghost"
                    onClick={() => onOpen(hit.chunk_id)}
                    aria-label={'Read passage: ' + hit.citation}
                  >
                    {displayCitation(hit.citation)}
                  </Button>
                  {!!hit.flagged.length && <p>Source warnings — inspect before relying on this passage.</p>}
                  {hit.quarantined && <p>Withheld from tutor context.</p>}
                  <p className="whitespace-pre-wrap text-sm">
                    {hit.text.slice(0, 240)}
                    {hit.text.length > 240 ? '…' : ''}
                  </p>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  )
}
