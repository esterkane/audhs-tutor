import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Routes, Route } from 'react-router-dom'
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
