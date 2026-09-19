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

describe('Corpus', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows course stats, flags, and inspectable search hits with scores', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/api/corpus/stats')) return jsonResponse(stats)
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
