import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { startMic } from './audio'
import { useVoiceLoop } from './useVoiceLoop'
vi.mock('./audio', async (original) => ({
  ...(await original<typeof import('./audio')>()),
  startMic: vi.fn(),
}))
class Socket {
  readyState = 0
  sent: string[] = []
  binaryType = ''
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  send(value: string) {
    if (this.readyState !== 1) throw new Error('not open')
    this.sent.push(value)
  }
  close() {
    this.readyState = 3
    this.onclose?.()
  }
  open() {
    this.readyState = 1
    this.onopen?.()
  }
  ready() {
    this.onmessage?.({ data: '{"type":"ready"}' })
  }
}
afterEach(() => vi.useRealTimers())
it('closes during CONNECTING without sending and ignores late callbacks', () => {
  const ws = new Socket()
  const { result } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }),
  )
  act(() => result.current.connect())
  expect(() => act(() => result.current.close())).not.toThrow()
  act(() => ws.open())
  expect(ws.sent).toEqual([])
  expect(result.current.status).toBe('idle')
})
it('returns false without losing the answer when text cannot be sent and reconnects cleanly', () => {
  const first = new Socket(),
    second = new Socket()
  const factory = vi.fn().mockReturnValueOnce(first).mockReturnValueOnce(second)
  const { result } = renderHook(() => useVoiceLoop({ sessionId: 's', makeSocket: factory }))
  act(() => result.current.connect())
  expect(result.current.sendText('keep this')).toBe(false)
  act(() => {
    first.open()
    first.ready()
  })
  act(() => {
    expect(result.current.sendText('hello')).toBe(true)
  })
  act(() => first.onerror?.())
  act(() => result.current.connect())
  act(() => {
    second.open()
    second.ready()
    first.onclose?.()
  })
  expect(result.current.status).toBe('ready')
  expect(second.sent).toHaveLength(1)
})
it('times out a socket that never becomes ready', () => {
  vi.useFakeTimers()
  const ws = new Socket()
  const { result } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }),
  )
  act(() => result.current.connect())
  act(() => vi.advanceTimersByTime(15000))
  expect(result.current.status).toBe('error')
  expect(ws.readyState).toBe(3)
})

it('disposes late microphone permission after Stop and prevents same-render duplicate sends', async () => {
  const ws = new Socket()
  let resolve!: (mic: Awaited<ReturnType<typeof startMic>>) => void
  vi.mocked(startMic).mockImplementation(
    () =>
      new Promise((r) => {
        resolve = r
      }),
  )
  const { result } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }),
  )
  act(() => result.current.connect())
  act(() => {
    ws.open()
    ws.ready()
  })
  let pending!: Promise<void>
  act(() => {
    pending = result.current.listen()
  })
  act(() => result.current.close())
  const stop = vi.fn()
  await act(async () => {
    resolve({ stop })
    await pending
  })
  expect(stop).toHaveBeenCalledOnce()
  const fresh = new Socket()
  // The second hook isolates the synchronous send guard from the disposed microphone path.
  const second = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => fresh as unknown as WebSocket }),
  )
  act(() => second.result.current.connect())
  act(() => {
    fresh.open()
    fresh.ready()
  })
  act(() => {
    expect(second.result.current.sendText('first')).toBe(true)
    expect(second.result.current.sendText('second')).toBe(false)
  })
  expect(fresh.sent.filter((x) => JSON.parse(x).type === 'text')).toHaveLength(1)
})

it('retains recovery only for completed voice turns', () => {
  const ws = new Socket()
  const { result } = renderHook(() => useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }))
  act(() => { result.current.connect(); ws.open(); ws.ready() })
  const turn = { turn_id: 't', text: 'Delivered answer', save_error: 'Save failed', save_receipt: 'receipt' }
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'done', turn: { ...turn, outcome: 'ok' } }) }))
  expect(result.current.saveTurn?.save_receipt).toBe('receipt')
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'done', turn: { ...turn, outcome: 'partial' } }) }))
  expect(result.current.saveTurn).toBeNull()
  expect(result.current.answer).toBe('Delivered answer')
})
