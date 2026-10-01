import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { TurnDone } from '../../lib/api'
import { jsonResponse, renderApp } from '../../test/utils'
import { TutorSources } from './TutorSources'

const turn: TurnDone = {
  turn_id: 'turn-1',
  model_call_id: null,
  tutor_trace_id: 'trace-1',
  registry_id: null,
  route: null,
  outcome: 'ok',
  sentences: 1,
  representation: null,
  flagged: [],
  latency_ms: 10,
  text: 'Example explanation.',
  sources: [
    { chunk_id: 'c1', citation: '[Example passage]', cited: false, flagged: [], trust_tier: 2, score: 1 },
  ],
  dropped: ['other:quarantined'],
}

afterEach(() => vi.unstubAllGlobals())

it('opens an exact passage, restores focus on close, and resets selection for another turn', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      jsonResponse({
        chunk_id: 'c1',
        citation: '[Example passage]',
        text: 'The actual source text.',
        document_title: 'Example',
        source_type: 'text',
        trust_tier: 2,
        uri: '/materials/example.txt',
        open_url: null,
      }),
    ),
  )
  const view = renderApp(<TutorSources turn={turn} />)
  fireEvent.click(screen.getByText('Sources for this explanation'))
  const trigger = screen.getByRole('button', { name: '[Example passage]' })
  fireEvent.click(trigger)
  expect(await screen.findByText('The actual source text.')).toBeInTheDocument()
  expect(screen.getByText(/not cited in the answer/)).toBeInTheDocument()
  expect(screen.getByText(/1 source withheld/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Close' }))
  expect(trigger).toHaveFocus()
  expect(trigger).toHaveAttribute('aria-expanded', 'false')
  fireEvent.click(trigger)
  view.rerender(<TutorSources turn={{ ...turn, turn_id: 'turn-2' }} />)
  expect(screen.queryByRole('region', { name: 'Source [Example passage]' })).not.toBeInTheDocument()
})

it('labels a response without retrieved sources honestly', () => {
  renderApp(<TutorSources turn={{ ...turn, sources: [], dropped: [] }} />)
  expect(screen.getByText('No course source for this explanation.')).toBeInTheDocument()
  expect(screen.queryByText('Sources for this explanation')).not.toBeInTheDocument()
})
