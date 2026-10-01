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

it('sends the identity header and exposes an unresolved claim without generic HTTP wording', async () => {
  const fetcher = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(
    async () =>
      new Response(
        JSON.stringify({
          error: {
            code: 'request_unresolved',
            message: 'The original request is still unresolved.',
          },
        }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      ),
  )
  vi.stubGlobal('fetch', fetcher)
  const onError = vi.fn()
  await streamTurn({ session_id: 's', text: 'x' }, { onError }, undefined, 'request-identity')
  expect(fetcher.mock.calls[0][1]?.headers).toMatchObject({ 'Idempotency-Key': 'request-identity' })
  expect(onError).toHaveBeenCalledWith({
    code: 'request_unresolved',
    message: 'The original request is still unresolved.',
  })
  vi.unstubAllGlobals()
})
