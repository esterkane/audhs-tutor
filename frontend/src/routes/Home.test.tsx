import { HomeTopicPreparation } from '../features/areas/HomeTopicPreparation'
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

it('puts the actual running topic and next action before optional setup', async () => {
  useMode.setState({ sessionId: 'stale', mode: 'steady', energy: 3, socratic: false })
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) =>
      jsonResponse(
        url.endsWith('/api/sessions/current')
          ? {
              ...session,
              active_skill: { ...session.next_skill, title: 'Missing values' },
              state: { ...session.state, block_status: 'running', phase: 'review' },
            }
          : null,
      ),
    ),
  )
  renderApp(<Home />)
  const resume = await screen.findByRole('button', { name: /Resume previous session: Missing values/ })
  const setup = screen.getByText('Session options', { selector: 'summary' })
  expect(resume.compareDocumentPosition(setup) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(screen.getByText('Next: continue your saved review.')).toBeVisible()
  expect(setup.parentElement).not.toHaveAttribute('open')
  expect(screen.getByRole('heading', { level: 1, name: 'Your next step' })).toBeVisible()
})

it('does not offer a stale local session as a verified resume after a server failure', async () => {
  useMode.setState({ sessionId: 'stale', mode: 'steady', energy: 3, socratic: false })
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) =>
      url.endsWith('/api/sessions/current')
        ? jsonResponse({ detail: 'Unavailable' }, 503)
        : jsonResponse(null),
    ),
  )
  renderApp(<Home />)
  expect(await screen.findByText(/Could not check your saved session/)).toBeVisible()
  expect(screen.queryByRole('button', { name: /Resume previous session/ })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Start session' })).toBeDisabled()
})

it('offers activation in the start card for an empty selected area without replacing the topic', async () => {
  useMode.setState({ sessionId: null, mode: 'steady', energy: 3, socratic: false })
  const fetchMock = vi.fn(async (url: string) => {
    if (url.endsWith('/api/preferences')) return jsonResponse({ values: { 'goal.area': 'empty-area' } })
    if (url.endsWith('/api/areas'))
      return jsonResponse({ areas: [{ id: 'empty-area', title: 'Local models' }] })
    if (url.endsWith('/api/skills'))
      return jsonResponse({ skills: [session.next_skill], next_skill_id: null })
    return jsonResponse(null)
  })
  vi.stubGlobal('fetch', fetchMock)
  renderApp(<Home />)
  const activate = await screen.findByRole('link', { name: 'Review and activate a lesson' })
  expect(activate).toHaveAttribute('href', '/areas?area=empty-area')
  expect(activate.closest('[aria-label="Start or resume learning"]')).not.toBeNull()
  expect(screen.getByText('New session topic: Local models')).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Start session' })).not.toBeInTheDocument()
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/api/sessions'))).toBe(false)
})

it('waits for the switched topic lookup and then starts its session', async () => {
  useMode.setState({ sessionId: null, mode: 'steady', energy: 3, socratic: false })
  let selected = ''
  let finishLookup!: (response: Response) => void
  const posts: unknown[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/api/preferences')) {
        if (init?.method === 'PUT') selected = JSON.parse(String(init.body)).value
        return jsonResponse({ values: { 'goal.area': selected } })
      }
      if (url.endsWith('/api/areas'))
        return jsonResponse({
          areas: [
            { id: 'python', title: 'Python', active_lessons: 1 },
            {
              id: 'empty',
              title: 'Creative',
              active_lessons: 0,
            },
          ],
        })
      if (url.endsWith('/api/skills')) {
        if (selected === 'empty') return jsonResponse({ skills: [], next_skill_id: null })
        if (selected)
          return new Promise<Response>((resolve) => {
            finishLookup = resolve
          })
        return jsonResponse({ skills: [session.next_skill], next_skill_id: 'k1' })
      }
      if (url.endsWith('/api/sessions') && init?.method === 'POST') {
        posts.push(JSON.parse(String(init.body)))
        return jsonResponse({
          ...session,
          due_reviews: 0,
          state: { ...session.state, skill_id: 'python-lesson' },
          next_skill: { ...session.next_skill, id: 'python-lesson' },
        })
      }
      return jsonResponse(null)
    }),
  )
  renderApp(
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/session" element={<p>NEW SESSION</p>} />
    </Routes>,
  )
  await waitFor(() => expect(screen.getByLabelText('Knowledge area')).toBeEnabled())
  fireEvent.change(screen.getByLabelText('Knowledge area'), { target: { value: 'python' } })
  await screen.findByText('Checking your lesson selection…')
  expect(screen.getByRole('button', { name: 'Start session' })).toBeDisabled()
  expect(screen.queryByText(/No available lesson in this selection/)).not.toBeInTheDocument()
  expect(screen.getByLabelText('Knowledge area')).toBeDisabled()
  await waitFor(() => expect(finishLookup).toBeDefined())
  finishLookup(
    jsonResponse({
      skills: [{ ...session.next_skill, id: 'python-lesson', title: 'Python variables' }],
      next_skill_id: 'python-lesson',
    }),
  )
  await waitFor(() => expect(screen.getByRole('button', { name: 'Start session' })).toBeEnabled())
  expect(screen.getByText('New session topic: Python')).toBeVisible()
  expect(
    screen.getByRole('option', { name: 'Creative · needs preparation (no activated lessons)' }),
  ).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Knowledge area'), { target: { value: 'empty' } })
  await screen.findByRole('link', { name: 'Review and activate a lesson' })
  expect(screen.queryByRole('button', { name: 'Start session' })).not.toBeInTheDocument()
  const previousLookup = finishLookup
  fireEvent.change(screen.getByLabelText('Knowledge area'), { target: { value: 'python' } })
  await screen.findByText('Checking your lesson selection…')
  await waitFor(() => expect(finishLookup).not.toBe(previousLookup))
  await waitFor(() => expect(screen.getByText('New session topic: Python')).toBeVisible())
  finishLookup(
    jsonResponse({
      skills: [{ ...session.next_skill, id: 'python-lesson', title: 'Python variables' }],
      next_skill_id: 'python-lesson',
    }),
  )
  await waitFor(() => expect(screen.getByRole('button', { name: 'Start session' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Start session' }))
  await screen.findByText('NEW SESSION')
  expect(posts).toHaveLength(1)
  expect(useMode.getState().skillId).toBe('python-lesson')
})

it('preserves the saved area when its names fail to load and offers a retry', async () => {
  useMode.setState({ sessionId: null, mode: 'steady', energy: 3, socratic: false })
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.endsWith('/api/preferences')) return jsonResponse({ values: { 'goal.area': 'saved-area' } })
      if (url.endsWith('/api/areas')) return jsonResponse({ detail: 'Unavailable' }, 503)
      if (url.endsWith('/api/skills')) return jsonResponse({ skills: [], next_skill_id: null })
      return jsonResponse(null)
    }),
  )
  renderApp(<Home />)
  await screen.findByRole('button', { name: 'Retry topics' })
  expect(screen.getByLabelText('Knowledge area')).toHaveValue('saved-area')
  expect(screen.getByRole('option', { name: 'Your selected area (details unavailable)' })).toBeInTheDocument()
})

it('does not call a failed lesson lookup empty or offer activation as its remedy', async () => {
  useMode.setState({ sessionId: null, mode: 'steady', energy: 3, socratic: false })
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.endsWith('/api/preferences')) return jsonResponse({ values: { 'goal.area': 'saved-area' } })
      if (url.endsWith('/api/areas')) return jsonResponse({ areas: [{ id: 'saved-area', title: 'Python' }] })
      if (url.endsWith('/api/skills')) return jsonResponse({ detail: 'Unavailable' }, 503)
      return jsonResponse(null)
    }),
  )
  renderApp(<Home />)
  await screen.findByRole('button', { name: 'Retry lesson selection' })
  expect(screen.getByRole('button', { name: 'Start session' })).toBeDisabled()
  expect(screen.queryByRole('link', { name: 'Review and activate a lesson' })).not.toBeInTheDocument()
  expect(screen.queryByText(/No available lesson in this selection/)).not.toBeInTheDocument()
})

it('offers active lesson review rather than activation when the selected area has lessons but none available', async () => {
  useMode.setState({ sessionId: null, mode: 'steady', energy: 3, socratic: false })
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.endsWith('/api/preferences')) return jsonResponse({ values: { 'goal.area': 'blocked' } })
      if (url.endsWith('/api/areas'))
        return jsonResponse({ areas: [{ id: 'blocked', title: 'Advanced topic', active_lessons: 2 }] })
      if (url.endsWith('/api/skills')) return jsonResponse({ skills: [], next_skill_id: null })
      return jsonResponse(null)
    }),
  )
  renderApp(<Home />)
  expect(await screen.findByRole('link', { name: 'Review active lessons' })).toHaveAttribute('href', '/map')
  expect(
    screen.getByText(/No lesson is available to start. Review active lessons and prerequisites/),
  ).toBeVisible()
  expect(screen.queryByRole('link', { name: 'Review and activate a lesson' })).not.toBeInTheDocument()
  expect(screen.queryByText(/This topic has no activated lessons yet/)).not.toBeInTheDocument()
})

it('previews only the selected topic prepared draft and links to explicit review', async () => {
  const fetchMock = vi.fn(async (url: string) => {
    if (url.endsWith('/api/preferences')) return jsonResponse({ values: { 'goal.area': 'local' } })
    if (url.endsWith('/api/areas'))
      return jsonResponse({ areas: [{ id: 'local', title: 'Local models', active_lessons: 0 }] })
    if (url.endsWith('/api/skills')) return jsonResponse({ skills: [], next_skill_id: null })
    if (url.endsWith('/api/curriculum/drafts'))
      return jsonResponse({
        drafts: [
          {
            id: 'other',
            area_id: 'other',
            status: 'draft',
            payload: { area_state: 'generated', skills: [{ title: 'Wrong topic' }] },
          },
          { id: 'interrupted', area_id: 'local', status: 'draft', payload: { area_state: 'interrupted' } },
          {
            id: 'prepared',
            area_id: 'local',
            status: 'draft',
            payload: {
              area_state: 'generated',
              skills: [{ slug: 'quantization', title: 'Quantization' }],
              learning_objects: [{ skill: 'quantization', goal: 'Explain the memory tradeoff' }],
            },
          },
        ],
      })
    return jsonResponse(null)
  })
  vi.stubGlobal('fetch', fetchMock)
  renderApp(<Home />)
  expect(await screen.findByText('Quantization')).toBeVisible()
  expect(screen.getByText('Explain the memory tradeoff')).toBeVisible()
  expect(screen.queryByText('Wrong topic')).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Review lessons to start' })).toHaveAttribute(
    'href',
    '/areas?area=local&draft=prepared',
  )
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/publish'))).toBe(false)
})

it('keeps preparation loading and failure distinct, with a review fallback', async () => {
  let finish!: (response: Response) => void
  vi.stubGlobal(
    'fetch',
    vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          finish = resolve
        }),
    ),
  )
  renderApp(<HomeTopicPreparation areaId="local" secondary={false} />)
  expect(screen.getByText('Checking prepared lessons for this topic…')).toBeVisible()
  finish(jsonResponse({ detail: 'Unavailable' }, 503))
  expect(await screen.findByRole('button', { name: 'Retry prepared lessons' })).toBeVisible()
  expect(screen.queryByText('Checking prepared lessons for this topic…')).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Review and activate a lesson' })).toHaveAttribute(
    'href',
    '/areas?area=local',
  )
})
