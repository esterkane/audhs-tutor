import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { cacheKey, readTextCache, writeTextCache } from './streamCache'
import { useLessonDraft } from './useLessonDraft'

afterEach(() => {
  vi.restoreAllMocks()
  sessionStorage.clear()
})
it('isolates lesson text by target and rejects corrupt or oversized cache records', () => {
  writeTextCache('first', { text: 'Received words', previousText: null, status: 'partial' })
  expect(readTextCache('first').value?.text).toBe('Received words')
  expect(readTextCache('second').value).toBeNull()
  sessionStorage.setItem(cacheKey('first'), '{invalid')
  expect(readTextCache('first').error).toMatch(/could not be restored/)
  expect(() =>
    writeTextCache('first', { text: 'x'.repeat(250000), previousText: null, status: 'partial' }),
  ).toThrow()
})
it('preserves sequential draft edits and restores only the original target', () => {
  const first = renderHook(() => useLessonDraft('first'))
  act(() => {
    first.result.current.setInput('First')
    first.result.current.setInput((text) => text + ' second')
  })
  expect(first.result.current.input).toBe('First second')
  first.unmount()
  expect(renderHook(() => useLessonDraft('second')).result.current.input).toBe('')
  expect(renderHook(() => useLessonDraft('first')).result.current.input).toBe('First second')
})
it('keeps the active draft when browser writes fail and reports unavailable restoration', () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('denied')
  })
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('denied')
  })
  expect(readTextCache('first').error).toMatch(/could not be restored/)
  const { result } = renderHook(() => useLessonDraft('first'))
  expect(result.current.error).toMatch(/could not be restored/)
  act(() => result.current.setInput('Keep my reasoning'))
  expect(result.current.input).toBe('Keep my reasoning')
  expect(result.current.error).toMatch(/could not be saved for reload/)
})

it('keeps legacy complete text without inventing a completed reply', () => {
  writeTextCache('legacy', { text: 'Old reply', previousText: null, status: 'complete' })
  expect(readTextCache('legacy')).toEqual({
    value: { text: 'Old reply', previousText: null, status: 'complete' },
    error: '',
  })
})

it.each([
  { outcome: 'partial' },
  { turn_id: '' },
  { text: 'Different reply' },
  { sources: [{ citation: 42 }] },
  { flagged: 'wrong type' },
  { memory_answers: [42] },
])('retains text when completion metadata is invalid: %j', (patch) => {
  const done = {
    turn_id: 't',
    model_call_id: null,
    tutor_trace_id: 'trace',
    registry_id: null,
    route: null,
    outcome: 'ok',
    sentences: 1,
    representation: null,
    sources: [],
    flagged: [],
    dropped: [],
    latency_ms: 1,
    text: 'Received text',
    ...patch,
  }
  sessionStorage.setItem(
    cacheKey('invalid'),
    JSON.stringify({ text: 'Received text', previousText: null, status: 'complete', done }),
  )
  const restored = readTextCache('invalid')
  expect(restored.value?.text).toBe('Received text')
  expect(restored.value?.done).toBeNull()
  expect(restored.error).toMatch(/details could not be restored/)
})

it('stores a large completed reply once, preserving the existing text capacity', () => {
  const text = 'a'.repeat(160000)
  const done = {
    turn_id: 't',
    model_call_id: null,
    tutor_trace_id: 'trace',
    registry_id: null,
    route: null,
    outcome: 'ok',
    sentences: 1,
    representation: null,
    sources: [],
    flagged: [],
    dropped: [],
    latency_ms: 1,
    text,
  }
  writeTextCache('large', { text, previousText: null, status: 'complete', done })
  expect(sessionStorage.getItem(cacheKey('large'))!.length).toBeLessThan(161000)
  expect(readTextCache('large').value?.done).toEqual(done)
})

it.each([null, { version: 2, reply: {} }, { version: 1, reply: { text: 'conflicting text' } }])(
  'rejects unknown or conflicting completion envelopes while retaining text (%j)',
  (completion) => {
    sessionStorage.setItem(
      cacheKey('envelope'),
      JSON.stringify({ text: 'Keep me', previousText: null, status: 'complete', completion }),
    )
    const recovered = readTextCache('envelope')
    expect(recovered.value?.text).toBe('Keep me')
    expect(recovered.value?.done).toBeNull()
    expect(recovered.error).toMatch(/details could not be restored/)
  },
)

it('preserves the latest bounded text if completion sources exceed the cache limit', () => {
  writeTextCache('overflow', { text: 'Earlier tokens', previousText: null, status: 'streaming' })
  const text = 'Latest final reply'
  const done = {
    turn_id: 't',
    model_call_id: null,
    tutor_trace_id: 'trace',
    registry_id: null,
    route: null,
    outcome: 'ok',
    sentences: 1,
    representation: null,
    sources: [{ chunk_id: 's', citation: 'x'.repeat(250000), trust_tier: 1, score: 1, cited: true }],
    flagged: [],
    dropped: [],
    latency_ms: 1,
    text,
  }
  expect(writeTextCache('overflow', { text, previousText: null, status: 'complete', done })).toMatch(
    /details are too large/,
  )
  expect(readTextCache('overflow').value).toEqual({ text, previousText: null, status: 'complete' })
})
