import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { AnswerChildren } from './AnswerChildren'
afterEach(() => vi.unstubAllGlobals())
it('loads direct historical replies only on expansion without recommending or generating', async () => {
  const fetcher = vi.fn(async () => jsonResponse({ items: [{ id: 'child', learner_question: 'Check this argument', created_at: '2026-10-02T00:00:00Z' }], next_cursor: 'child' }))
  vi.stubGlobal('fetch', fetcher)
  renderApp(<AnswerChildren answerId="parent" />)
  expect(fetcher).not.toHaveBeenCalled()
  fireEvent.click(screen.getByText('Later replies to this answer'))
  expect(await screen.findByRole('link', { name: 'Check this argument' })).toHaveAttribute('href', '/answers/child')
  expect(fetcher).toHaveBeenCalledWith('/api/answers?parent_answer_id=parent&limit=5', expect.anything())
  expect(screen.getByRole('link', { name: 'Browse all direct follow-ups' })).toHaveAttribute('href', '/answers?parent_answer_id=parent')
  expect(screen.getByText(/not automatically a correction/)).toBeVisible()
})
it('distinguishes unavailable history from an empty list and offers retry', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(jsonResponse({ error: { message: 'Unavailable' } }, 503)).mockResolvedValue(jsonResponse({ items: [], next_cursor: null }))
  vi.stubGlobal('fetch', fetcher)
  renderApp(<AnswerChildren answerId="parent" />)
  fireEvent.click(screen.getByText('Later replies to this answer'))
  fireEvent.click(await screen.findByRole('button', { name: 'Retry follow-up history' }))
  expect(await screen.findByText('No saved direct follow-ups yet.')).toBeVisible()
})
