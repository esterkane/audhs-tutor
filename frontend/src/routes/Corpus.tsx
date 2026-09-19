import { useState } from 'react'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import {
  useCorpusStats,
  useDocuments,
  useForgetDocument,
  useIngest,
  useRetierDocument,
  useSearch,
  type SearchHit,
} from '../features/corpus/api'

const TRUST_LABELS: Record<number, string> = {
  0: 'untrusted',
  1: 'web',
  2: 'course',
  3: 'owner-verified',
}

function IngestForm() {
  const ingest = useIngest()
  const [path, setPath] = useState('')
  const [course, setCourse] = useState('')
  const [trust, setTrust] = useState(2)
  const summary = ingest.data?.summary as Record<string, unknown> | undefined
  return (
    <Card>
      <CardTitle>Ingest course material</CardTitle>
      <p className="text-sm text-muted mb-3">
        A folder laid out like a Udemy export (Course / Section / Lecture) with .vtt, .srt, .ipynb, .pdf, .md
        or .txt files. Unchanged files are skipped; changed files get a new version. You decide the trust
        level, the files never do.
      </p>
      <form
        className="grid gap-3"
        onSubmit={(e) => {
          e.preventDefault()
          ingest.mutate({ path, course: course || null, trust_tier: trust, index: true })
        }}
      >
        <label className="text-sm font-medium">
          Local path
          <input
            className="block w-full border border-line rounded-md px-2 py-1 mt-1"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/Users/you/Udemy or /Users/you/Udemy/Some Course"
            required
          />
        </label>
        <label className="text-sm font-medium">
          Course name (only when the path is the course folder itself)
          <input
            className="block w-full border border-line rounded-md px-2 py-1 mt-1"
            value={course}
            onChange={(e) => setCourse(e.target.value)}
          />
        </label>
        <label className="text-sm font-medium">
          Trust tier
          <select
            className="block border border-line rounded-md px-2 py-1 mt-1"
            value={trust}
            onChange={(e) => setTrust(Number(e.target.value))}
          >
            {[0, 1, 2, 3].map((t) => (
              <option key={t} value={t}>
                {t} · {TRUST_LABELS[t]}
              </option>
            ))}
          </select>
        </label>
        <div>
          <Button type="submit" variant="primary" disabled={ingest.isPending || !path}>
            {ingest.isPending ? 'Ingesting…' : 'Ingest'}
          </Button>
        </div>
      </form>
      {ingest.isError && (
        <p role="alert" className="text-warn mt-2">
          {(ingest.error as Error).message}
        </p>
      )}
      {summary && (
        <p className="text-sm mt-3" role="status">
          {String(summary.documents)} documents, {String(summary.new_versions)} new versions,{' '}
          {String(summary.chunks)} chunks ({String(summary.deduped)} duplicates dropped,{' '}
          {String(summary.flagged)} flagged, {String(summary.indexed)} indexed)
          {ingest.data && ingest.data.skipped.length > 0 && ` · ${ingest.data.skipped.length} files skipped`}
        </p>
      )}
    </Card>
  )
}

function Hit({ hit, index }: { hit: SearchHit; index: number }) {
  return (
    <li className="border border-line rounded-md p-3 text-sm">
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-muted">
        <span>[{index + 1}]</span>
        <span className="text-fg">{hit.citation}</span>
        <span>{hit.source_type}</span>
        <span>trust {hit.trust_tier}</span>
        <span>fused {hit.score.toFixed(3)}</span>
        {hit.dense_score != null && <span>dense {hit.dense_score.toFixed(3)}</span>}
        {hit.sparse_score != null && <span>sparse {hit.sparse_score.toFixed(3)}</span>}
        {hit.rerank_score != null && <span>rerank {hit.rerank_score.toFixed(3)}</span>}
        {hit.flagged.length > 0 && <span className="text-warn">flagged: {hit.flagged.join(', ')}</span>}
        {hit.quarantined && <span className="text-warn">withheld from the tutor</span>}
      </div>
      <p className="mt-2 whitespace-pre-wrap">{hit.text}</p>
    </li>
  )
}

function SearchPanel() {
  const search = useSearch()
  const [query, setQuery] = useState('')
  const [course, setCourse] = useState('')
  const [minTrust, setMinTrust] = useState(0)
  const [tutorView, setTutorView] = useState(false)
  return (
    <Card>
      <CardTitle>Inspect retrieval</CardTitle>
      <p className="text-sm text-muted mb-3">
        The same hybrid search the tutor uses, with its scores. By default it shows everything in the index;
        turn on "as the tutor sees it" to apply the tutor's trust floor and mark hits it would withhold.
      </p>
      <form
        className="flex flex-wrap gap-2 items-end"
        onSubmit={(e) => {
          e.preventDefault()
          search.mutate({
            query,
            k: 8,
            course: course || null,
            min_trust_tier: minTrust,
            tutor_view: tutorView,
          })
        }}
      >
        <label className="text-sm font-medium grow">
          Query
          <input
            className="block w-full border border-line rounded-md px-2 py-1 mt-1"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            required
          />
        </label>
        <label className="text-sm font-medium">
          Course
          <input
            className="block border border-line rounded-md px-2 py-1 mt-1"
            value={course}
            onChange={(e) => setCourse(e.target.value)}
            placeholder="all"
          />
        </label>
        <label className="text-sm font-medium">
          Min trust
          <select
            className="block border border-line rounded-md px-2 py-1 mt-1"
            value={minTrust}
            onChange={(e) => setMinTrust(Number(e.target.value))}
          >
            {[0, 1, 2, 3].map((t) => (
              <option key={t} value={t}>
                {t} · {TRUST_LABELS[t]}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium flex items-center gap-1 h-10">
          <input type="checkbox" checked={tutorView} onChange={(e) => setTutorView(e.target.checked)} />
          as the tutor sees it
        </label>
        <Button type="submit" variant="primary" disabled={search.isPending || !query}>
          Search
        </Button>
      </form>
      {search.isError && (
        <p role="alert" className="text-warn mt-2">
          {(search.error as Error).message}
        </p>
      )}
      {search.data && (
        <div className="mt-3">
          <p className="text-sm text-muted" role="status">
            {search.data.hits.length} hits in {search.data.latency_ms} ms from {search.data.collection}
            {search.data.reranked ? ' · reranked' : ''}
            {search.data.flagged_patterns.length > 0 &&
              ` · flagged: ${search.data.flagged_patterns.join(', ')}`}
          </p>
          <ol className="grid gap-2 mt-2">
            {search.data.hits.map((h, i) => (
              <Hit key={h.chunk_id} hit={h} index={i} />
            ))}
          </ol>
        </div>
      )}
    </Card>
  )
}

export function Corpus() {
  const stats = useCorpusStats()
  const [course, setCourse] = useState<string | null>(null)
  const docs = useDocuments(course)
  const forget = useForgetDocument()
  const retier = useRetierDocument()
  return (
    <div className="grid gap-4">
      <Card>
        <CardTitle>Corpus</CardTitle>
        {stats.isLoading && <p>Loading…</p>}
        {stats.data && (
          <>
            <p className="text-sm text-muted">
              {stats.data.documents} documents · {stats.data.chunks} chunks · {stats.data.flagged_chunks}{' '}
              flagged
              {stats.data.index
                ? ` · index ${stats.data.index.collection} (${stats.data.index_count ?? stats.data.index.chunk_count} vectors)`
                : ' · no index yet'}
              {` · reranker ${stats.data.retrieval.reranker ?? 'off'}`}
              {` · max ${stats.data.retrieval.max_per_document} hits per document`}
            </p>
            <p className="text-sm text-muted mt-1">
              Flagged = the chunk contains instruction-like text (for example "ignore previous instructions").
              Tier 0 is never sent to the tutor. Flagged chunks from tier 1 are withheld. Flagged chunks from
              tiers 2 and 3 are sent, quoted, with the flag shown next to the source.
            </p>
            {stats.data.courses.length === 0 ? (
              <p className="mt-2">Nothing ingested yet. Add a course below.</p>
            ) : (
              <ul className="mt-3 grid gap-2">
                {stats.data.courses.map((c) => (
                  <li key={c.course} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                    <Button
                      size="sm"
                      pressed={course === c.course}
                      onClick={() => setCourse(course === c.course ? null : c.course)}
                      aria-label={`Show documents of ${c.course}`}
                    >
                      {c.course}
                    </Button>
                    <span className="text-muted">
                      {c.documents} documents · {c.chunks} chunks · {c.source_types.join(', ')} · trust{' '}
                      {c.trust_tiers.map((t) => TRUST_LABELS[t] ?? t).join('/')}
                      {c.flagged > 0 && <span className="text-warn"> · {c.flagged} flagged</span>}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
        {course && docs.data && (
          <table className="mt-3 w-full text-sm">
            <caption className="text-left text-muted mb-1">Documents in {course}</caption>
            <thead>
              <tr className="text-left text-muted">
                <th scope="col" className="pr-2">
                  Section
                </th>
                <th scope="col" className="pr-2">
                  Lecture
                </th>
                <th scope="col" className="pr-2">
                  Type
                </th>
                <th scope="col" className="pr-2">
                  Version
                </th>
                <th scope="col" className="pr-2">
                  Trust
                </th>
                <th scope="col" className="pr-2">
                  Chunks
                </th>
                <th scope="col" className="pr-2">
                  Flagged
                </th>
                <th scope="col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {docs.data.documents.map((d) => (
                <tr key={d.id}>
                  <td className="pr-2">{d.section ?? '—'}</td>
                  <td className="pr-2">{d.lecture ?? d.title}</td>
                  <td className="pr-2">{d.source_type}</td>
                  <td className="pr-2">{d.version}</td>
                  <td className="pr-2">
                    <select
                      className="border border-line rounded-md px-1 py-0.5"
                      value={d.trust_tier}
                      aria-label={`Trust tier of ${d.lecture ?? d.title}`}
                      onChange={(e) =>
                        retier.mutate({ documentId: d.id, trust_tier: Number(e.target.value) })
                      }
                    >
                      {[0, 1, 2, 3].map((t) => (
                        <option key={t} value={t}>
                          {t} · {TRUST_LABELS[t]}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="pr-2">{d.chunks}</td>
                  <td className={d.flagged ? 'text-warn pr-2' : 'pr-2'}>{d.flagged}</td>
                  <td>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        if (window.confirm(`Remove "${d.lecture ?? d.title}" from the corpus?`))
                          forget.mutate(d.id)
                      }}
                      aria-label={`Remove ${d.lecture ?? d.title}`}
                    >
                      Remove
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      <details className="rounded-lg border border-line bg-card p-4 shadow-sm">
        <summary className="cursor-pointer font-medium">Add course material</summary>
        <div className="mt-3">
          <IngestForm />
        </div>
      </details>
      <details className="rounded-lg border border-line bg-card p-4 shadow-sm">
        <summary className="cursor-pointer font-medium">Inspect retrieval</summary>
        <div className="mt-3">
          <SearchPanel />
        </div>
      </details>
    </div>
  )
}
