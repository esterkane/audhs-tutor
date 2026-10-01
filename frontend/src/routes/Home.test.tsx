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
  plan: [
    { type: 'retrieval', planned_min: 5, node_ids: [], optional: false, reason: '' },
    { type: 'recap', planned_min: 3, node_ids: [], optional: false, reason: '' },
  ],
  checkpoint: {},
  state: {
    block_index: null,
    block: null,
    block_id: null,
    block_status: null,
    block_started_at: null,
    phase: null,
    skill_id: 'k1',
    next_index: 0,
    plan_version: 1,
    timer_extension_min: 0,
    plan_complete: false,
    allowed: true,
    message: '',
  },
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
    const blockStarts: unknown[] = []
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/api/plan/blocks/start')) {
        blockStarts.push(JSON.parse(String(init?.body)))
        return jsonResponse({ ...session.state, block_index: 0, block_status: 'running', phase: 'review' })
      }
      return init?.method === 'POST' ? jsonResponse(session, 201) : jsonResponse(null)
    })
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
    await waitFor(() => expect(screen.getByRole('button', { name: /start session/i })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: /start session/i }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const post = fetchMock.mock.calls.find(
      (c) => (c as unknown as [string, RequestInit])[1]?.method === 'POST',
    ) as unknown as [string, RequestInit]
    const [, init] = post
    expect(JSON.parse(init.body as string)).toEqual({
      mode: 'low_capacity',
      energy: 2,
      socratic: false,
    })
    // due reviews -> an explained offer, never an auto-route; low energy recommends the capped review
    expect(await screen.findByText(/which first\?/i)).toBeInTheDocument()
    const review = screen.getByRole('button', { name: /review \(3 of 3 due\)/i })
    expect(review).toHaveClass('bg-accent')
    fireEvent.click(review)
    expect(await screen.findByText('REVIEW SCREEN')).toBeInTheDocument()
    expect(useMode.getState().sessionId).toBe('s1')
    // the choice starts the plan's review block on the server (review-first semantics)
    expect(blockStarts).toEqual([{ session_id: 's1', index: 0 }])
  })

  it('routes Resume by the server phase of the running block', async () => {
    useMode.setState({ mode: 'steady', energy: 3, socratic: false, sessionId: null })
    const running = {
      ...session,
      state: {
        ...session.state,
        block_index: 0,
        block: session.plan[0],
        block_id: 's1:0',
        block_status: 'running',
        block_started_at: new Date().toISOString(),
        phase: 'review',
      },
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) =>
        url.endsWith('/api/sessions/current') ? jsonResponse(running) : jsonResponse(null),
      ),
    )
    renderApp(
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/review" element={<p>REVIEW SCREEN</p>} />
        <Route path="/session" element={<p>SESSION SCREEN</p>} />
      </Routes>,
    )
    const resume = await screen.findByRole('button', { name: /resume previous session \(review\)/i })
    fireEvent.click(resume)
    expect(await screen.findByText('REVIEW SCREEN')).toBeInTheDocument()
    expect(useMode.getState().sessionId).toBe('s1')
  })

  it('offers a goal from published courses and previews the session length before starting', async () => {
    useMode.setState({ mode: 'steady', energy: 3, socratic: false, sessionId: null })
    const puts: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/curriculum/material'))
          return jsonResponse({
            courses: [
              {
                course: 'LLM Evaluation',
                documents: 4,
                chunks: 20,
                drafts: 0,
                published_skills: 3,
                status: 'published',
              },
              {
                course: 'Only searchable',
                documents: 2,
                chunks: 9,
                drafts: 0,
                published_skills: 0,
                status: 'searchable',
              },
            ],
          })
        if (url.includes('/api/plan/preview'))
          return jsonResponse({
            mode: 'steady',
            energy: 3,
            blocks: [
              { type: 'retrieval', planned_min: 7, node_ids: [], optional: false, reason: '' },
              { type: 'new_material', planned_min: 20, node_ids: [], optional: false, reason: '' },
              { type: 'recap', planned_min: 5, node_ids: [], optional: false, reason: '' },
            ],
            minimum_viable: ['retrieval', 'recap'],
            total_min: 32,
            policy_version: 'planner.v1',
          })
        if (url.endsWith('/api/preferences') && init?.method === 'PUT') {
          puts.push(JSON.parse(String(init.body)))
          return jsonResponse({ values: { 'goal.course': 'LLM Evaluation' }, specs: [] })
        }
        if (url.endsWith('/api/preferences')) return jsonResponse({ values: {}, specs: [] })
        return jsonResponse(null)
      }),
    )
    renderApp(
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>,
    )
    // only courses with published skills can be a goal; the duration preview names the blocks
    const goal = (await screen.findByLabelText('Goal')) as HTMLSelectElement
    await screen.findByRole('option', { name: 'LLM Evaluation (3 skills)' })
    expect(Array.from(goal.options).map((o) => o.textContent)).toEqual([
      'Whole skill map',
      'LLM Evaluation (3 skills)',
    ])
    expect(
      await screen.findByText(/retrieval 7 min → new material 20 min → recap 5 min · about 32 min in total/),
    ).toBeInTheDocument()
    fireEvent.change(goal, { target: { value: 'LLM Evaluation' } })
    await waitFor(() => expect(puts).toEqual([{ key: 'goal.course', value: 'LLM Evaluation' }]))
    // the questioning style is an explicit opt-in behind "More options", default explicit
    fireEvent.click(
      screen.getByText(/More options · questioning style: Explicit \(default\)/, { selector: 'summary' }),
    )
    expect(screen.getByRole('button', { name: /explicit \(default\)/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })
})
