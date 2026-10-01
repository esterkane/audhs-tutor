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
