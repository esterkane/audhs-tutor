import { fireEvent, screen, waitFor } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Link, Route, Routes } from 'react-router-dom'
import { jsonResponse, renderApp } from '../test/utils'
import { Corpus } from './Corpus'

const stats = {
  retrieval: { collection: 'corpus_v1', reranker: null, max_per_document: 3 },
  documents: 2,
  versions: 2,
  chunks: 9,
  flagged_chunks: 1,
  courses: [
    {
      course: 'Transformers from Scratch',
      documents: 2,
      chunks: 9,
      flagged: 1,
      source_types: ['course_caption'],
      trust_tiers: [2],
    },
  ],
  index: {
    collection: 'corpus_v1',
    embedding_registry_id: 'nomic',
    embedding_version: 1,
    dims: 768,
    chunk_count: 9,
    last_reindex: null,
  },
  index_count: 9,
}

const search = {
  query: 'scaled dot product',
  hits: [
    {
      chunk_id: 'c1',
      rank: 0,
      score: 0.032,
      dense_score: 0.81,
      sparse_score: 4.2,
      rerank_score: null,
      citation: '[Transformers from Scratch › Attention › Self-attention @00:12]',
      course: 'Transformers from Scratch',
      section: 'Attention',
      lecture: 'Self-attention',
      source_type: 'course_caption',
      trust_tier: 2,
      t_start: 12,
      flagged: ['ignore_previous'],
      quarantined: false,
      text: 'We divide by the square root of d k.',
    },
  ],
  latency_ms: 21,
  reranked: false,
  flagged_patterns: ['ignore_previous'],
  collection: 'corpus_v1',
}

const capabilities = {
  formats: { documents: ['.pdf', '.docx'], 'audio (transcribed)': ['.mp3', '.wav'] },
  unsupported: { '.rar': 'extract it first (zip/tar are supported)' },
  archives: ['.zip'],
  audio: ['.mp3'],
  video: ['.mp4'],
  images: ['.png'],
  stt: {
    ready: false,
    registry_id: null,
    detail: 'no ready speech-to-text model — Models › pull whisper-large-v3-turbo',
    package_installed: false,
  },
  vision: { ready: false, registry_id: null, detail: 'no ready vision model — Models › pull gemma3-12b' },
  audio_decoder: 'afconvert',
  legacy_office: 'textutil',
  image_converter: 'sips',
}

const ingestBodies: unknown[] = []
const ingestOut = {
  summary: {
    documents: 2,
    new_versions: 2,
    chunks: 5,
    deduped: 0,
    flagged: 0,
    indexed: 5,
    transcribed_media: 1,
    audio_seconds: 61.5,
    images_read: 0,
    outcomes: { imported: 2, unchanged: 0, retryable_error: 1, unsupported: 1 },
  },
  results: [],
  skipped: [
    { path: '/x/Course/Lecture 1/talk.mkv', reason: '.mkv needs ffmpeg', outcome: 'retryable_error' },
    { path: '/x/Course/Lecture 1/book.mobi', reason: 'unsupported file type: .mobi', outcome: 'unsupported' },
  ],
}
let jobPolls = 0

describe('Corpus', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('shows course stats, flags, and inspectable search hits with scores', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/corpus/ingest/jobs') && init?.method === 'POST') {
          ingestBodies.push(JSON.parse(String(init?.body)))
          return jsonResponse({ job_id: 'j1', run_id: null, status: 'queued', started_at: 't' })
        }
        if (url.endsWith('/api/corpus/ingest/jobs/j1')) {
          jobPolls += 1
          if (jobPolls === 1)
            return jsonResponse({
              job_id: 'j1',
              run_id: 'r1',
              status: 'running',
              started_at: 't',
              progress: {
                done: 1,
                total: 3,
                current: '/x/Course/Lecture 1/talk.mkv',
                outcomes: { imported: 1 },
                archive: null,
                member_done: 0,
                member_total: 0,
              },
            })
          return jsonResponse({
            job_id: 'j1',
            run_id: 'r1',
            status: 'finished',
            started_at: 't',
            result: ingestOut,
          })
        }
        if (url.endsWith('/api/corpus/ingest/runs')) return jsonResponse([])
        if (url.endsWith('/api/corpus/stats')) return jsonResponse(stats)
        if (url.endsWith('/api/corpus/capabilities')) return jsonResponse(capabilities)
        if (url.endsWith('/api/corpus/search')) return jsonResponse(search)
        return jsonResponse({ documents: [] })
      }),
    )
    const { container } = renderApp(
      <Routes>
        <Route path="/corpus" element={<Corpus />} />
      </Routes>,
      { route: '/corpus' },
    )
    expect(await screen.findByText(/2 documents · 9 chunks · 1 flagged/)).toBeInTheDocument()
    expect(screen.getByText(/Flagged = the chunk contains instruction-like text/)).toBeInTheDocument()
    // readiness of optional runtimes is stated as text with the next step, before any ingest
    expect(await screen.findByText(/pull whisper-large-v3-turbo/)).toBeInTheDocument()
    expect(screen.getByText(/pull gemma3-12b/)).toBeInTheDocument()
    const formats = screen.getByText('All supported file types', { selector: 'summary' })
    expect(formats.closest('details')).not.toHaveAttribute('open')
    fireEvent.click(formats)
    expect(screen.getByText(/\.rar \(extract it first/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Transcription language/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Transcribe audio\/video/)).toBeChecked()
    // the form sends language + media, and the report explains every skipped file
    fireEvent.change(screen.getByLabelText('Local path'), { target: { value: '/x/Course' } })
    fireEvent.change(screen.getByLabelText(/Transcription language/), { target: { value: 'de' } })
    fireEvent.click(screen.getByLabelText(/Transcribe audio\/video/))
    fireEvent.click(screen.getByRole('button', { name: 'Ingest' }))
    // the run reports what it is doing while it runs, then its outcome classes
    expect(await screen.findByText(/File 2 of 3: Lecture 1\/talk.mkv/)).toBeInTheDocument()
    expect(screen.getByText(/So far 1 imported/)).toBeInTheDocument()
    expect(
      await screen.findByText(/1 media transcribed \(61.5 s\)/, {}, { timeout: 4000 }),
    ).toBeInTheDocument()
    expect(ingestBodies[0]).toMatchObject({
      path: '/x/Course',
      language: 'de',
      media: false,
      trust_tier: 2,
      index: true,
      resume_run_id: null,
    })
    expect(screen.getByRole('list', { name: 'Outcomes' })).toHaveTextContent(/2 imported/)
    fireEvent.click(
      screen.getByText(/try again later \(runtime or I\/O problem — a resume retries these\): 1/, {
        selector: 'summary',
      }),
    )
    expect(screen.getByText(/needs ffmpeg/)).toBeInTheDocument()
    expect(screen.getByText(/format not supported \(see the hint\): 1/)).toBeInTheDocument()
    // secondary tasks are collapsed by default (one task per screen)
    const inspect = screen.getByText('Inspect retrieval', { selector: 'summary' })
    expect(inspect.closest('details')).not.toHaveAttribute('open')
    fireEvent.click(inspect)
    expect(
      screen.getByText(/index corpus_v1 \(9 vectors\) · reranker off · max 3 hits per document/),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Transformers from Scratch/ })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Query'), { target: { value: 'scaled dot product' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByText(/1 hits in 21 ms/)).toBeInTheDocument()
    expect(screen.getByText(/Self-attention @00:12/)).toBeInTheDocument()
    expect(screen.getByText(/dense 0.810/)).toBeInTheDocument()
    expect(screen.getAllByText(/flagged: ignore_previous/)).toHaveLength(2) // hit + summary
    expect(await axe(container)).toHaveNoViolations()
  })
})

it('recovers a running job from its link and remembers it across remounts without starting another', async () => {
  localStorage.clear()
  const fetchMock = vi.fn(async (url: string) => {
    if (url.endsWith('/ingest/jobs/recovered'))
      return jsonResponse({
        job_id: 'recovered',
        status: 'running',
        progress: {
          done: 4,
          total: 10,
          current: '/course/notes.md',
          outcomes: { imported: 4 },
        },
      })
    if (url.endsWith('/stats')) return jsonResponse(stats)
    if (url.endsWith('/capabilities')) return jsonResponse(capabilities)
    return jsonResponse([])
  })
  vi.stubGlobal('fetch', fetchMock)
  const first = renderApp(<Corpus />, { route: '/corpus?ingestJob=recovered' })
  expect(await screen.findByText(/File 5 of 10/)).toBeVisible()
  expect(screen.getByRole('button', { name: 'Stop after this file' })).toBeEnabled()
  first.unmount()
  renderApp(<Corpus />, { route: '/corpus' })
  expect(await screen.findByText(/File 5 of 10/)).toBeVisible()
  expect(fetchMock.mock.calls.every((call) => !call[0].endsWith('/ingest/jobs'))).toBe(true)
  localStorage.clear()
  vi.unstubAllGlobals()
})

it('keeps a job accepted after navigation and follows a new job link on the same route', async () => {
  localStorage.clear()
  let accept!: (response: Response) => void
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/ingest/jobs') && init?.method === 'POST')
        return new Promise<Response>((resolve) => {
          accept = resolve
        })
      if (url.includes('/ingest/jobs/'))
        return jsonResponse({
          job_id: url.split('/').pop(),
          status: 'running',
          progress: {
            done: url.endsWith('/second') ? 7 : 2,
            total: 10,
            current: '/course/notes.md',
            outcomes: {},
          },
        })
      if (url.endsWith('/stats')) return jsonResponse(stats)
      if (url.endsWith('/capabilities')) return jsonResponse(capabilities)
      return jsonResponse([])
    }),
  )
  renderApp(
    <>
      <Link to="/away">Leave</Link>
      <Link to="/corpus">Return</Link>
      <Link to="/corpus?ingestJob=second">Second job</Link>
      <Routes>
        <Route path="/corpus" element={<Corpus />} />
        <Route path="/away" element={<p>Away</p>} />
      </Routes>
    </>,
    { route: '/corpus' },
  )
  fireEvent.change(await screen.findByLabelText('Local path'), { target: { value: '/course' } })
  fireEvent.click(screen.getByRole('button', { name: /^Ingest$/ }))
  await waitFor(() => expect(accept).toBeDefined())
  fireEvent.click(screen.getByText('Leave'))
  accept(jsonResponse({ job_id: 'first', status: 'queued' }))
  await waitFor(() => expect(localStorage.getItem('audhs:corpus:last-job')).toBe('first'))
  fireEvent.click(screen.getByText('Return'))
  expect(await screen.findByText(/File 3 of 10/)).toBeVisible()
  fireEvent.click(screen.getByText('Second job'))
  expect(await screen.findByText(/File 8 of 10/)).toBeVisible()
  localStorage.clear()
  vi.unstubAllGlobals()
})
