import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { jsonResponse, renderApp } from '../test/utils'
import { Models } from './Models'

const models = {
  models: [
    {
      id: 'llama31-8b',
      display_name: 'Llama 3.1 8B',
      source: 'ollama_library',
      repo_id: 'llama3.1',
      file_or_tag: 'llama3.1:8b',
      runtime: 'ollama',
      role: 'chat',
      quant: 'Q4_K_M',
      size_gb: 4.9,
      context_len: 131072,
      licence: 'Llama 3.1',
      status: 'ready',
      benchmark: { tok_per_s: 47.5, first_token_ms: 120, tutoring_hard_checks: { passed: 4, total: 5 } },
      price_in_per_mtok: 0,
      price_out_per_mtok: 0,
      local_path: null,
      updated_at: 'now',
    },
    {
      id: 'gemma3-12b',
      display_name: 'Gemma 3 12B',
      source: 'ollama_library',
      repo_id: 'gemma3',
      file_or_tag: 'gemma3:12b',
      runtime: 'ollama',
      role: 'chat',
      quant: null,
      size_gb: null,
      context_len: null,
      licence: 'Gemma',
      status: 'available',
      benchmark: null,
      price_in_per_mtok: 0,
      price_out_per_mtok: 0,
      local_path: null,
      updated_at: 'now',
    },
  ],
}
const routing = {
  profile: 'default',
  routes: [
    {
      task: 'chat',
      override: null,
      chain: [{ registry_id: 'llama31-8b', status: 'ready' }],
      resolved: 'llama31-8b',
    },
  ],
}

describe('Models', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lists the registry with status and bench, downloads only on click, shows routing', async () => {
    const pulls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/pull') && init?.method === 'POST') {
          pulls.push(url)
          return jsonResponse(
            { id: 'j1', kind: 'pull', registry_id: 'gemma3-12b', status: 'running', log: [] },
            202,
          )
        }
        if (url.endsWith('/api/models/jobs')) return jsonResponse({ jobs: [] })
        if (url.endsWith('/api/models/routing')) return jsonResponse(routing)
        if (url.endsWith('/api/models')) return jsonResponse(models)
        return jsonResponse({})
      }),
    )
    renderApp(
      <Routes>
        <Route path="/models" element={<Models />} />
      </Routes>,
      { route: '/models' },
    )
    expect(await screen.findByText('Llama 3.1 8B')).toBeInTheDocument()
    expect(screen.getByText(/47.5 tok\/s · first token 120 ms · tutoring checks 4\/5/)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Download' })).toHaveLength(1) // only the available one
    expect(pulls).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Download' }))
    await waitFor(() => expect(pulls).toHaveLength(1))
    expect(pulls[0]).toContain('/api/models/gemma3-12b/pull')
    fireEvent.click(screen.getByText('Routing: which model does each task use'))
    expect(await screen.findByText('llama31-8b (ready)')).toBeInTheDocument()
  })
})
