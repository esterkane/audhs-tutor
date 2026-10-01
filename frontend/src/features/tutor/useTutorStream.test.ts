import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { streamTurn, type StreamHandlers } from '../../lib/api'
import { useTutorStream } from './useTutorStream'
vi.mock('../../lib/api', () => ({ streamTurn: vi.fn() }))
afterEach(() => {
  vi.clearAllMocks()
  vi.useRealTimers()
})
const request = { session_id: 's', skill_id: 'k', text: 'Explain this' }
it('ignores old callbacks and finalization after a replacement starts', async () => {
  const runs: Array<{ h: StreamHandlers; finish: () => void }> = []
  vi.mocked(streamTurn).mockImplementation(
    (_req, h) => new Promise((resolve) => runs.push({ h, finish: resolve })),
  )
  const { result } = renderHook(() => useTutorStream())
  let first!: Promise<void>
  let second!: Promise<void>
  act(() => {
    first = result.current.run(request)
  })
  act(() => {
    runs[0].h.onToken?.('old')
  })
  act(() => {
    second = result.current.run({ ...request, text: 'New question' })
  })
  await act(async () => {
    runs[0].h.onToken?.('late')
    runs[0].finish()
    await first
  })
  expect(result.current.busy).toBe(true)
  expect(result.current.text).toBe('')
  act(() => result.current.stop())
  await act(async () => {
    runs[1].finish()
    await second
  })
})

it('stops immediately, retains received text, and retries the exact request', async () => {
  const runs: Array<{ h: StreamHandlers; finish: () => void }> = []
  vi.mocked(streamTurn).mockImplementation(
    (_req, h) => new Promise((resolve) => runs.push({ h, finish: resolve })),
  )
  const { result } = renderHook(() => useTutorStream())
  act(() => {
    void result.current.run(request)
  })
  act(() => {
    runs[0].h.onToken?.('Partial explanation')
    result.current.stop()
  })
  expect(result.current.status).toBe('stopped')
  expect(result.current.busy).toBe(false)
  expect(result.current.text).toBe('Partial explanation')
  act(() => {
    void result.current.retry()
  })
  expect(vi.mocked(streamTurn).mock.calls[1][0]).toEqual(request)
  expect(result.current.previous?.text).toBe('Partial explanation')
  await act(async () => {
    runs[0].finish()
    runs[1].finish()
  })
  expect(result.current.status).toBe('failed')
})

it('retains partial text when transport fails or EOF arrives without completion', async () => {
  vi.mocked(streamTurn).mockImplementation(async (_req, h) => {
    h.onToken?.('Keep this')
    throw new Error('offline')
  })
  const { result } = renderHook(() => useTutorStream())
  await act(async () => {
    await result.current.run(request)
  })
  expect(result.current).toMatchObject({
    text: 'Keep this',
    error: 'offline',
    status: 'partial',
    busy: false,
  })
  vi.mocked(streamTurn).mockImplementation(async (_req, h) => {
    h.onToken?.('Interrupted')
  })
  await act(async () => {
    await result.current.run(request)
  })
  expect(result.current.status).toBe('partial')
  expect(result.current.error).toContain('before completion')
})

it('times out an idle response and ignores subsequent tokens', async () => {
  vi.useFakeTimers()
  let handlers!: StreamHandlers
  let finish!: () => void
  vi.mocked(streamTurn).mockImplementation((_req, h) => {
    handlers = h
    return new Promise((resolve) => {
      finish = resolve
    })
  })
  const { result } = renderHook(() => useTutorStream(100))
  act(() => {
    void result.current.run(request)
    handlers.onToken?.('Retained')
  })
  act(() => {
    vi.advanceTimersByTime(101)
  })
  expect(result.current).toMatchObject({ status: 'partial', busy: false, text: 'Retained' })
  act(() => handlers.onToken?.(' late'))
  expect(result.current.text).toBe('Retained')
  await act(async () => finish())
})

for (const outcome of ['ok', 'partial']) {
  it(`preserves terminal ${outcome} status and evidence despite late callbacks`, async () => {
    const done = {
      turn_id: 'turn',
      model_call_id: null,
      tutor_trace_id: 'trace',
      registry_id: null,
      route: null,
      outcome,
      sentences: 1,
      representation: null,
      sources: [],
      flagged: [],
      dropped: [],
      latency_ms: 10,
      text: 'Answer',
    }
    vi.mocked(streamTurn).mockImplementation(async (_req, h) => {
      h.onToken?.('Answer')
      h.onDone?.(done)
      h.onToken?.('late')
      h.onError?.({ code: 'late', message: 'Late error' })
    })
    const { result } = renderHook(() => useTutorStream())
    await act(async () => {
      await result.current.run(request)
    })
    expect(result.current).toMatchObject({
      text: 'Answer',
      done,
      error: null,
      busy: false,
      status: outcome === 'ok' ? 'complete' : 'partial',
    })
  })
}
