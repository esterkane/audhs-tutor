import { act, fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { jsonResponse, renderApp } from '../test/utils'
import { useMode } from '../stores/mode'
import { Learn } from './Learn'

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })
function mount() {
  useMode.setState({ sessionId: 'stale', skillId: 'stale' })
  return renderApp(<Routes>
    <Route path="/learn" element={<Learn />} />
    <Route path="/" element={<h1>Home destination</h1>} />
    <Route path="/session" element={<h1>Session destination</h1>} />
    <Route path="/review" element={<h1>Review destination</h1>} />
    <Route path="/recap" element={<h1>Recap destination</h1>} />
  </Routes>, { route: '/learn' })
}
it.each([
  ['teach', false, 'Session'], ['review', false, 'Review'],
  ['recap', false, 'Recap'], ['teach', true, 'Recap'],
])('routes server %s complete=%s', async (phase, plan_complete, destination) => {
  const fetcher = vi.fn().mockResolvedValue(jsonResponse({ id: 'actual', state: { phase, plan_complete, block_status: 'running', skill_id: 'actual-skill' } }))
  vi.stubGlobal('fetch', fetcher)
  mount()
  await screen.findByRole('heading', { name: `${destination} destination` })
  expect(useMode.getState().sessionId).toBe('actual')
  expect(fetcher).toHaveBeenCalledTimes(1)
  expect(fetcher.mock.calls[0][0]).toBe('/api/sessions/current')
})
it('returns to Home when no session exists', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(null)))
  mount()
  await screen.findByRole('heading', { name: 'Home destination' })
})
it('offers retry without using stale identity', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(jsonResponse({}, 503)).mockResolvedValueOnce(jsonResponse(null)))
  mount()
  await screen.findByRole('alert')
  expect(useMode.getState().sessionId).toBe('stale')
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  await screen.findByRole('heading', { name: 'Home destination' })
})
it('leaving during a slow read prevents a late redirect', async () => {
  let resolve!: (response: Response) => void
  let signal: AbortSignal | undefined
  vi.stubGlobal('fetch', vi.fn((_url, init) => { signal = init.signal; return new Promise<Response>(done => { resolve = done }) }))
  mount()
  expect(screen.getByRole('status')).toHaveTextContent('Checking')
  fireEvent.click(screen.getByRole('link', { name: 'Return Home' }))
  expect(signal?.aborted).toBe(true)
  resolve(jsonResponse({ id: 'late', state: { phase: 'teach' } }))
  await screen.findByRole('heading', { name: 'Home destination' })
  expect(useMode.getState().sessionId).toBe('stale')
})

it('bounds a stalled response body and allows retry', async () => {
  vi.useFakeTimers()
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: true, json: () => new Promise(() => {}) }).mockResolvedValueOnce(jsonResponse(null)))
  mount()
  await act(async () => { await vi.advanceTimersByTimeAsync(15001) })
  await act(async () => { await vi.advanceTimersByTimeAsync(1) })
  expect(screen.getByRole('alert')).toBeVisible()
  vi.useRealTimers()
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  await screen.findByRole('heading', { name: 'Home destination' })
})
