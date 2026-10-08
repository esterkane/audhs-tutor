import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp, jsonResponse } from '../../test/utils'
import { CorrectionImpact } from './CorrectionImpact'

const impact = { draft_id: 'd', revision: 2, affected_reviews: 3, linked_exercises: 1,
  passages: [{ reference: 'c', status: 'available', text: 'Source evidence', document_version_id: 'v', truncated: true }],
  review: { source_status: 'unchanged', problems: [], content_changed: false, question_state_changed: false } }
afterEach(() => vi.unstubAllGlobals())
it('loads only explicitly and labels unsaved work and limited source evidence', async () => {
  const fetcher = vi.fn(async () => jsonResponse(impact)); vi.stubGlobal('fetch', fetcher)
  renderApp(<CorrectionImpact id="d" revision={2} dirty />)
  expect(fetcher).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Load impact preview' }))
  expect(await screen.findByText(/3 active review card/)).toBeVisible()
  expect(screen.getByText(/does not represent your current edits/)).toBeVisible()
  fireEvent.click(screen.getByText('Source c · available'))
  expect(screen.getByText('Source evidence')).toBeVisible()
  expect(screen.getByText(/not the complete passage/)).toBeVisible()
})
it('retains the prior preview with an explicit error on failed refresh', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(jsonResponse(impact)).mockRejectedValueOnce(new Error('offline')))
  renderApp(<CorrectionImpact id="d" revision={3} dirty={false} />)
  fireEvent.click(screen.getByRole('button', { name: 'Load impact preview' }))
  await screen.findByText(/3 active review card/)
  fireEvent.click(screen.getByRole('button', { name: 'Refresh impact preview' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Your edits are kept')
  expect(screen.getByText(/3 active review card/)).toBeVisible()
  expect(screen.getByText(/does not represent your current edits/)).toBeVisible()
})
it('requires explicit source confirmation and clears it on refresh', async () => {
  const onPublish = vi.fn()
  vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ ...impact, publication_available: true, preview_token: 'ac1.' + 'a'.repeat(64) })))
  renderApp(<CorrectionImpact id="d" revision={2} dirty={false} onPublish={onPublish} />)
  fireEvent.click(screen.getByRole('button', { name: 'Load impact preview' }))
  const publish = await screen.findByRole('button', { name: 'Publish correction for my practice' })
  expect(publish).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox'))
  expect(publish).toBeEnabled()
  fireEvent.click(publish); fireEvent.click(publish)
  expect(onPublish).toHaveBeenCalledTimes(1)
  expect(publish).toBeDisabled()
})
