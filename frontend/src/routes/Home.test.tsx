import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { useMode } from '../stores/mode'
import { jsonResponse, renderApp } from '../test/utils'
import { Home } from './Home'

const session = {
  id: 's1',
  mode: 'low_capacity',
  energy: 2,
  socratic: false,
  started_at: 'now',
  ended_at: null,
  energy_after: null,
  next_skill: {
    id: 'k1',
    slug: 'x',
    title: 'Dot product',
    description: '',
    domain: 'ai_ml',
    success_criteria: [],
    prerequisites: [],
    mastery: 0,
    unlocked: true,
    state: {},
  },
  due_reviews: 3,
  review_cap: 5,
  minimum_viable: ['retrieval', 'recap'],
}

describe('Home', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('offers concrete mode/energy choices and starts a session with the chosen state', async () => {
    useMode.setState({
      mode: 'steady',
      energy: 3,
      socratic: false,
      sessionId: null,
    })
    const fetchMock = vi.fn(async () => jsonResponse(session, 201))
    vi.stubGlobal('fetch', fetchMock)
    renderApp(
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/review" element={<p>REVIEW SCREEN</p>} />
        <Route path="/session" element={<p>SESSION SCREEN</p>} />
      </Routes>,
    )
    fireEvent.click(screen.getByRole('button', { name: /low capacity/i }))
    fireEvent.click(screen.getByRole('button', { name: '2' }))
    expect(screen.getByRole('button', { name: /explicit \(default\)/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    fireEvent.click(screen.getByRole('button', { name: /start session/i }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toEqual({
      mode: 'low_capacity',
      energy: 2,
      socratic: false,
    })
    // low energy + due reviews -> minimum-viable path first
    expect(await screen.findByText('REVIEW SCREEN')).toBeInTheDocument()
    expect(useMode.getState().sessionId).toBe('s1')
  })
})
