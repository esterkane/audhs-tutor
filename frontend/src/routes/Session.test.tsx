import { clearDraft } from '../features/assess/draft'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { useMode } from '../stores/mode'
import { jsonResponse, renderApp, sseResponse } from '../test/utils'
import { Session } from './Session'
import { axe } from 'vitest-axe'

beforeEach(() => {
  sessionStorage.clear()
  clearDraft('audhs-answer:s1:a1')
})

const plan = [
  { type: 'movement_primer', planned_min: 5, node_ids: [], optional: true, reason: '', domain: 'movement' },
  { type: 'retrieval', planned_min: 8, node_ids: ['k1'], optional: false, reason: '' },
  { type: 'new_material', planned_min: 20, node_ids: ['k1'], optional: false, reason: '' },
  { type: 'recap', planned_min: 5, node_ids: [], optional: false, reason: '' },
]

function session(state: Record<string, unknown>) {
  return {
    id: 's1',
    mode: 'steady',
    energy: 3,
    socratic: false,
    started_at: 'now',
    ended_at: null,
    energy_after: null,
    next_skill: {
      id: 'k1',
      slug: 'x',
      title: 'Dot product',
      description: 'd',
      domain: 'ai_ml',
      success_criteria: [],
      prerequisites: [],
      mastery: 0.2,
      unlocked: true,
      state: {},
    },
    due_reviews: 2,
    review_cap: 5,
    minimum_viable: ['retrieval', 'recap'],
    plan,
    checkpoint: {},
    experiment: null,
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
      ...state,
    },
  }
}

const running0 = {
  block_index: 0,
  block: plan[0],
  block_id: 's1:0',
  block_status: 'running',
  block_started_at: new Date(Date.now() - 30 * 60_000).toISOString(), // long expired
  phase: 'practice',
  next_index: 1,
}

describe('Session', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('renders the server block, advances once on a double click, and routes by the returned phase', async () => {
    useMode.setState({ sessionId: 's1', skillId: null, mode: 'steady' })
    const calls: Array<[string, unknown]> = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/sessions/s1')) return jsonResponse(session(running0))
        if (url.endsWith('/api/practice/activities'))
          return jsonResponse({ activities: { movement: ['Walk'], guitar: [] } })
        if (url.endsWith('/api/adaptations')) return jsonResponse({ proposals: [] })
        if (url.endsWith('/api/plan/blocks/next')) {
          calls.push([url, JSON.parse(String(init?.body))])
          await new Promise((r) => setTimeout(r, 20))
          return jsonResponse({
            ...session({}).state,
            block_index: 1,
            block: plan[1],
            block_id: 's1:1',
            block_status: 'running',
            block_started_at: new Date().toISOString(),
            phase: 'review',
            next_index: 2,
            message: 'started',
          })
        }
        if (url.endsWith('/api/plan/blocks/extend')) {
          calls.push([url, JSON.parse(String(init?.body))])
          return jsonResponse({ ...session(running0).state, timer_extension_min: 5, message: 'extended' })
        }
        return jsonResponse({})
      }),
    )
    renderApp(
      <Routes>
        <Route path="/session" element={<Session />} />
        <Route path="/review" element={<p>REVIEW SCREEN</p>} />
      </Routes>,
      { route: '/session' },
    )
    // the running movement block comes from the server state, not from a local guess
    expect(await screen.findByText('Movement block')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Session plan and energy settings'))
    expect(screen.getByRole('listitem', { current: 'step' })).toHaveTextContent(/Move/)
    // the soft timer is derived from the server start time: 30 min ago on a 5-min block → prompt
    expect(await screen.findByText(/Planned time is up \(5 min\)/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /5 more minutes/i }))
    await waitFor(() => expect(calls.some(([u]) => u.endsWith('/blocks/extend'))).toBe(true))
    expect(calls.find(([u]) => u.endsWith('/blocks/extend'))?.[1]).toMatchObject({
      session_id: 's1',
      index: 0,
      minutes: 5,
    })
    // double-click on "Skip this block": exactly one /blocks/next with the current index
    const skip = screen.getByRole('button', { name: /skip this block/i })
    fireEvent.click(skip)
    fireEvent.click(skip)
    expect(await screen.findByText('REVIEW SCREEN')).toBeInTheDocument()
    const nexts = calls.filter(([u]) => u.endsWith('/blocks/next'))
    expect(nexts).toHaveLength(1)
    expect(nexts[0][1]).toMatchObject({ session_id: 's1', from_index: 0, reason: 'skipped' })
  })

  it('offers the plan start when no block is running and starts the chosen block', async () => {
    useMode.setState({ sessionId: 's1', skillId: null, mode: 'steady' })
    const starts: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/sessions/s1')) return jsonResponse(session({}))
        if (url.endsWith('/api/plan/blocks/start')) {
          starts.push(JSON.parse(String(init?.body)))
          return jsonResponse({
            ...session({}).state,
            block_index: 1,
            block: plan[1],
            block_id: 's1:1',
            block_status: 'running',
            block_started_at: new Date().toISOString(),
            phase: 'review',
          })
        }
        return jsonResponse({})
      }),
    )
    renderApp(
      <Routes>
        <Route path="/session" element={<Session />} />
        <Route path="/review" element={<p>REVIEW SCREEN</p>} />
      </Routes>,
      { route: '/session' },
    )
    expect(await screen.findByText('Choose where to begin')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Move \(5 min\), then new material: Dot product/i }),
    ).toBeInTheDocument()
    // review-first says what it skips
    expect(screen.getByRole('button', { name: /review first \(2 due\) — skips Move/i })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /review first \(2 due\)/i }))
    expect(await screen.findByText('REVIEW SCREEN')).toBeInTheDocument()
    expect(starts).toEqual([{ session_id: 's1', index: 1 }])
  })
})

it('preserves the assessment answer and confidence after a grading error and allows retry', async () => {
  useMode.setState({ sessionId: 's1', skillId: 'k1', mode: 'steady' })
  const attempts: Array<Record<string, unknown>> = []
  const state = { ...running0, block: plan[2], block_index: 2, phase: 'assess', skill_id: 'k1' }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.includes('/api/exercises/'))
        return jsonResponse({ error: { code: 'not_found', message: 'No exercise' } }, 404)
      if (url.endsWith('/api/sessions/s1')) return jsonResponse(session(state))
      if (url.includes('/api/assess/next'))
        return jsonResponse({
          skill_id: 'k1',
          item: {
            id: 'a1',
            skill_id: 'k1',
            kind: 'explain_back',
            question: 'Explain the relationship.',
          },
        })
      if (url.endsWith('/api/assess/attempt')) {
        attempts.push(JSON.parse(String(init?.body)))
        return jsonResponse(
          { error: { code: 'grading_unavailable', message: 'Try grading again; mastery unchanged.' } },
          503,
        )
      }
      return jsonResponse({})
    }),
  )
  renderApp(<Session />, { route: '/session' })
  const input = await screen.findByLabelText('Your answer')
  fireEvent.change(input, { target: { value: 'My explanation of the relationship.' } })
  fireEvent.click(screen.getByText('Confidence (optional)'))
  fireEvent.click(screen.getByRole('button', { name: '3' }))
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('mastery unchanged')
  expect(input).toHaveValue('My explanation of the relationship.')
  expect(screen.queryByText(/Score .*%/)).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  await waitFor(() => expect(attempts).toHaveLength(2))
  expect(attempts[1]).toMatchObject({ answer: attempts[0].answer, confidence_pre: 3, assessment_id: 'a1' })
  vi.unstubAllGlobals()
})

it('guides explanation to a question with optional controls collapsed and accessible', async () => {
  useMode.setState({ sessionId: 's1', skillId: 'k1', mode: 'steady' })
  const state = {
    ...running0,
    block: plan[2],
    block_index: 2,
    phase: 'teach',
    skill_id: 'k1',
    block_started_at: new Date().toISOString(),
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.includes('/api/exercises/'))
        return jsonResponse({ error: { code: 'not_found', message: 'No exercise' } }, 404)
      if (url.endsWith('/api/sessions/s1')) return jsonResponse(session(state))
      if (url.includes('/api/tutor/stream'))
        return sseResponse([
          ['token', { text: 'A dot product combines matching components.' }],
          ['done', { turn_id: 't1', sources: [], outcome: 'complete' }],
        ])
      if (url.includes('/api/assess/next'))
        return jsonResponse({
          item: { id: 'a1', kind: 'explain_back', question: 'Explain the relationship.' },
        })
      return jsonResponse({})
    }),
  )
  const { container } = renderApp(<Session />, { route: '/session' })
  expect(
    await screen.findByText(
      'Start with an explanation. Try a question when ready, or save this topic for later.',
    ),
  ).toBeVisible()
  expect(screen.getByText('More ways to learn').closest('details')).not.toHaveAttribute('open')
  expect(screen.getByRole('button', { name: 'Stop session' })).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Start explanation' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Try a question' }))
  expect(await screen.findByLabelText('Your answer')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Check my answer' })).toBeDisabled()
  expect(await axe(container)).toHaveNoViolations()
  vi.unstubAllGlobals()
})

it('offers continuing the plan after feedback without requiring another question', async () => {
  useMode.setState({ sessionId: 's1', skillId: 'k1', mode: 'steady' })
  const nextCalls: unknown[] = []
  const state = {
    ...running0,
    block: plan[2],
    block_index: 2,
    phase: 'assess',
    skill_id: 'k1',
    block_started_at: new Date().toISOString(),
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.includes('/api/exercises/'))
        return jsonResponse({ error: { code: 'not_found', message: 'No exercise' } }, 404)
      if (url.endsWith('/api/sessions/s1')) return jsonResponse(session(state))
      if (url.includes('/api/assess/next'))
        return jsonResponse({
          item: { id: 'a1', kind: 'mcq', question: 'Choose a value.', options: ['One', 'Two'] },
        })
      if (url.endsWith('/api/assess/attempt'))
        return jsonResponse({
          score: 1,
          feedback: 'The components match.',
          next_step: 'Continue.',
          criterion_results: [],
          mastery: 0.4,
          review: { due: '2026-10-01' },
          confidence_pre: 3,
        })
      if (url.endsWith('/api/plan/blocks/next')) {
        nextCalls.push(JSON.parse(String(init?.body)))
        return jsonResponse({ ...state, allowed: true, plan_complete: true })
      }
      return jsonResponse({})
    }),
  )
  renderApp(
    <Routes>
      <Route path="/session" element={<Session />} />
      <Route path="/recap" element={<p>RECAP SCREEN</p>} />
    </Routes>,
    { route: '/session' },
  )
  fireEvent.click(await screen.findByRole('button', { name: 'One' }))
  fireEvent.click(screen.getByText('Confidence (optional)'))
  fireEvent.click(screen.getByRole('button', { name: '3' }))
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  expect(await screen.findByText('Feedback on your answer')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Try another question (optional)' })).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Continue the plan' }))
  expect(await screen.findByText('RECAP SCREEN')).toBeVisible()
  expect(nextCalls).toEqual([{ session_id: 's1', from_index: 2, reason: 'finished', grasp_passed: true }])
  vi.unstubAllGlobals()
})
