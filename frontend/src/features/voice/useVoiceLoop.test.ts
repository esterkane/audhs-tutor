import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Player, startMic } from './audio'
import { claimReading, updateReading, useReadingControls } from './readingOwner'
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
  const { result } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }),
  )
  act(() => {
    result.current.connect()
    ws.open()
    ws.ready()
  })
  const turn = { turn_id: 't', text: 'Delivered answer', save_error: 'Save failed', save_receipt: 'receipt' }
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'done', turn: { ...turn, outcome: 'ok' } }) }))
  expect(result.current.saveTurn?.save_receipt).toBe('receipt')
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'done', turn: { ...turn, outcome: 'partial' } }) }))
  expect(result.current.saveTurn).toBeNull()
  expect(result.current.answer).toBe('Delivered answer')
})

it('keeps interrupted text and ignores late turn messages until an explicit new turn', () => {
  const audio = vi.spyOn(Player.prototype, 'enqueue').mockImplementation(() => {})
  const ws = new Socket()
  const { result } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }),
  )
  const message = (value: object) => act(() => ws.onmessage?.({ data: JSON.stringify(value) }))
  act(() => result.current.connect())
  act(() => {
    ws.open()
    ws.ready()
  })
  act(() => {
    result.current.sendText('Original question')
  })
  message({ type: 'token', text: 'Keep this partial text' })
  act(() => result.current.interrupt())
  message({ type: 'token', text: ' stale continuation' })
  message({ type: 'audio', pcm16_b64: 'AAA=', sample_rate: 24000 })
  expect(audio).not.toHaveBeenCalled()
  message({ type: 'interrupted' })
  expect(result.current.status).toBe('stopping')
  expect(result.current.sendText('Too early')).toBe(false)
  message({ type: 'done', turn: { turn_id: 'old', outcome: 'ok', text: 'Old final text' } })
  expect(result.current.answer).toBe('Keep this partial text')
  expect(result.current.saveTurn?.turn_id).toBe('old')
  expect(result.current.status).toBe('ready')
  act(() => {
    expect(result.current.sendText('New question')).toBe(true)
  })
  message({ type: 'token', text: 'New answer' })
  expect(result.current.answer).toBe('New answer')
  audio.mockRestore()
})

it('closes a stalled interrupted turn without losing delivered text or allowing stale callbacks', () => {
  vi.useFakeTimers()
  const ws = new Socket()
  const { result } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }),
  )
  act(() => result.current.connect())
  act(() => {
    ws.open()
    ws.ready()
  })
  act(() => {
    result.current.sendText('Question')
  })
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'token', text: 'Retain this' }) }))
  act(() => result.current.interrupt())
  act(() => vi.advanceTimersByTime(15000))
  expect(result.current.status).toBe('error')
  expect(ws.readyState).toBe(3)
  expect(result.current.answer).toBe('Retain this')
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'token', text: 'Too late' }) }))
  expect(result.current.answer).toBe('Retain this')
})

it('waits for empty-transcription acknowledgement and clears its timer before a new turn', () => {
  vi.useFakeTimers()
  const ws = new Socket()
  const { result } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }),
  )
  act(() => result.current.connect())
  act(() => {
    ws.open()
    ws.ready()
  })
  act(() => result.current.stopListening())
  act(() => result.current.interrupt())
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'nothing_heard' }) }))
  expect(result.current.status).toBe('stopping')
  expect(result.current.sendText('Too soon')).toBe(false)
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'interrupted' }) }))
  expect(result.current.status).toBe('ready')
  act(() => {
    expect(result.current.sendText('Next question')).toBe(true)
  })
  act(() => vi.advanceTimersByTime(15000))
  expect(result.current.status).toBe('thinking')
  expect(ws.readyState).toBe(1)
})

it('negotiates typed identities and rejects late content from another request', () => {
  const audio = vi.spyOn(Player.prototype, 'enqueue').mockImplementation(() => {})
  const ws = new Socket()
  const { result } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }),
  )
  const message = (value: object) => act(() => ws.onmessage?.({ data: JSON.stringify(value) }))
  act(() => result.current.connect())
  act(() => ws.open())
  message({ type: 'ready', request_identity: 'typed-v1' })
  act(() => {
    expect(result.current.sendText('First')).toBe(true)
  })
  const first = JSON.parse(ws.sent.at(-1)!).request_id
  expect(first).toMatch(/^[a-f0-9-]{36}$/)
  message({ type: 'token', request_id: first, text: 'First answer' })
  message({ type: 'done', request_id: first, turn: { turn_id: 'one', text: 'First answer', outcome: 'ok' } })
  act(() => {
    expect(result.current.sendText('Second')).toBe(true)
  })
  const second = JSON.parse(ws.sent.at(-1)!).request_id
  expect(second).not.toBe(first)
  message({ type: 'token', request_id: first, text: 'Stale' })
  message({ type: 'audio', request_id: first, pcm16_b64: 'AAA=', sample_rate: 24000 })
  expect(audio).not.toHaveBeenCalled()
  message({ type: 'done', request_id: first, turn: { turn_id: 'one', text: 'Stale final', outcome: 'ok' } })
  message({ type: 'token', text: 'Unidentified stale text' })
  expect(result.current.answer).toBe('')
  expect(result.current.status).toBe('thinking')
  message({ type: 'token', request_id: second, text: 'Second answer' })
  expect(result.current.answer).toBe('Second answer')
  audio.mockRestore()
})

it('shows untagged startup errors after reconnecting an identified conversation', () => {
  const first = new Socket(),
    second = new Socket()
  const factory = vi.fn().mockReturnValueOnce(first).mockReturnValueOnce(second)
  const { result } = renderHook(() => useVoiceLoop({ sessionId: 's', makeSocket: factory }))
  act(() => result.current.connect())
  act(() => {
    first.open()
    first.onmessage?.({ data: JSON.stringify({ type: 'ready', request_identity: 'typed-v1' }) })
  })
  act(() => {
    result.current.sendText('First')
  })
  act(() => first.onerror?.())
  act(() => result.current.connect())
  act(() => {
    second.open()
    second.onmessage?.({ data: JSON.stringify({ type: 'error', message: 'Session unavailable' }) })
  })
  expect(result.current.error).toBe('Session unavailable')
  expect(result.current.status).toBe('error')
})

it('identifies microphone capture and stops recording at the matching processing boundary', async () => {
  const ws = new Socket()
  const stop = vi.fn()
  let frame!: (pcm: Int16Array) => void
  vi.mocked(startMic).mockImplementation(async (callback) => {
    frame = callback
    return { stop }
  })
  const { result } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }),
  )
  act(() => result.current.connect())
  act(() => {
    ws.open()
    ws.onmessage?.({ data: JSON.stringify({ type: 'ready', request_identity: 'utterance-v1' }) })
  })
  await act(async () => {
    await result.current.listen()
  })
  const capture = JSON.parse(ws.sent.at(-1)!)
  expect(capture.type).toBe('capture')
  expect(capture.request_id).toMatch(/^[a-f0-9-]{36}$/)
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'processing', request_id: 'another' }) }))
  expect(stop).not.toHaveBeenCalled()
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'processing', request_id: capture.request_id }) }))
  expect(stop).toHaveBeenCalledOnce()
  expect(result.current.status).toBe('thinking')
  const sends = ws.sent.length
  act(() => frame(new Int16Array([1, 2])))
  expect(ws.sent).toHaveLength(sends)
  act(() =>
    ws.onmessage?.({
      data: JSON.stringify({ type: 'transcript', request_id: capture.request_id, text: 'My speech' }),
    }),
  )
  expect(result.current.transcript).toBe('My speech')
})

it('sends scoped interruption controls and ignores stale acknowledgements', () => {
  const ws = new Socket()
  const { result } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }),
  )
  const message = (value: object) => act(() => ws.onmessage?.({ data: JSON.stringify(value) }))
  act(() => result.current.connect())
  act(() => ws.open())
  message({ type: 'ready', request_identity: 'utterance-v1', control_identity: true })
  act(() => {
    result.current.sendText('Current question')
  })
  const identity = JSON.parse(ws.sent.at(-1)!).request_id
  act(() => result.current.interrupt())
  expect(JSON.parse(ws.sent.at(-1)!)).toEqual({ type: 'interrupt', request_id: identity })
  message({ type: 'done', request_id: identity, turn: null })
  message({ type: 'interrupted', request_id: 'previous' })
  message({ type: 'interrupted' })
  expect(result.current.status).toBe('stopping')
  expect(result.current.sendText('Too soon')).toBe(false)
  message({ type: 'interrupted', request_id: identity })
  expect(result.current.status).toBe('ready')
})

it('records an identified turn before sending and refuses a turn when recovery storage rejects it', () => {
  const ws = new Socket()
  const admitted: string[] = []
  const onRequest = vi.fn((id: string) => {
    admitted.push(id)
    return false
  })
  const onTerminal = vi.fn()
  const hook = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket, onRequest, onTerminal }),
  )
  act(() => {
    hook.result.current.connect()
    ws.open()
  })
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'ready', request_identity: 'utterance-v1' }) }))
  act(() => {
    expect(hook.result.current.sendText('Keep my draft')).toBe(false)
  })
  expect(ws.sent.map((x) => JSON.parse(x).type)).toEqual(['start'])
  onRequest.mockImplementation((id) => {
    expect(ws.sent).toHaveLength(1)
    admitted.push(id)
    return true
  })
  act(() => {
    expect(hook.result.current.sendText('Send once')).toBe(true)
  })
  const sent = JSON.parse(ws.sent[1])
  expect(sent.request_id).toBe(admitted.at(-1))
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'done', request_id: 'stale', turn: null }) }))
  expect(onTerminal).not.toHaveBeenCalled()
  act(() =>
    ws.onmessage?.({ data: JSON.stringify({ type: 'done', request_id: sent.request_id, turn: null }) }),
  )
  expect(onTerminal).toHaveBeenCalledExactlyOnceWith(sent.request_id)
})

it('does not displace a reading on connect, empty send or text-only send', () => {
  const stop = vi.fn()
  const release = claimReading(stop)
  const ws = new Socket()
  const { result, unmount } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', textOnly: true, makeSocket: () => ws as unknown as WebSocket }),
  )
  act(() => {
    result.current.connect()
    ws.open()
    ws.ready()
  })
  act(() => {
    expect(result.current.sendText('')).toBe(false)
    expect(result.current.sendText('hello')).toBe(true)
  })
  expect(stop).not.toHaveBeenCalled()
  unmount()
  release()
})

it('voice Send replaces reading, owns queued audio through done, and releases on drain', () => {
  const stop = vi.fn()
  claimReading(stop)
  const players: Player[] = []
  let pending = 0
  const enqueue = vi.spyOn(Player.prototype, 'enqueue').mockImplementation(function (this: Player) {
    players.push(this)
    pending++
  })
  const count = vi.spyOn(Player.prototype, 'pending').mockImplementation(() => pending)
  const ws = new Socket()
  const { result, unmount } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }),
  )
  act(() => {
    result.current.connect()
    ws.open()
    ws.ready()
  })
  act(() => {
    result.current.sendText('hello')
  })
  expect(stop).toHaveBeenCalledWith('voice activity')
  act(() =>
    ws.onmessage?.({ data: JSON.stringify({ type: 'audio', pcm16_b64: 'AAAA', sample_rate: 24000 }) }),
  )
  act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'done', turn: { text: 'Reply' } }) }))
  expect(useReadingControls.getState().reading).toMatchObject({ kind: 'voice', status: 'speaking' })
  act(() => {
    pending = 0
    players[0].onIdle?.()
  })
  expect(useReadingControls.getState().reading).toBeNull()
  expect(result.current.answer).toBe('Reply')
  unmount()
  enqueue.mockRestore()
  count.mockRestore()
})

it('a reading displaces pending microphone acquisition and preserves received voice text', async () => {
  let resolve!: (mic: Awaited<ReturnType<typeof startMic>>) => void
  vi.mocked(startMic).mockImplementation(
    () =>
      new Promise((r) => {
        resolve = r
      }),
  )
  const ws = new Socket()
  const { result, unmount } = renderHook(() =>
    useVoiceLoop({
      sessionId: 's',
      initialText: { transcript: 'Earlier question', answer: 'Earlier answer', interrupted: false },
      makeSocket: () => ws as unknown as WebSocket,
    }),
  )
  act(() => {
    result.current.connect()
    ws.open()
    ws.ready()
  })
  let listening!: Promise<void>
  act(() => {
    listening = result.current.listen()
  })
  let release!: () => void
  act(() => {
    release = claimReading(vi.fn())
    updateReading(release, {
      status: 'New reading',
      ready: true,
      paused: false,
      changing: false,
      stop: vi.fn(),
      togglePause: vi.fn(),
    })
  })
  const stop = vi.fn()
  await act(async () => {
    resolve({ stop } as Awaited<ReturnType<typeof startMic>>)
    await listening
  })
  expect(stop).toHaveBeenCalledOnce()
  expect(ws.readyState).toBe(3)
  expect(result.current.answer).toBe('Earlier answer')
  expect(result.current.audioNotice).toMatch(/another reading started/)
  const enqueue = vi.spyOn(Player.prototype, 'enqueue')
  act(() =>
    ws.onmessage?.({ data: JSON.stringify({ type: 'audio', pcm16_b64: 'AAAA', sample_rate: 24000 }) }),
  )
  expect(enqueue).not.toHaveBeenCalled()
  unmount()
  expect(useReadingControls.getState().reading?.status).toBe('New reading')
  release()
  enqueue.mockRestore()
})

it('shared stop closes microphone and socket without erasing the conversation', async () => {
  const stop = vi.fn()
  vi.mocked(startMic).mockResolvedValue({ stop } as Awaited<ReturnType<typeof startMic>>)
  const ws = new Socket()
  const { result } = renderHook(() =>
    useVoiceLoop({
      sessionId: 's',
      initialText: { transcript: 'Question', answer: 'Answer', interrupted: false },
      makeSocket: () => ws as unknown as WebSocket,
    }),
  )
  act(() => {
    result.current.connect()
    ws.open()
    ws.ready()
  })
  await act(async () => {
    await result.current.listen()
  })
  expect(useReadingControls.getState().reading).toMatchObject({ kind: 'voice', status: 'listening' })
  act(() => useReadingControls.getState().reading?.stop())
  expect(stop).toHaveBeenCalledOnce()
  expect(ws.readyState).toBe(3)
  expect(result.current.answer).toBe('Answer')
  expect(useReadingControls.getState().reading).toBeNull()
})

it('releases voice controls after a failed send or socket error', () => {
  const ws = new Socket()
  const { result } = renderHook(() =>
    useVoiceLoop({ sessionId: 's', makeSocket: () => ws as unknown as WebSocket }),
  )
  act(() => {
    result.current.connect()
    ws.open()
    ws.ready()
  })
  const send = vi.spyOn(ws, 'send').mockImplementation(() => {
    throw new Error('send failed')
  })
  act(() => {
    expect(result.current.sendText('hello')).toBe(false)
  })
  expect(useReadingControls.getState().reading).toBeNull()
  send.mockRestore()
  act(() => {
    result.current.close()
    result.current.connect()
    ws.open()
    ws.ready()
  })
  act(() => {
    result.current.sendText('retry')
  })
  expect(useReadingControls.getState().reading?.kind).toBe('voice')
  act(() => ws.onerror?.())
  expect(useReadingControls.getState().reading).toBeNull()
})
