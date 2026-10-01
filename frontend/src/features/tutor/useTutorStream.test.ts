import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { streamTurn, type StreamHandlers } from '../../lib/api'
import { useTutorStream } from './useTutorStream'
vi.mock('../../lib/api', () => ({ streamTurn: vi.fn() }))
afterEach(() => {
  sessionStorage.clear()
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
    result.current.stop()
    result.current.recovery.discard()
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

it('keeps the request clock through tokens and resets it on retry', async () => {
  const clock = vi.spyOn(performance, 'now').mockReturnValue(100)
  const pending: Array<{ h: StreamHandlers; finish: () => void }> = []
  vi.mocked(streamTurn).mockImplementation((_req, h) => new Promise((finish) => pending.push({ h, finish })))
  const { result } = renderHook(() => useTutorStream())
  act(() => {
    void result.current.run(request)
  })
  expect(result.current.startedAt).toBe(100)
  clock.mockReturnValue(5000)
  act(() => pending[0].h.onToken?.('A partial response'))
  expect(result.current.startedAt).toBe(100)
  act(() => result.current.stop())
  act(() => {
    void result.current.retry()
  })
  expect(result.current.startedAt).toBe(5000)
  await act(async () => {
    pending[0].finish()
    pending[1].finish()
  })
  clock.mockRestore()
})

it.each(['ok', 'partial'])(
  'uses canonical completed text while preserving partial tokens (%s)',
  async (outcome) => {
    vi.mocked(streamTurn).mockImplementation(async (_req, h) => {
      h.onToken?.('Valid sentence. Incomplete tail')
      h.onDone?.({
        turn_id: 'canonical',
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
        latency_ms: 1,
        text: 'Valid sentence.',
      })
    })
    const { result } = renderHook(() => useTutorStream())
    await act(async () => {
      await result.current.run(request)
    })
    expect(result.current.text).toBe(outcome === 'ok' ? 'Valid sentence.' : 'Valid sentence. Incomplete tail')
    expect(result.current.status).toBe(outcome === 'ok' ? 'complete' : 'partial')
  },
)

it('restores partial text and the exact retry identity after unmount without automatic sending', async () => {
  const runs: Array<{ h: StreamHandlers; finish: () => void }> = []
  vi.mocked(streamTurn).mockImplementation((_req, h) => new Promise((finish) => runs.push({ h, finish })))
  const first = renderHook(() => useTutorStream(60000, 'block-one'))
  act(() => {
    void first.result.current.run(request)
  })
  const originalKey = vi.mocked(streamTurn).mock.calls[0][3]
  act(() => {
    runs[0].h.onToken?.('Keep these words')
    first.result.current.stop()
  })
  first.unmount()
  const second = renderHook(() => useTutorStream(60000, 'block-one'))
  expect(second.result.current.text).toBe('Keep these words')
  expect(second.result.current.restored).toBe(true)
  expect(streamTurn).toHaveBeenCalledTimes(1)
  act(() => {
    void second.result.current.retry()
  })
  expect(vi.mocked(streamTurn).mock.calls[1][0]).toEqual(request)
  expect(vi.mocked(streamTurn).mock.calls[1][3]).toBe(originalKey)
  expect(second.result.current.previous?.text).toBe('Keep these words')
  await act(async () => {
    runs.forEach((run) => run.finish())
  })
})

it('does not replace unresolved work without explicit discard', async () => {
  vi.mocked(streamTurn).mockImplementation(async (_req, h) => {
    h.onToken?.('Partial')
  })
  const { result } = renderHook(() => useTutorStream(60000, 'durable-conflict'))
  await act(async () => {
    await result.current.run(request)
  })
  await act(async () => {
    await result.current.run({ ...request, text: 'Changed question' })
  })
  expect(streamTurn).toHaveBeenCalledTimes(1)
  expect(result.current.text).toBe('Partial')
  expect(result.current.error).toMatch(/earlier request/)
})

it('keeps unscoped question help ephemeral across different questions and sessions', async () => {
  sessionStorage.clear()
  vi.mocked(streamTurn).mockImplementation(async (_request, handlers) => {
    handlers.onToken?.('Help for the first question')
  })
  const first = renderHook(() => useTutorStream())
  await act(async () => {
    await first.result.current.run(request)
  })
  expect(first.result.current.text).toBe('Help for the first question')
  expect(sessionStorage.length).toBe(0)
  expect(vi.mocked(streamTurn).mock.calls[0][3]).toBeUndefined()
  first.unmount()
  const second = renderHook(() => useTutorStream())
  expect(second.result.current.text).toBe('')
  expect(second.result.current.recovery.pending).toBeNull()
  await act(async () => {
    await second.result.current.run({ ...request, session_id: 'other', text: 'Different question' })
  })
  await act(async () => {
    await second.result.current.run({ ...request, session_id: 'other', text: 'Explain instead' })
  })
  expect(streamTurn).toHaveBeenCalledTimes(3)
  expect(sessionStorage.length).toBe(0)
})
