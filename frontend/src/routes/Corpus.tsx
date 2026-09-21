import { useState } from 'react'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import {
  useCapabilities,
  useCorpusStats,
  useDocuments,
  useCancelIngestJob,
  useForgetDocument,
  useIngestJob,
  useIngestRuns,
  useRetierDocument,
  useSearch,
  useStartIngestJob,
  type IngestOut,
  type SearchHit,
} from '../features/corpus/api'

const TRUST_LABELS: Record<number, string> = {
  0: 'untrusted',
  1: 'web',
  2: 'course',
  3: 'owner-verified',
}

function Capabilities() {
  const caps = useCapabilities()
  if (!caps.data) return null
  const c = caps.data
  return (
    <div className="text-sm mb-3">
      <p className="text-muted">
        Captions and transcripts, documents (Word, PowerPoint, Excel, ODF, PDF, RTF, LaTeX), EPUB, HTML,
        notes, notebooks and source code, zip/tar archives, audio, video and slide images. Unchanged files are
        skipped; changed files get a new version. You decide the trust level, the files never do.
      </p>
      <ul className="mt-2 grid gap-1" aria-label="Optional runtimes">
        <li>
          <span className="font-medium">Audio/video transcription:</span>{' '}
          {c.stt.ready ? 'ready' : 'not ready'} — {c.stt.detail}
        </li>
        <li>
          <span className="font-medium">Slide images:</span> {c.vision.ready ? 'ready' : 'not ready'} —{' '}
          {c.vision.detail}
        </li>
      </ul>
      <details className="mt-2">
        <summary className="cursor-pointer">All supported file types</summary>
        <dl className="mt-2 grid gap-1">
          {Object.entries(c.formats).map(([group, suffixes]) => (
            <div key={group} className="flex flex-wrap gap-x-2">
              <dt className="font-medium">{group}:</dt>
              <dd className="text-muted">{suffixes.join(' ')}</dd>
            </div>
          ))}
          <div className="flex flex-wrap gap-x-2">
            <dt className="font-medium">not supported:</dt>
            <dd className="text-muted">
              {Object.entries(c.unsupported)
                .map(([s, hint]) => `${s} (${hint})`)
                .join(' · ')}
            </dd>
          </div>
        </dl>
      </details>
    </div>
  )
}

/** What each outcome class means for the owner — literal, one line each. */
const OUTCOME_LABELS: Record<string, string> = {
  imported: 'imported (new version stored)',
  unchanged: 'unchanged (same content as before)',
  reference_only: 'links only (references, not material)',
  no_content: 'nothing to keep (empty or no text)',
  unsupported: 'format not supported (see the hint)',
  gated: 'left out on purpose (caption present, media off, secret-looking)',
  retryable_error: 'try again later (runtime or I/O problem — a resume retries these)',
  access_blocked: 'needs you (permission denied or encrypted)',
  parser_error: 'could not be parsed (claimed format, broken file)',
}
const OUTCOME_ORDER = Object.keys(OUTCOME_LABELS)

function shortPath(p: string) {
  const parts = p.split('!/')
  const tail = parts[parts.length - 1].split('/').slice(-2).join('/')
  return parts.length > 1 ? `${parts[0].split('/').slice(-1)[0]} › ${tail}` : tail
}

function IngestReport({ out }: { out: IngestOut }) {
  const summary = out.summary as Record<string, unknown>
  const outcomes = (summary.outcomes ?? {}) as Record<string, number>
  const groups = OUTCOME_ORDER.filter((o) => out.skipped.some((s) => s.outcome === o))
  return (
    <div className="mt-3 text-sm">
      <p role="status">
        {String(summary.documents)} documents, {String(summary.new_versions)} new versions,{' '}
        {String(summary.chunks)} chunks ({String(summary.deduped)} duplicates dropped,{' '}
        {String(summary.flagged)} flagged, {String(summary.indexed)} indexed)
        {Number(summary.transcribed_media) > 0 &&
          ` · ${String(summary.transcribed_media)} media transcribed (${String(summary.audio_seconds)} s)`}
        {Number(summary.images_read) > 0 && ` · ${String(summary.images_read)} images read`}
        {out.skipped.length > 0 && ` · ${out.skipped.length} files skipped`}
        {Number(summary.resumed) > 0 && ` · ${String(summary.resumed)} already done before the resume`}
      </p>
      <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-1" aria-label="Outcomes">
        {OUTCOME_ORDER.filter((o) => outcomes[o] > 0).map((o) => (
          <li key={o}>
            <span className="font-medium">{outcomes[o]}</span> {OUTCOME_LABELS[o]}
          </li>
        ))}
      </ul>
      {groups.map((o) => (
        <details key={o} className="mt-2">
          <summary className="cursor-pointer">
            {OUTCOME_LABELS[o]}: {out.skipped.filter((s) => s.outcome === o).length}
          </summary>
          <ul className="mt-1 grid gap-1">
            {out.skipped
              .filter((s) => s.outcome === o)
              .slice(0, 50)
              .map((s) => (
                <li key={s.path}>
                  <span className="text-muted">{shortPath(s.path)}</span> — {s.reason}
                </li>
              ))}
            {out.skipped.filter((s) => s.outcome === o).length > 50 && (
              <li>… and {out.skipped.filter((s) => s.outcome === o).length - 50} more</li>
            )}
          </ul>
        </details>
      ))}
    </div>
  )
}

function IngestForm() {
  const start = useStartIngestJob()
  const cancel = useCancelIngestJob()
  const [jobId, setJobId] = useState<string | null>(null)
  const job = useIngestJob(jobId)
  const runs = useIngestRuns()
  const [path, setPath] = useState('')
  const [course, setCourse] = useState('')
  const [trust, setTrust] = useState(2)
  const [language, setLanguage] = useState('')
  const [media, setMedia] = useState(true)
  const [index, setIndex] = useState(true)
  const [stopRequested, setStopRequested] = useState(false)
  const active = job.data && (job.data.status === 'queued' || job.data.status === 'running')
  const progress = job.data?.progress
  const interrupted = (runs.data ?? []).filter((r) => r.status === 'interrupted')

  function launch(resumeRunId: string | null, src = path, courseName = course) {
    start.mutate(
      {
        path: src,
        course: courseName || null,
        trust_tier: trust,
        index,
        language: language.trim() || null,
        media,
        resume_run_id: resumeRunId,
      },
      {
        onSuccess: (j) => {
          setStopRequested(false)
          setJobId(j.job_id)
        },
      },
    )
  }

  return (
    <Card>
      <CardTitle>Ingest course material</CardTitle>
      <Capabilities />
      <form
        className="grid gap-3"
        onSubmit={(e) => {
          e.preventDefault()
          launch(null)
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
        <label className="text-sm font-medium">
          Transcription language (ISO code, empty = detect)
          <input
            className="block w-24 border border-line rounded-md px-2 py-1 mt-1"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            placeholder="en"
            maxLength={5}
          />
        </label>
        <label className="text-sm font-medium flex items-center gap-2">
          <input type="checkbox" checked={media} onChange={(e) => setMedia(e.target.checked)} />
          Transcribe audio/video and read images (slow; a run keeps going in the background)
        </label>
        <label className="text-sm font-medium flex items-center gap-2">
          <input type="checkbox" checked={index} onChange={(e) => setIndex(e.target.checked)} />
          Index into retrieval now (needs the embedding model; off = store only, reindex later)
        </label>
        <div className="flex gap-2 flex-wrap">
          <Button type="submit" variant="primary" disabled={start.isPending || !!active || !path}>
            {active ? 'Ingesting…' : 'Ingest'}
          </Button>
          {active && jobId && (
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setStopRequested(true)
                cancel.mutate(jobId)
              }}
              disabled={cancel.isPending || stopRequested}
            >
              {stopRequested ? 'Stopping after the current file…' : 'Stop after this file'}
            </Button>
          )}
        </div>
      </form>
      {start.isError && (
        <p role="alert" className="text-warn mt-2">
          {(start.error as Error).message}
        </p>
      )}
      {active && (
        <>
          {/* the per-file line changes every second: visible, but not announced on every poll */}
          <p className="text-sm mt-3" role="status" aria-live="off">
            {progress
              ? `File ${progress.done + 1} of ${progress.total}: ${shortPath(progress.current)}` +
                (progress.archive
                  ? ` · inside ${progress.archive}, member ${progress.member_done + 1} of ${progress.member_total}`
                  : '')
              : 'Starting the run…'}
          </p>
          {/* announced only when the outcome counts change (rarely), not on every file */}
          <p className="text-xs text-muted" aria-live="polite">
            {progress
              ? `So far ${
                  OUTCOME_ORDER.filter((o) => (progress.outcomes[o] ?? 0) > 0)
                    .map((o) => `${progress.outcomes[o]} ${o.replace('_', ' ')}`)
                    .join(', ') || 'nothing finished yet'
                }`
              : ''}
          </p>
        </>
      )}
      {job.data?.status === 'failed' && (
        <p role="alert" className="text-warn mt-2">
          The run failed: {job.data.error}. Nothing already imported was lost.
        </p>
      )}
      {job.data?.status === 'interrupted' && (
        <p role="status" className="text-sm text-warn mt-2">
          Stopped after the current file. Everything finished so far is kept; resume below to continue (a
          resume keeps the run's original settings and retries files marked "try again later").
        </p>
      )}
      {job.data?.result && <IngestReport out={job.data.result} />}
      {interrupted.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer">Interrupted runs you can resume ({interrupted.length})</summary>
          <ul className="mt-1 grid gap-1">
            {interrupted.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center gap-2">
                <span className="text-muted">{shortPath(r.src)}</span> {r.files_done} of {r.files_total} files
                done
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={!!active || start.isPending}
                  onClick={() => launch(r.id, r.src, r.course ?? '')}
                >
                  Resume
                </Button>
              </li>
            ))}
          </ul>
        </details>
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
