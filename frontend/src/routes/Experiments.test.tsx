import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { jsonResponse, renderApp } from '../test/utils'
import { Experiments } from './Experiments'

const exp = {
  id: 'e1',
  name: 'Socratic vs explicit',
  hypothesis: 'Socratic improves delayed recall.',
  metric: 'delayed_recall',
  unit_type: 'node',
  status: 'running',
  created_at: 'now',
  started_at: 'now',
  ended_at: null,
  arms: [
    { id: 'a', name: 'explicit', config: { socratic: false }, assigned: 3 },
    { id: 'b', name: 'socratic', config: { socratic: true }, assigned: 3 },
  ],
}
const results = {
  experiment: exp,
  primary_metric: 'delayed_recall',
  metrics: [
    {
      metric: 'delayed_recall',
      lower_is_better: false,
      arms: [
        { arm_id: 'a', name: 'explicit', n: 6, mean: 0.5, sd: 0.55 },
        { arm_id: 'b', name: 'socratic', n: 6, mean: 1.0, sd: 0.0 },
      ],
      difference: 0.5,
      ci95: [0.06, 0.94],
      reading: 'Hypothesis supported so far: socratic looks higher-is-better on delayed_recall.',
    },
  ],
  units: [{ id: 'n1', arm: 'socratic', label: 'Softmax', ts: 'now' }],
}

describe('Experiments', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lists experiments, opens results as hypotheses with the raw numbers, stops on click', async () => {
    const posts: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method === 'POST') {
          posts.push(url)
          return jsonResponse({ ...exp, status: 'done' })
        }
        if (url.endsWith('/results')) return jsonResponse(results)
        return jsonResponse({
          experiments: [exp],
          templates: [{ id: 'socratic-vs-explicit', name: 'T', hypothesis: 'h' }],
          metrics: ['delayed_recall'],
        })
      }),
    )
    renderApp(
      <Routes>
        <Route path="/experiments" element={<Experiments />} />
      </Routes>,
      { route: '/experiments' },
    )
    expect(await screen.findByText('Socratic vs explicit')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Results' }))
    expect(
      await screen.findByText(/explicit: 0.50 \(n=6\) · socratic: 1.00 \(n=6\) · difference \+0.50/),
    ).toBeInTheDocument()
    expect(screen.getByText(/Hypothesis supported so far/)).toBeInTheDocument()
    expect(screen.getByText(/never as a score of you/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
    await waitFor(() => expect(posts).toContain('/api/experiments/e1/stop'))
  })
})
