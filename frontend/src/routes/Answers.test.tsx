import { fireEvent, screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../test/utils'
import { Answers } from './Answers'

vi.mock('../features/programs/AnswerFeedback', () => ({ AnswerFeedback: () => null }))
vi.mock('../features/programs/AnswerFollowup', () => ({ AnswerFollowup: () => null }))
vi.mock('../features/voice/ReadAloud', () => ({ ReadAloud: () => <button>Listen</button> }))
afterEach(() => vi.unstubAllGlobals())
const summary = {
  id: 'a1',
  request_text: 'Why clean this data?',
  surface: 'playground',
  created_at: '2026-10-01T10:00:00Z',
  preview: 'Keep group representation in mind.',
}
function open(route = '/answers') {
  return renderApp(
    <Routes>
      <Route path="/answers" element={<Answers />} />
      <Route path="/answers/:answerId" element={<Answers />} />
    </Routes>,
    { route },
  )
}

it('reopens exact saved work and returns to its filtered history without generating', async () => {
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    expect(init?.method ?? 'GET').toBe('GET')
    if (url === '/api/answers/a1')
      return jsonResponse({
        ...summary,
        text: 'The old explanation.',
        request: { code: 'print(groups)', output: 'old output', output_stale: true, learner_answer: 'I retained 30 of 50 rows.' },
        metadata: {},
        turn_id: 't1',
      })
    expect(url).toContain('/api/answers?')
    expect(url).toContain('surface=playground')
    return jsonResponse({ items: [summary], next_cursor: null })
  })
  vi.stubGlobal('fetch', fetcher)
  open('/answers?surface=playground')
  fireEvent.click(await screen.findByRole('link', { name: 'Why clean this data?' }))
  expect(await screen.findByText('The old explanation.')).toBeVisible()
  fireEvent.click(screen.getByText('Your submitted answer at the time'))
  expect(screen.getByText('I retained 30 of 50 rows.')).toBeVisible()
  expect(screen.getByRole('heading', { name: 'Request at the time' })).toBeVisible()
  fireEvent.click(screen.getByText('Material and code supplied at the time'))
  expect(screen.getByText('print(groups)')).toBeVisible()
  expect(screen.getByText(/already marked as belonging to earlier code/)).toBeVisible()
  fireEvent.click(screen.getByRole('link', { name: 'Back to saved answers' }))
  expect(await screen.findByLabelText('Show')).toHaveValue('playground')
  expect(fetcher.mock.calls.every(([url]) => url.startsWith('/api/answers'))).toBe(true)
})

it('retries failure, pages older answers, and clears the cursor when filtering', async () => {
  let failed = true
  const fetcher = vi.fn(async (url: string) => {
    if (failed) return jsonResponse({}, 503)
    return jsonResponse({ items: [summary], next_cursor: url.includes('cursor=') ? null : 'a1' })
  })
  vi.stubGlobal('fetch', fetcher)
  open()
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load saved answers')
  failed = false
  fireEvent.click(screen.getByRole('button', { name: 'Retry history' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Older answers' }))
  await waitFor(() => expect(fetcher.mock.calls.some(([url]) => url.includes('cursor=a1'))).toBe(true))
  fireEvent.change(screen.getByLabelText('Show'), { target: { value: 'tutor' } })
  await waitFor(() => expect(fetcher.mock.calls.at(-1)?.[0]).toBe('/api/answers?surface=tutor&limit=20'))
})

it('shows an honest empty state', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse({ items: [], next_cursor: null })),
  )
  open()
  expect(await screen.findByText(/No saved answers in this view/)).toBeVisible()
})

it.each([404, 503])('distinguishes unavailable records from service errors (%s)', async (status) => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse({}, status)),
  )
  open('/answers/missing')
  expect(await screen.findByRole('alert')).toHaveTextContent(
    status === 404 ? 'This saved answer is unavailable.' : 'Could not load this answer.',
  )
  expect(screen.queryByText('The old explanation.')).not.toBeInTheDocument()
})

it('preserves follow-up context and historical source qualifications', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      jsonResponse({
        ...summary,
        request_text: 'Why?',
        text: 'Because groups differ.',
        request: {
          history: [
            { role: 'user', text: 'Does cleaning affect representation?' },
            { role: 'assistant', text: 'Compare the groups first.' },
          ],
        },
        metadata: {
          sources: [{ chunk_id: 'c1', citation: 'Sample note', cited: false, flagged: ['untrusted'] }],
          dropped: ['c2:quarantined'],
        },
        turn_id: 't1',
      }),
    ),
  )
  open('/answers/a1')
  await screen.findByText('Because groups differ.')
  fireEvent.click(screen.getByText('Conversation supplied at the time'))
  expect(screen.getByText('Does cleaning affect representation?')).toBeVisible()
  expect(screen.getByText('Compare the groups first.')).toBeVisible()
  fireEvent.click(screen.getByText('Source references'))
  expect(screen.getByText(/not cited in the answer/)).toBeVisible()
  expect(screen.getByText(/flagged: untrusted/)).toBeVisible()
  expect(screen.getByText(/1 source withheld/)).toBeVisible()
  expect(screen.getByText(/current corpus copy/)).toBeVisible()
})

it('submits search explicitly and retains it through answer opening and return', async () => {
  const fetcher = vi.fn(async (url: string) =>
    url === '/api/answers/a1'
      ? jsonResponse({ ...summary, text: 'Saved reply', request: {}, metadata: {}, turn_id: 't1' })
      : jsonResponse({ items: [summary], next_cursor: null }),
  )
  vi.stubGlobal('fetch', fetcher)
  open('/answers?surface=playground&cursor=old')
  await screen.findByRole('link', { name: 'Why clean this data?' })
  fireEvent.change(screen.getByLabelText('Search saved answers'), { target: { value: 'groups' } })
  expect(fetcher.mock.calls).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: 'Search' }))
  await waitFor(() => expect(fetcher.mock.calls.at(-1)?.[0]).toContain('q=groups'))
  expect(fetcher.mock.calls.at(-1)?.[0]).not.toContain('cursor=')
  fireEvent.click(await screen.findByRole('link', { name: 'Why clean this data?' }))
  await screen.findByText('Saved reply')
  fireEvent.click(screen.getByRole('link', { name: 'Back to saved answers' }))
  expect(await screen.findByLabelText('Search saved answers')).toHaveValue('groups')
  fireEvent.click(screen.getByRole('button', { name: 'Clear search' }))
  await waitFor(() => expect(fetcher.mock.calls.at(-1)?.[0]).not.toContain('q='))
})
it('retains the exact historical memory snapshot when reopening a generated reply', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({
    ...summary, text: 'New response', request: {}, metadata: { answer_memory: [{
      answer_id: 'old', saved_at: '2026-10-01T09:00:00Z', question: 'Which group?', excerpt: 'Exact prior excerpt',
    }] },
  })))
  open('/answers/a1')
  fireEvent.click(await screen.findByText('Previous tutor answers supplied as context'))
  expect(screen.getByText('Exact prior excerpt')).toBeVisible()
  expect(screen.getByText(/not independent evidence/)).toBeVisible()
  expect(screen.getByRole('link', { name: 'Open previous answer' })).toHaveAttribute('href', '/answers/old')
})


it('filters alternative explanations and keeps unknown historical provenance explicit', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url === '/api/answers/a1') return jsonResponse({ ...summary, surface: 'representation', text: 'Old analogy [1].', request: {}, metadata: { provenance_available: false }, turn_id: 'representation:s:r' })
    expect(url).toContain('surface=representation')
    return jsonResponse({ items: [{ ...summary, surface: 'representation' }], next_cursor: null })
  }))
  open('/answers?surface=representation')
  expect(await screen.findByLabelText('Show')).toHaveValue('representation')
  fireEvent.click(await screen.findByRole('link', { name: 'Why clean this data?' }))
  expect(await screen.findByText(/Original source details were not recorded/)).toBeVisible()
  expect(screen.getByText('Old analogy [1].')).toBeVisible()
})
