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
      problem: null,
      action: null,
    },
    {
      task: 'grade_rubric',
      override: null,
      chain: [{ registry_id: 'hosted-strong', status: 'available' }],
      resolved: null,
      problem: 'hosted-strong is hosted and ANTHROPIC_API_KEY is empty',
      action: 'set ANTHROPIC_API_KEY in .env and restart the backend',
    },
  ],
}
const costs = {
  daily_cap_usd: 1.5,
  day_start: '2026-09-20T00:00:00+00:00',
  window_start: '2026-09-20T00:00:00+00:00',
  today: {
    counted: 0.2134,
    remaining: 1.2866,
    reported: 0.2,
    estimated: 0.0034,
    unknown_reserved: 0.01,
    legacy: 0,
    open_reservations: 0,
  },
  window: {
    hosted_calls: 3,
    free_calls: 12,
    failed_calls: 1,
    cancelled_calls: 0,
    blocked_calls: 0,
    retried_requests: 1,
    unknown_calls: 1,
    legacy_rows: 0,
    open_reservations: 0,
    expired_reservations: 0,
  },
  by_task: [
    {
      key: 'grade_rubric',
      calls: 3,
      failed: 1,
      cost_usd: 0.2034,
      unknown_usd: 0.01,
      tokens_in: 3000,
      tokens_out: 300,
    },
  ],
  by_provider: [],
  recent_failures: [
    {
      ts: '2026-09-20T10:00:00+00:00',
      request_id: 'r1',
      attempt: 1,
      registry_id: 'hosted-strong',
      task: 'grade_rubric',
      route: 'primary',
      outcome: 'error',
      cost_status: 'unknown',
      reserved_usd: 0.01,
      error: 'timeout',
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
        if (url.includes('/api/models/costs')) return jsonResponse(costs)
        if (url.endsWith('/api/voice/readiness'))
          return jsonResponse({
            stt: { ready: false, status: 'available', detail: 'not downloaded', action: 'pull it' },
            tts: { ready: false, status: 'available', detail: 'no server', action: 'start it' },
            vad: { ready: true, status: 'fallback', detail: 'energy', action: 'pull silero' },
            tools: { ready: true, status: 'ready', detail: 'browser mic', action: null },
            activated: false,
            retain_audio: false,
            retention_days: 7,
            voice: 'af_heart',
            can_activate: false,
            stt_id: 'whisper-large-v3-turbo',
            tts_id: 'kokoro-82m',
            vad_id: 'silero-vad',
            conversation_lang: '',
            conversation_lang_supported: true,
            notes: [],
          })
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
    // an unavailable route names the problem and the one step that fixes it
    expect(screen.getByText(/ANTHROPIC_API_KEY is empty/)).toBeInTheDocument()
    expect(screen.getByText('set ANTHROPIC_API_KEY in .env and restart the backend')).toBeInTheDocument()
    // the cost view keeps reported / estimated / unknown apart and shows failures
    expect(screen.getByText(/\$0\.2134/)).toBeInTheDocument()
    expect(
      screen.getByText('Reported by the provider (never below the registry estimate)'),
    ).toBeInTheDocument()
    expect(screen.getByText('$0.2000')).toBeInTheDocument()
    expect(screen.getByText('$0.0034')).toBeInTheDocument()
    expect(screen.getByText(/Unknown billing \(failed calls/)).toBeInTheDocument()
    fireEvent.click(screen.getByText(/Failed, stopped or retried calls \(1\)/))
    expect(screen.getByText(/attempt 1 · error · billing unknown · timeout/)).toBeInTheDocument()
  })
})
