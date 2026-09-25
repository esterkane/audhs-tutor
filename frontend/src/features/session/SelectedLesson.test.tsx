import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { Home } from '../../routes/Home'
import { Map } from '../../routes/Map'
import { useMode } from '../../stores/mode'
import { jsonResponse, renderApp } from '../../test/utils'
vi.mock('mermaid', () => ({
  default: { initialize: vi.fn(), render: vi.fn(async () => ({ svg: '<svg />' })) },
}))
afterEach(() => vi.unstubAllGlobals())

for (const running of [false, true]) {
  it(`carries a non-default map choice to session creation (running=${running})`, async () => {
    useMode.setState({ sessionId: running ? 'old' : null, skillId: running ? 'default' : null })
    const posts: Array<[string, unknown]> = []
    const selected = {
      id: 'chosen',
      title: 'Chosen lesson',
      unlocked: true,
      description: 'Selected context',
      mastery: 0,
      memory: { items: 0, due: 0 },
    }
    const state = { skill_id: 'default', phase: 'review', block_status: 'running' }
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method === 'POST') {
          posts.push([url, JSON.parse(String(init.body))])
          return jsonResponse({ id: 'new', state: { ...state, phase: 'teach', skill_id: 'chosen' } })
        }
        if (url === '/api/sessions/current')
          return jsonResponse(running ? { id: 'old', active_skill: { title: 'Old topic' }, state } : null)
        if (url === '/api/skills') return jsonResponse({ skills: [selected], next_skill_id: 'default' })
        return jsonResponse({ nodes: [selected], edges: [], mermaid: 'graph LR' })
      }),
    )
    renderApp(
      <Routes>
        <Route path="/map" element={<Map />} />
        <Route path="/" element={<Home />} />
        <Route path="/session" element={<p>Selected session screen</p>} />
      </Routes>,
      { route: '/map' },
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Learn this' }))
    expect(await screen.findByText('Learn: Chosen lesson')).toBeInTheDocument()
    expect(posts).toHaveLength(0)
    if (running) expect(useMode.getState().skillId).toBe('default')
    const button = screen.getByRole('button', {
      name: running ? 'End and start this lesson' : 'Start this lesson',
    })
    await waitFor(() => expect(button).toBeEnabled())
    fireEvent.click(button)
    expect(await screen.findByText('Selected session screen')).toBeInTheDocument()
    expect(posts.at(-1)).toEqual(['/api/sessions', expect.objectContaining({ skill_id: 'chosen' })])
    expect(posts.map(([url]) => url)).toEqual(
      running ? ['/api/sessions/old/end', '/api/sessions'] : ['/api/sessions'],
    )
    expect(useMode.getState().skillId).toBe('chosen')
  })
}

it('keeps the current session when eligibility preflight rejects an unlocked non-teaching item', async () => {
  useMode.setState({ sessionId: 'old', skillId: 'default' })
  const posts: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === 'POST') posts.push(url)
      if (url.includes('/selection/'))
        return jsonResponse(
          { error: { code: 'lesson_unavailable', message: 'Choose a teaching lesson' } },
          409,
        )
      if (url === '/api/skills')
        return jsonResponse({ skills: [{ id: 'vocab', title: 'Vocabulary', unlocked: true }] })
      return jsonResponse({
        id: 'old',
        state: { skill_id: 'default', phase: 'review', block_status: 'running' },
      })
    }),
  )
  renderApp(<Home />, { route: '/?lesson=vocab' })
  fireEvent.click(await screen.findByRole('button', { name: 'End and start this lesson' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not start this lesson')
  expect(posts).toEqual([])
  expect(useMode.getState().sessionId).toBe('old')
})

it('keeps the current session and returns to its review phase without starting or ending anything', async () => {
  const posts: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === 'POST') posts.push(url)
      if (url === '/api/skills')
        return jsonResponse({ skills: [{ id: 'chosen', title: 'Chosen', unlocked: true }] })
      return jsonResponse({
        id: 'old',
        state: { skill_id: 'default', phase: 'review', block_status: 'running' },
      })
    }),
  )
  renderApp(
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/review" element={<p>Existing review</p>} />
    </Routes>,
    { route: '/?lesson=chosen' },
  )
  fireEvent.click(await screen.findByRole('button', { name: 'Keep current session' }))
  expect(await screen.findByText('Existing review')).toBeInTheDocument()
  expect(posts).toEqual([])
  expect(useMode.getState().skillId).toBe('default')
})
