import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { PlanRecovery } from './PlanReview'
const preview = { id: 'updated', session_id: 'bound-session', why: 'Only future activities change.', plan_blocks: [{ type: 'learn', planned_min: 10 }, { type: 'review', planned_min: 3 }], protected_blocks: 1 }
afterEach(() => vi.unstubAllGlobals())
it('previews without accepting, focuses the preview, then applies only by separate choice', async () => {
  const writes: Array<{ url: string; body: unknown }> = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === 'POST') writes.push({ url, body: init.body ? JSON.parse(String(init.body)) : null })
    return jsonResponse(url.endsWith('/refresh-plan') ? preview : { entries: [] })
  }))
  renderApp(<PlanRecovery id="original" fromUndo />)
  expect(screen.queryByRole('button', { name: 'Apply reviewed plan' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Review an updated plan' }))
  const heading = await screen.findByRole('heading', { name: 'Updated plan — not applied' })
  await waitFor(() => expect(heading).toHaveFocus())
  expect(writes).toHaveLength(1)
  expect(writes[0].url).toContain('/original/refresh-plan')
  expect(screen.getByText('review · 3 min')).toBeVisible()
  expect(screen.queryByText('learn · 10 min')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Apply reviewed plan' }))
  expect(await screen.findByRole('status')).toHaveTextContent('Updated plan applied')
  expect(writes[1]).toEqual({ url: expect.stringContaining('/updated/decide'), body: { decision: 'try', session_id: 'bound-session' } })
  expect(screen.getByRole('button', { name: 'Apply reviewed plan' })).toBeDisabled()
})
it('shows decline errors before a preview exists', async () => {
  vi.stubGlobal('fetch', vi.fn(async (_url: string, init?: RequestInit) => init?.method === 'POST' ? jsonResponse({ error: { code: 'unavailable', message: 'Please retry later.' } }, 503) : jsonResponse({ entries: [] })))
  renderApp(<PlanRecovery id="original" />)
  fireEvent.click(screen.getByRole('button', { name: 'Not now' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Please retry later.')
})
it('requires a new preview after another session advance', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url.endsWith('/refresh-plan')) return jsonResponse(preview)
    if (url.endsWith('/decide')) return jsonResponse({ error: { code: 'stale_plan', message: 'The session changed again.' } }, 409)
    return jsonResponse({ entries: [] })
  }))
  renderApp(<PlanRecovery id="original" fromUndo />)
  fireEvent.click(screen.getByRole('button', { name: 'Review an updated plan' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Apply reviewed plan' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('The session changed again.')
  expect(screen.getByRole('button', { name: 'Apply reviewed plan' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Review an updated plan' })).toBeEnabled()
})
