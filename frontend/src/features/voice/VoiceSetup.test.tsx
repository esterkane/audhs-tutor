import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { jsonResponse, renderApp } from '../../test/utils'
import { VoiceSetup } from './VoiceSetup'

const notReady = {
  stt: {
    ready: false,
    status: 'available',
    detail: 'MLX Whisper snapshot not downloaded',
    action: 'Models › pull whisper-large-v3-turbo (about 1.6 GB, mlx-community, MIT)',
  },
  tts: {
    ready: false,
    status: 'available',
    detail: 'no Kokoro server at http://localhost:8880',
    action: 'Kokoro is a persistent server you start yourself…',
  },
  vad: {
    ready: true,
    status: 'fallback',
    detail: 'silero-vad not installed; energy detector in use',
    action: 'Models › pull silero-vad (2 MB, MIT)',
  },
  tools: { ready: true, status: 'ready', detail: 'browser microphone', action: null },
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
}

describe('VoiceSetup', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows each component with its next step, installs only on click, and cannot activate until ready', async () => {
    const posts: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method === 'POST') posts.push(url)
        if (url.endsWith('/api/voice/readiness')) return jsonResponse(notReady)
        if (url.endsWith('/api/voice/verify'))
          return jsonResponse({
            stt: null,
            tts: null,
            problems: [
              'speech recognition is not installed (see readiness)',
              'the Kokoro voice server is not reachable (see readiness)',
            ],
          })
        if (url.endsWith('/pull'))
          return jsonResponse(
            { id: 'j1', kind: 'pull', registry_id: 'whisper-large-v3-turbo', status: 'running', log: [] },
            202,
          )
        return jsonResponse({})
      }),
    )
    const { container } = renderApp(<VoiceSetup />)
    expect(await screen.findByText(/MLX Whisper snapshot not downloaded/)).toBeInTheDocument()
    expect(screen.getByText(/Models › pull whisper-large-v3-turbo/)).toBeInTheDocument()
    expect(screen.getByText(/no Kokoro server/)).toBeInTheDocument()
    expect(screen.getByText(/energy detector in use/)).toBeInTheDocument()
    expect(posts).toHaveLength(0) // nothing downloads on load
    expect(screen.getByRole('button', { name: '4 · Activate voice' })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Test my microphone/ })).toBeDisabled()
    expect(await axe(container)).toHaveNoViolations()
    fireEvent.click(screen.getByRole('button', { name: /Download speech recognition/ }))
    await waitFor(() => expect(posts.some((u) => u.endsWith('/whisper-large-v3-turbo/pull'))).toBe(true))
    fireEvent.click(screen.getByRole('button', { name: /Verify the components load/ }))
    expect(await screen.findByText(/speech recognition is not installed/)).toBeInTheDocument()
    expect(screen.getByText(/Not activated: sessions stay text-only/)).toBeInTheDocument()
  })
})
