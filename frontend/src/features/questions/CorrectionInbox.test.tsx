import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { CorrectionInbox } from './CorrectionInbox'

const item = { id: 'r1', target: 'assessment', assessment_id: 'a1', draft_id: null,
  reported_question: 'Original wording', current_question: 'Corrected wording',
  content_status: 'changed', labels: ['incorrect'], note: 'My reason', created_at: '2026-10-08T10:00:00Z' }
afterEach(() => vi.unstubAllGlobals())

it('loads only on request and preserves loaded reports when refresh fails', async () => {
  let fail = false
  const fetcher = vi.fn(async () => fail
    ? jsonResponse({ error: { message: 'offline' } }, 503)
    : jsonResponse({ items: [item], total: 1, offset: 0, limit: 20 }))
  vi.stubGlobal('fetch', fetcher)
  renderApp(<CorrectionInbox />)
  expect(fetcher).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Show question reports' }))
  await screen.findByText('Original wording')
  expect(screen.getByText('Corrected wording')).toBeVisible()
  expect(screen.getByText('Your note: My reason')).toBeVisible()
  fail = true
  fireEvent.click(screen.getByRole('button', { name: 'Refresh question reports' }))
  await screen.findByRole('alert')
  expect(screen.getByText('Original wording')).toBeVisible()
  fail = false
  fireEvent.click(screen.getByRole('button', { name: 'Refresh question reports' }))
  await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
})

it('paginates explicitly and returns focus without treating unavailable content as resolved', async () => {
  const paths: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    paths.push(path)
    return jsonResponse(path.includes('offset=20')
      ? { items: [{ ...item, id: 'last', current_question: null, content_status: 'unavailable', reported_question: 'Last report' }], total: 21, offset: 20, limit: 20 }
      : { items: Array.from({ length: 20 }, (_, i) => ({ ...item, id: String(i) })), total: 21, offset: 0, limit: 20 })
  }))
  renderApp(<CorrectionInbox />)
  fireEvent.click(screen.getByRole('button', { name: 'Show question reports' }))
  fireEvent.click(await screen.findByRole('button', { name: 'More reports' }))
  await screen.findByText('Last report')
  expect(screen.getByText('Current content unavailable; your report is preserved.')).toBeVisible()
  await waitFor(() => expect(screen.getByRole('heading', { name: 'Reported questions' })).toHaveFocus())
  expect(paths).toHaveLength(2)
  fireEvent.click(screen.getByRole('button', { name: 'Previous reports' }))
  await screen.findByRole('button', { name: 'More reports' })
})
