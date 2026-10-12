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
        {
          arm_id: 'a',
          name: 'explicit',
          n: 6,
          mean: 0.5,
          sd: 0.55,
          n_units: 6,
          n_events: 23,
          fidelity: null,
        },
        { arm_id: 'b', name: 'socratic', n: 6, mean: 1.0, sd: 0.0, n_units: 6, n_events: 19, fidelity: 0.8 },
      ],
      difference: 0.5,
      ci95: [0.06, 0.94],
      reading:
        'socratic has the better number on delayed recall so far (difference +0.500; 95% CI +0.060 to +0.940; 6+6 units (23+19 events)). Fewer than 10 units per arm: this is not evidence for either arm and can still flip.',
      available: true,
      method: 'newcombe_wilson_units',
    },
    {
      metric: 'completion',
      lower_is_better: false,
      arms: [
        {
          arm_id: 'a',
          name: 'explicit',
          n: 0,
          mean: null,
          sd: null,
          n_units: 0,
          n_events: 0,
          fidelity: null,
        },
        {
          arm_id: 'b',
          name: 'socratic',
          n: 0,
          mean: null,
          sd: null,
          n_units: 0,
          n_events: 0,
          fidelity: null,
        },
      ],
      difference: null,
      ci95: null,
      reading: 'Not measurable for node-unit experiments: block_ended is per block, not per node.',
      available: false,
      method: 'unavailable',
    },
  ],
  units: [{ id: 'n1', arm: 'socratic', label: 'Softmax', ts: 'now' }],
  analysis_version: 'v2',
  units_without_data: 1,
  low_fidelity_units: 1,
  outcome_window_days: 30,
  caveats: ['1 unit(s) received the assigned arm in less than half of their tutor turns; they are excluded.'],
}

describe('Experiments', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('distinguishes failed reads from empty data and retries without a mutation', async () => {
    let fail = true
    const fetcher = vi.fn(async () => fail
      ? jsonResponse({ detail: 'Unavailable' }, 503)
      : jsonResponse({ experiments: [], templates: [], metrics: [] }))
    vi.stubGlobal('fetch', fetcher)
    renderApp(<Experiments />)
    expect(screen.queryByText(/No experiments yet/)).not.toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load experiments.')
    expect(screen.queryByText(/No experiments yet/)).not.toBeInTheDocument()
    fail = false
    fireEvent.click(screen.getByRole('button', { name: 'Retry loading experiments' }))
    expect(await screen.findByText(/No experiments yet/)).toBeInTheDocument()
    expect(fetcher).toHaveBeenCalledTimes(2)
  })

  it('recovers a results error without closing the chosen experiment', async () => {
    let fail = true
    vi.stubGlobal('fetch', vi.fn(async (url: string) => url.endsWith('/results')
      ? fail ? jsonResponse({ detail: 'Unavailable' }, 503) : jsonResponse(results)
      : jsonResponse({ experiments: [exp], templates: [], metrics: [] })))
    renderApp(<Experiments />)
    fireEvent.click(await screen.findByRole('button', { name: 'Results' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load results.')
    expect(screen.queryByText('Loading results…')).not.toBeInTheDocument()
    fail = false
    fireEvent.click(screen.getByRole('button', { name: 'Retry loading results' }))
    expect(await screen.findByText(/Analysis v2/)).toBeInTheDocument()
  })

  it('retains cached experiment and result data when invalidated reads fail', async () => {
    let fail = false
    vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === 'POST') {
        fail = true
        return jsonResponse({ ...exp, status: 'done' })
      }
      if (fail) return jsonResponse({ detail: 'Unavailable' }, 503)
      return jsonResponse(url.endsWith('/results') ? results : { experiments: [exp], templates: [], metrics: [] })
    }))
    renderApp(<Experiments />)
    fireEvent.click(await screen.findByRole('button', { name: 'Results' }))
    expect(await screen.findByText(/Analysis v2/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
    expect(await screen.findByText('Could not refresh experiments. Showing the last loaded data.')).toBeInTheDocument()
    expect(await screen.findByText('Could not refresh results. Showing the last loaded data.')).toBeInTheDocument()
    expect(screen.getByText('Socratic vs explicit')).toBeInTheDocument()
    expect(screen.getByText(/Analysis v2/)).toBeInTheDocument()
  })

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
    // units and events are both shown; events are never the sample size
    expect(
      await screen.findByText(
        /explicit: 0.50 \(6 nodes, 23 events\) · socratic: 1.00 \(6 nodes, 19 events, arm delivered in 80% of turns\) · difference \+0.50/,
      ),
    ).toBeInTheDocument()
    expect(screen.getByText(/not evidence for either arm and can still flip/)).toBeInTheDocument()
    expect(screen.getByText(/Analysis v2: the assigned node is the observation/)).toBeInTheDocument()
    expect(screen.getByText(/1 unit\(s\) did not receive their arm/)).toBeInTheDocument()
    fireEvent.click(screen.getByText(/Other metrics/, { selector: 'summary' }))
    expect(screen.getByText(/Not measurable for node-unit experiments: completion/)).toBeInTheDocument()
    expect(screen.getByText(/Method: Wilson\/Newcombe interval on unit proportions/)).toBeInTheDocument()
    expect(screen.getByText(/never as a score of you/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
    await waitFor(() => expect(posts).toContain('/api/experiments/e1/stop'))
  })
})
