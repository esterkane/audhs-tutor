import { afterEach, describe, expect, it, vi } from 'vitest'
import { sseResponse } from '../test/utils'
import { streamTurn } from './api'

describe('streamTurn', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('parses meta, tokens and done events from the SSE body', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        sseResponse([
          ['meta', { turn_id: 't1', action: 'explain', hint_level: 0 }],
          ['token', { text: 'Hello ' }],
          ['token', { text: 'world' }],
          ['done', { turn_id: 't1', text: 'Hello world', sources: [] }],
        ]),
      ),
    )
    const tokens: string[] = []
    let meta: unknown
    let done: unknown
    await streamTurn(
      { session_id: 's', text: 'x', action: 'auto' },
      {
        onMeta: (m) => (meta = m),
        onToken: (t) => tokens.push(t),
        onDone: (d) => (done = d),
      },
    )
    expect(tokens.join('')).toBe('Hello world')
    expect(meta).toMatchObject({ action: 'explain' })
    expect(done).toMatchObject({ turn_id: 't1' })
  })
})
