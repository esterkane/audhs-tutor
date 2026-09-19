import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { ChallengePanel } from './ChallengePanel'

const modes = {
  modes: [
    { mode: 'planted_error', hint: 'Find the error' },
    { mode: 'steelman', hint: 'Argue it' },
  ],
}
const item = {
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
    fireEvent.click(screen.getByRole('button', { name: '4' }))
    expect(submit).toBeEnabled()
    fireEvent.click(submit)
    await waitFor(() => expect(screen.getByText(/found it/i)).toBeInTheDocument())
    expect(screen.getByText(/delayed review .* scheduled/i)).toBeInTheDocument()
    const body = JSON.parse(
      (fetchMock.mock.calls.at(-1) as unknown as [string, RequestInit])[1].body as string,
    )
    expect(body).toMatchObject({ assessment_id: 'a1', confidence_pre: 4 })
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))
    expect(onDone).toHaveBeenCalled()
  })
})
