import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { jsonResponse, renderApp } from '../../test/utils'
import { SourceViewer } from './SourceViewer'

const chunk = {
  chunk_id: 'c1',
  text: 'Transformers from Scratch › Attention\nWe divide by the square root of d k.',
  citation: '[Transformers from Scratch › Attention › Self-attention @00:12]',
  course: 'Transformers from Scratch',
  section: 'Attention',
  lecture: 'Self-attention',
  source_type: 'udemy_caption',
  trust_tier: 2,
  document_title: 'Self-attention',
  uri: '/Users/x/Udemy/Course/Section/lecture.en.vtt',
  open_url: 'file:///Users/x/Udemy/Course/Section/lecture.en.vtt',
  t_start: 12,
  t_end: 40,
  prev_text: 'Scores come from query-key dot products.',
  next_text: 'Then softmax turns scores into weights.',
  available: true,
}

describe('SourceViewer', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows the cited passage with neighbours, a timestamp, a guarded link, and files a report', async () => {
    const posts: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/curriculum/chunks/c1')) return jsonResponse(chunk)
        if (url.endsWith('/api/curriculum/reports')) {
          posts.push(JSON.parse(String(init?.body)))
          return jsonResponse(
            {
              id: 'r1',
              kind: 'wrong_source',
              turn_id: 't1',
              chunk_id: 'c1',
              skill_id: null,
              note: 'x',
              status: 'open',
              created_at: 'now',
            },
            201,
          )
        }
        return jsonResponse({ error: { code: 'not_found', message: 'gone' } }, 404)
      }),
    )
    const onClose = vi.fn()
    const { container } = renderApp(
      <SourceViewer chunkId="c1" citation="[cit]" turnId="t1" onClose={onClose} />,
    )
    expect(await screen.findByText(/We divide by the square root/)).toBeInTheDocument()
    expect(screen.getByText(/at 00:12–00:40/)).toBeInTheDocument()
    expect(screen.getByText(/Scores come from query-key/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open the original \(lecture.en.vtt\)/ })).toHaveAttribute(
      'href',
      'file:///Users/x/Udemy/Course/Section/lecture.en.vtt',
    )
    expect(await axe(container)).toHaveNoViolations()
    fireEvent.click(screen.getByRole('button', { name: /Report this source as wrong/ }))
    fireEvent.change(screen.getByLabelText(/What is wrong/), { target: { value: 'wrong lecture' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send report' }))
    await waitFor(() => expect(posts).toHaveLength(1))
    expect(posts[0]).toMatchObject({
      kind: 'wrong_source',
      chunk_id: 'c1',
      turn_id: 't1',
      note: 'wrong lecture',
    })
    expect(await screen.findByText(/Reported\. It stays on record/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(onClose).toHaveBeenCalled()
  })

  it('falls back to the citation when the passage is gone', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse({ error: { code: 'not_found', message: 'gone' } }, 404)),
    )
    renderApp(<SourceViewer chunkId="missing" citation="[Course › Lecture @01:00]" onClose={() => {}} />)
    expect(await screen.findByText(/no longer in the corpus/)).toBeInTheDocument()
    expect(screen.getByText('[Course › Lecture @01:00]')).toBeInTheDocument()
  })
})
