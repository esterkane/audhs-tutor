import { afterEach, expect, it, vi } from 'vitest'
import { loadSession, SESSION_LOAD_TIMEOUT_MS } from './loadSession'

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

it('times out an ignored abort and discards its late result', async () => {
  vi.useFakeTimers()
  let resolve!: (r: Response) => void
  let signal: AbortSignal | undefined
  vi.stubGlobal(
    'fetch',
    vi.fn((_url, init) => {
      signal = init.signal
      return new Promise<Response>((r) => {
        resolve = r
      })
    }),
  )
  const pending = loadSession('first', new AbortController().signal)
  const rejected = expect(pending).rejects.toThrow('took too long')
  await vi.advanceTimersByTimeAsync(SESSION_LOAD_TIMEOUT_MS)
  await rejected
  expect(signal?.aborted).toBe(true)
  resolve(new Response(JSON.stringify({ id: 'obsolete' })))
  await Promise.resolve()
  expect(vi.getTimerCount()).toBe(0)
})

it('cancels obsolete reads even when transport ignores cancellation', async () => {
  vi.useFakeTimers()
  vi.stubGlobal(
    'fetch',
    vi.fn(() => new Promise(() => {})),
  )
  const controller = new AbortController()
  const pending = loadSession('first', controller.signal)
  const rejected = expect(pending).rejects.toThrow('cancelled')
  controller.abort()
  await rejected
  expect(vi.getTimerCount()).toBe(0)
})
