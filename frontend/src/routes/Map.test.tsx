import { fireEvent, screen, waitFor, act, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { useMode } from '../stores/mode'
import { jsonResponse, renderApp } from '../test/utils'
import { Map } from './Map'
import { useLocation, MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import mermaid from 'mermaid'
function SelectedLesson() {
  return <p>{useLocation().search}</p>
}

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
        <Route path="/" element={<SelectedLesson />} />
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
    expect(await screen.findByText('?lesson=b')).toBeInTheDocument()
    expect(useMode.getState().skillId).toBeNull()
  })
})

it('retries a failed drawing while preserving the accessible nodes', async () => {
  vi.mocked(mermaid.render).mockRejectedValueOnce(new Error('fixture rendering failure'))
  vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(map)))
  renderApp(<Map />)
  const retry = await screen.findByRole('button', { name: 'Retry diagram' })
  expect(screen.getByText('Dot product')).toBeVisible()
  fireEvent.click(retry)
  expect(await screen.findByTestId('map-svg')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Retry diagram' })).toBeNull()
})
it('uses distinct render identities and ignores a retired drawing after data refresh', async () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const ids: string[] = []
  let releaseOld!: () => void
  vi.mocked(mermaid.render).mockImplementationOnce((id) => {
    ids.push(id)
    return new Promise(resolve => { releaseOld = () => resolve({ svg: '<svg data-testid="obsolete-map"></svg>', diagramType: 'flowchart' }) })
  }).mockImplementationOnce(async (id) => { ids.push(id); return { svg: '<svg data-testid="latest-map"></svg>', diagramType: 'flowchart' } })
  vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(map)))
  render(<QueryClientProvider client={qc}><MemoryRouter><Map /></MemoryRouter></QueryClientProvider>)
  await waitFor(() => expect(releaseOld).toBeTypeOf('function'))
  act(() => qc.setQueryData(['skill-map', ''], { ...map, mermaid: 'graph LR; b[New]' }))
  expect(await screen.findByTestId('latest-map')).toBeInTheDocument()
  await act(async () => { releaseOld(); await Promise.resolve() })
  expect(ids[0]).not.toBe(ids[1])
  expect(screen.queryByTestId('obsolete-map')).toBeNull()
  expect(screen.getByTestId('latest-map')).toBeInTheDocument()
})
