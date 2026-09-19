import { fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { useMode } from '../stores/mode'
import { jsonResponse, renderApp } from '../test/utils'
import { Map } from './Map'

vi.mock('mermaid', () => ({
  default: { initialize: vi.fn(), render: vi.fn(async () => ({ svg: '<svg data-testid="map-svg"></svg>' })) },
}))

const map = {
  nodes: [
    {
      id: 'a',
      slug: 'dot',
      title: 'Dot product',
      domain: 'ai_ml',
      mastery: 0.71,
      dimensions: {},
      memory: { items: 3, due: 1, mean_retrievability: 0.9 },
      unlocked: true,
      is_next: false,
    },
    {
      id: 'b',
      slug: 'softmax',
      title: 'Softmax',
      domain: 'ai_ml',
      mastery: 0.0,
      dimensions: {},
      memory: { items: 0, due: 0, mean_retrievability: null },
      unlocked: true,
      is_next: true,
    },
    {
      id: 'c',
      slug: 'attn',
      title: 'Attention',
      domain: 'ai_ml',
      mastery: 0.0,
      dimensions: {},
      memory: { items: 0, due: 0, mean_retrievability: null },
      unlocked: false,
      is_next: false,
    },
  ],
  edges: [{ from: 'a', to: 'c', kind: 'prerequisite' }],
  mermaid: 'graph LR\n  n0["Dot"]',
}

describe('Map', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lists every node with mastery, memory and lock state, and starts learning an unlocked one', async () => {
    useMode.setState({ sessionId: 's1', skillId: null })
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse(map)),
    )
    renderApp(
      <Routes>
        <Route path="/map" element={<Map />} />
        <Route path="/session" element={<p>SESSION SCREEN</p>} />
      </Routes>,
      { route: '/map' },
    )
    expect(await screen.findByText('Dot product')).toBeInTheDocument()
    expect(screen.getByText(/mastery 71% · unlocked/)).toBeInTheDocument()
    expect(screen.getByText(/3 items, 1 due/)).toBeInTheDocument()
    expect(screen.getByText(/· next/)).toBeInTheDocument()
    const locked = screen.getByRole('button', { name: /locked/i })
    expect(locked).toBeDisabled()
    fireEvent.click(screen.getAllByRole('button', { name: /learn this/i })[1])
    expect(useMode.getState().skillId).toBe('b')
    expect(await screen.findByText('SESSION SCREEN')).toBeInTheDocument()
  })
})
