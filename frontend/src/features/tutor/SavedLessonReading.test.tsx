import { fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { useSavedReading } from '../representations/api'
import { SavedLessonReading } from './SavedLessonReading'

vi.mock('./LessonReader', () => ({ LessonReader: ({ text, identity }: { text: string; identity: string }) => <div data-testid="reader" data-identity={identity}>{text}</div> }))
const saved = { object_id: 'object', object_version: 1, content_sha256: 'hash', concept: 'Fit', goal: 'Protect held-out data', passages: ['Fit on training records.', 'Apply the same median.'], source_ids: [], activation_id: 'activation', draft_id: 'draft', answer_id: 'answer' }
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
function setup() {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Harness() { return <SavedLessonReading reading={useSavedReading('skill')} active hasReply={false} /> }
  render(<QueryClientProvider client={cache}><MemoryRouter><Harness /></MemoryRouter></QueryClientProvider>)
  return cache
}
it('shows saved content and origin with no mutation or generation', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(saved)))
  vi.stubGlobal('fetch', fetch)
  setup()
  expect(await screen.findByTestId('reader')).toHaveTextContent('Fit on training records.')
  expect(screen.getByRole('link', { name: 'Original saved answer' })).toHaveAttribute('href', '/answers/answer')
  expect(screen.getByText(/do not verify accuracy/)).toBeInTheDocument()
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(fetch.mock.calls[0][0]).toBe('/api/objects/skill/reading')
})
it('preserves loaded reading on refresh failure and accepts explicit retry', async () => {
  let failed = false
  vi.stubGlobal('fetch', vi.fn(async () => failed ? new Response('{}', { status: 503 }) : new Response(JSON.stringify(saved))))
  const cache = setup()
  await screen.findByTestId('reader')
  failed = true
  await cache.invalidateQueries({ queryKey: ['lesson-reading', 'skill'] })
  await screen.findByRole('alert')
  expect(screen.getByTestId('reader')).toHaveTextContent('Apply the same median.')
  failed = false
  fireEvent.click(screen.getByRole('button', { name: 'Retry saved lesson' }))
  await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
})
it('does not invent saved content for a shared lesson', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('null')))
  const cache = setup()
  await waitFor(() => expect(cache.getQueryState(['lesson-reading', 'skill'])?.status).toBe('success'))
  expect(screen.queryByTestId('reader')).not.toBeInTheDocument()
})
