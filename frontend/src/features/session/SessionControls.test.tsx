import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Link, Routes, Route } from 'react-router-dom'
import { renderApp, jsonResponse } from '../../test/utils'
import { useMode } from '../../stores/mode'
import { SessionControls } from './SessionControls'
afterEach(() => vi.unstubAllGlobals())
it('stops without an assessment or recap rating and returns to topic selection', async () => {
  useMode.setState({ sessionId: 's1' })
  const calls: Array<[string, unknown]> = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === 'POST') calls.push([url, JSON.parse(String(init.body))])
      return jsonResponse(url.endsWith('/preferences') ? { values: {}, specs: [] } : { ended_at: 'now' })
    }),
  )
  renderApp(
    <Routes>
      <Route path="/session" element={<SessionControls sessionId="s1" skillId="k1" />} />
      <Route path="/" element={<p>Choose your topic</p>} />
    </Routes>,
    { route: '/session' },
  )
  fireEvent.click(screen.getByRole('button', { name: 'Change topic' }))
  expect(await screen.findByText('Choose your topic')).toBeVisible()
  await waitFor(() => expect(calls).toEqual([['/api/sessions/s1/end', {}]]))
  expect(useMode.getState().sessionId).toBeNull()
})

it('pauses without ending, rating or clearing the active session', async () => {
  useMode.setState({ sessionId: 's1', skillId: 'k1' })
  const calls: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    calls.push(url)
    return jsonResponse({ values: {}, specs: [] })
  }))
  renderApp(
    <Routes>
      <Route path="/session" element={<SessionControls sessionId="s1" skillId="k1" />} />
      <Route path="/" element={<p>Resume from Home</p>} />
    </Routes>,
    { route: '/session' },
  )
  fireEvent.click(screen.getByRole('button', { name: 'Pause and return Home' }))
  expect(await screen.findByText('Resume from Home')).toBeVisible()
  expect(useMode.getState().sessionId).toBe('s1')
  expect(useMode.getState().skillId).toBe('k1')
  expect(calls.every((url) => url.endsWith('/preferences'))).toBe(true)
})

for (const newerSession of [false, true]) it(`late End cannot override navigation or a newer session (${newerSession})`, async () => {
  useMode.setState({ sessionId: 's1', skillId: 'k1' })
  let release!: (response: Response) => void
  const response = new Promise<Response>(resolve => { release = resolve })
  vi.stubGlobal('fetch', vi.fn((url: string) => url.endsWith('/end') ? response : Promise.resolve(jsonResponse({ values: {}, specs: [] }))))
  renderApp(<Routes>
    <Route path="/session" element={<><SessionControls sessionId="s1" /><Link to="/preferences">Preferences</Link></>} />
    <Route path="/preferences" element={<p>Preferences destination</p>} />
    <Route path="/" element={<p>Home destination</p>} />
  </Routes>, { route: '/session' })
  fireEvent.click(screen.getByRole('button', { name: 'End session' }))
  await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/sessions/s1/end', expect.anything()))
  fireEvent.click(screen.getByRole('link', { name: 'Preferences' }))
  await screen.findByText('Preferences destination')
  if (newerSession) useMode.setState({ sessionId: 's2', skillId: 'k2' })
  await act(async () => { release(jsonResponse({ ended_at: 'now' })); await response })
  expect(screen.getByText('Preferences destination')).toBeVisible()
  expect(useMode.getState().sessionId).toBe(newerSession ? 's2' : null)
  if (newerSession) expect(useMode.getState().skillId).toBe('k2')
})

for (const historyChange of ['push', 'back-forward'] as const) it(`End respects ${historyChange} before React unmounts`, async () => {
  useMode.setState({ sessionId: 's1' })
  let release!: (response: Response) => void
  const response = new Promise<Response>(resolve => { release = resolve })
  vi.stubGlobal('fetch', vi.fn((url: string) => url.endsWith('/end') ? response : Promise.resolve(jsonResponse({ values: {}, specs: [] }))))
  const oldState = window.history.state
  const oldUrl = window.location.href
  renderApp(<Routes>
    <Route path="/session" element={<SessionControls sessionId="s1" />} />
    <Route path="/" element={<p>Home destination</p>} />
  </Routes>, { route: '/session' })
  fireEvent.click(screen.getByRole('button', { name: 'End session' }))
  await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/sessions/s1/end', expect.anything()))
  try {
    if (historyChange === 'push') window.history.replaceState({ key: 'new-entry' }, '', '/preferences')
    else window.dispatchEvent(new PopStateEvent('popstate'))
    await act(async () => { release(jsonResponse({ ended_at: 'now' })); await response })
    expect(screen.queryByText('Home destination')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'End session' })).toBeVisible()
    expect(useMode.getState().sessionId).toBeNull()
  } finally { window.history.replaceState(oldState, '', oldUrl) }
})
