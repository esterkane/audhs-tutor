import { fireEvent, screen } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
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
      source_types: ['udemy_caption'],
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
      source_type: 'udemy_caption',
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
  },
  results: [],
  skipped: [{ path: '/x/Course/Lecture 1/talk.mkv', reason: '.mkv needs ffmpeg' }],
}

describe('Corpus', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows course stats, flags, and inspectable search hits with scores', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/corpus/ingest')) {
          ingestBodies.push(JSON.parse(String(init?.body)))
          return jsonResponse(ingestOut)
        }
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
    expect(await screen.findByText(/1 media transcribed \(61.5 s\)/)).toBeInTheDocument()
    expect(ingestBodies[0]).toMatchObject({ path: '/x/Course', language: 'de', media: false, trust_tier: 2 })
    fireEvent.click(screen.getByText('Skipped files and why', { selector: 'summary' }))
    expect(screen.getByText(/needs ffmpeg/)).toBeInTheDocument()
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
