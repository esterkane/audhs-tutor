import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { clearDraft } from '../assess/draft'
import { ChallengePanel } from './ChallengePanel'

beforeEach(() => { sessionStorage.clear(); clearDraft('challenge:s1:a1') })

const modes = {
  modes: [
    { mode: 'planted_error', hint: 'Find the error' },
    { mode: 'steelman', hint: 'Argue it' },
  ],
}
const item = {
  content_version: 'old-version',
  assessment_id: 'a1',
  skill_id: 'k1',
  mode: 'planted_error',
  prompt: 'Spot the error: we divide by d_k.',
  criteria: ['Locates the error'],
  cached: false,
  sources: [],
}
const result = {
  attempt_id: 'x',
  assessment_id: 'a1',
  skill_id: 'k1',
  kind: 'challenge_planted_error',
  dimension: 'application',
  correct: null,
  score: 1,
  criterion_results: [{ criterion: 'Locates the error', passed: true, evidence: 'sqrt' }],
  misconception: null,
  confidence: 0.9,
  grader_level: 'local',
  feedback: 'Found it.',
  next_step: 'Explain why.',
  confidence_pre: 4,
  calibration: 'estimate close to result',
  review: { item_id: 'r1', due: '2030-01-03T00:00:00+00:00', state: 'review', stability: 3 },
  mastery: 0.4,
}

describe('ChallengePanel', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('offers concrete modes, requires confidence before submit, shows criterion feedback and the delayed review', async () => {
    const fetchMock = vi.fn(async (url: string) =>
      url.endsWith('/modes')
        ? jsonResponse(modes)
        : url.endsWith('/start')
          ? jsonResponse(item)
          : jsonResponse(result),
    )
    vi.stubGlobal('fetch', fetchMock)
    const onDone = vi.fn()
    renderApp(<ChallengePanel sessionId="s1" skillId="k1" onDone={onDone} />)
    fireEvent.click(await screen.findByRole('button', { name: /planted error/i }))
    expect(await screen.findByText(/spot the error/i)).toBeInTheDocument()
    const submit = screen.getByRole('button', { name: /submit/i })
    expect(submit).toBeDisabled()
    fireEvent.change(screen.getByLabelText(/your answer/i), { target: { value: 'it should be sqrt(d_k)' } })
    fireEvent.click(screen.getByText('Confidence (optional)'))
    fireEvent.click(screen.getByRole('button', { name: '4' }))
    expect(submit).toBeEnabled()
    fireEvent.click(submit)
    await waitFor(() => expect(screen.getByText(/found it/i)).toBeInTheDocument())
    expect(screen.getByText(/delayed review .* scheduled/i)).toBeInTheDocument()
    const body = JSON.parse(
      (fetchMock.mock.calls.at(-1) as unknown as [string, RequestInit])[1].body as string,
    )
    expect(body).toMatchObject({ assessment_id: 'a1', confidence_pre: 4, content_version: 'old-version' })
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))
    expect(onDone).toHaveBeenCalled()
  })
})

it('shows grading failure, retains the answer and confidence, and retries successfully', async () => {
  const bodies: Array<Record<string, unknown>> = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/modes')) return jsonResponse(modes)
      if (url.endsWith('/start')) return jsonResponse(item)
      if (url.includes('/api/assess/requests/')) return jsonResponse({ status: 'not_found', result: null })
      bodies.push(JSON.parse(String(init?.body)))
      return bodies.length === 1
        ? jsonResponse(
            { error: { code: 'grading_unavailable', message: 'Try again; mastery unchanged.' } },
            503,
          )
        : jsonResponse(result)
    }),
  )
  const done = vi.fn()
  renderApp(<ChallengePanel sessionId="s1" skillId="k1" onDone={done} />)
  fireEvent.click(await screen.findByRole('button', { name: /planted error/i }))
  const input = await screen.findByLabelText(/your answer/i)
  fireEvent.change(input, { target: { value: 'Use sqrt(d_k) to scale the variance.' } })
  fireEvent.click(screen.getByText('Confidence (optional)'))
  fireEvent.click(screen.getByRole('button', { name: '4' }))
  fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('mastery unchanged')
  expect(input).toHaveValue('Use sqrt(d_k) to scale the variance.')
  expect(done).not.toHaveBeenCalled()
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
  expect(bodies).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: 'Check saved result' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Send the original answer' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Use feedback for this answer' }))
  expect(await screen.findByRole('status')).toHaveTextContent('Found it.')
  expect(bodies[1]).toMatchObject({ answer: bodies[0].answer, confidence_pre: 4 })
  vi.unstubAllGlobals()
})

it('refreshes the same stale challenge without regeneration and preserves the written answer', async () => {
  const writes: Record<string, unknown>[] = []
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/modes')) return jsonResponse(modes)
    if (url.endsWith('/start')) return jsonResponse(item)
    if (url.includes('/api/assess/items/a1?'))
      return jsonResponse({
        id: 'a1',
        skill_id: 'k1',
        kind: 'challenge_planted_error',
        question: 'Updated challenge',
        criteria: ['New criterion'],
        content_version: 'new-version',
      })
    if (url.endsWith('/submit')) {
      writes.push(JSON.parse(String(init?.body)))
      return writes.length === 1
        ? jsonResponse({ error: { code: 'assessment_content_changed', message: 'Changed' } }, 409)
        : jsonResponse(result)
    }
    return jsonResponse(null)
  })
  vi.stubGlobal('fetch', fetcher)
  renderApp(<ChallengePanel sessionId="s1" skillId="k1" onDone={() => {}} />)
  fireEvent.click(await screen.findByRole('button', { name: /planted error/i }))
  fireEvent.change(await screen.findByLabelText(/your answer/i), { target: { value: 'Keep my reasoning' } })
  fireEvent.click(screen.getByRole('button', { name: /submit/i }))
  fireEvent.click(await screen.findByRole('button', { name: 'Review updated question — keep my answer' }))
  expect(await screen.findByText('Updated challenge')).toBeVisible()
  expect(screen.getByLabelText(/your answer/i)).toHaveValue('Keep my reasoning')
  expect(fetcher.mock.calls.filter(([url]) => url.endsWith('/start'))).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: /submit/i }))
  await waitFor(() => expect(writes).toHaveLength(2))
  expect(writes[1]).toMatchObject({ answer: 'Keep my reasoning', content_version: 'new-version' })
})

it('cannot clear a rejected answer from another activity by refreshing the current challenge', async () => {
  const pending = {
    version: 1,
    id: crypto.randomUUID(),
    endpoint: '/api/assess/attempt',
    body: { session_id: 's1', assessment_id: 'different-item', answer: 'Keep original', hint_count: 0 },
    question: 'Earlier question',
    rejectedContent: true,
  }
  sessionStorage.setItem('assessment-request:v1:s1', JSON.stringify(pending))
  const fetcher = vi.fn(async (url: string) =>
    url.endsWith('/modes') ? jsonResponse(modes) : jsonResponse(item),
  )
  vi.stubGlobal('fetch', fetcher)
  renderApp(<ChallengePanel sessionId="s1" skillId="k1" onDone={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /planted error/i }))
  await screen.findByText(/Spot the error/)
  fireEvent.click(screen.getByRole('button', { name: 'Review updated question — keep my answer' }))
  expect(await screen.findByText(/This saved answer belongs to another question/)).toBeInTheDocument()
  expect(JSON.parse(sessionStorage.getItem('assessment-request:v1:s1')!).id).toBe(pending.id)
  expect(screen.getByText('Keep original')).toBeInTheDocument()
  expect(fetcher.mock.calls.some(([url]) => url.includes('/api/assess/items/'))).toBe(false)
})


it('retains the answer through exclusion, failed refresh and explicit restoration', async () => {
  let state = 'active'
  let revision = 0
  let failRefresh = false
  let deferRefresh = false
  let releaseRefresh!: () => void
  const submits: unknown[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/modes')) return jsonResponse(modes)
    if (url.endsWith('/start')) return jsonResponse(JSON.parse(String(init?.body)).mode === 'steelman'
      ? { ...item, assessment_id: 'a2', mode: 'steelman', prompt: 'New challenge' }
      : { ...item, content_version: revision ? 'fresh' : item.content_version })
    if (url === '/api/questions/a1/practice') {
      if (init?.method === 'POST') {
        state = JSON.parse(String(init.body)).action === 'suspend' ? 'suspended' : 'active'
        revision++
      }
      const status = { assessment_id: 'a1', state, revision, reason: null }
      return jsonResponse(init?.method === 'POST' ? status : { status, affected_reviews: 0 })
    }
    if (url.startsWith('/api/assess/items/') && deferRefresh) await new Promise<void>(resolve => { releaseRefresh = resolve })
    if (url.startsWith('/api/assess/items/')) return failRefresh
      ? jsonResponse({ error: { message: 'offline' } }, 503)
      : jsonResponse({ id: 'a1', question: item.prompt, criteria: item.criteria, content_version: 'fresh' })
    if (url.endsWith('/submit')) { submits.push(JSON.parse(String(init?.body))); return jsonResponse(result) }
    return jsonResponse(null)
  }))
  const view = renderApp(<ChallengePanel sessionId="s1" skillId="k1" onDone={() => {}} />)
  fireEvent.click(await screen.findByRole('button', { name: /planted error/i }))
  fireEvent.change(await screen.findByLabelText('Your answer'), { target: { value: 'my explanation' } })
  fireEvent.click(screen.getByRole('button', { name: 'Question practice options' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Exclude this question' }))
  await screen.findByText('This challenge is excluded. Your answer is kept in this tab. Restore the question before submitting.')
  expect(screen.getByRole('button', { name: 'Submit' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Restore this question' }))
  failRefresh = true
  fireEvent.click(await screen.findByRole('button', { name: 'Refresh restored challenge' }))
  await screen.findByText('Could not refresh the challenge. Your answer is kept. Try again.')
  expect(screen.getByLabelText('Your answer')).toHaveValue('my explanation')
  failRefresh = false
  fireEvent.click(screen.getByRole('button', { name: 'Refresh restored challenge' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Submit' })).toBeEnabled())
  view.unmount()
  renderApp(<ChallengePanel sessionId="s1" skillId="k1" onDone={() => {}} />)
  fireEvent.click(await screen.findByRole('button', { name: /planted error/i }))
  expect(await screen.findByLabelText('Your answer')).toHaveValue('my explanation')
  expect(submits).toEqual([])
  fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
  await screen.findByText('Found it.')
  expect(submits).toEqual([expect.objectContaining({ answer: 'my explanation', content_version: 'fresh' })])
  fireEvent.click(screen.getByRole('button', { name: 'Question practice options' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Exclude this question' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Restore this question' }))
  deferRefresh = true
  fireEvent.click(await screen.findByRole('button', { name: 'Refresh restored challenge' }))
  await waitFor(() => expect(releaseRefresh).toBeDefined())
  fireEvent.click(screen.getByRole('button', { name: 'Another mode' }))
  fireEvent.click(await screen.findByRole('button', { name: /steelman/i }))
  await screen.findByText('New challenge')
  fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: 'new answer' } })
  await act(async () => { releaseRefresh() })
  expect(screen.getByText('New challenge')).toBeVisible()
  expect(screen.getByLabelText('Your answer')).toHaveValue('new answer')
})
