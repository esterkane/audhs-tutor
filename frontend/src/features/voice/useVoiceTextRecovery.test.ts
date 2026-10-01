import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { useVoiceTextRecovery, voiceTextKey } from './useVoiceTextRecovery'
beforeEach(() => sessionStorage.clear())
afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})
it('flushes on pagehide and refuses oversized or corrupt restored data', () => {
  const first = renderHook(() => useVoiceTextRecovery('one'))
  act(() =>
    first.result.current.save({
      draft: 'my draft',
      transcript: 'question',
      answer: 'received',
      interrupted: true,
    }),
  )
  act(() => window.dispatchEvent(new Event('pagehide')))
  expect(JSON.parse(sessionStorage.getItem(voiceTextKey('one'))!).draft).toBe('my draft')
  sessionStorage.setItem(voiceTextKey('broken'), '{broken')
  expect(renderHook(() => useVoiceTextRecovery('broken')).result.current.error).toMatch(
    /could not be restored/,
  )
  sessionStorage.setItem(voiceTextKey('large'), 'x'.repeat(250001))
  expect(renderHook(() => useVoiceTextRecovery('large')).result.current.error).toMatch(
    /could not be restored/,
  )
})
it('reports denied persistence and preserves text in its pending snapshot', () => {
  vi.useFakeTimers()
  const denied = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('denied')
  })
  const view = renderHook(() => useVoiceTextRecovery('denied'))
  act(() =>
    view.result.current.save({ draft: 'my reasoning', transcript: '', answer: '', interrupted: false }),
  )
  act(() => vi.advanceTimersByTime(250))
  expect(view.result.current.error).toMatch(/could not be saved for reload/)
  denied.mockRestore()
  act(() => window.dispatchEvent(new Event('pagehide')))
  expect(JSON.parse(sessionStorage.getItem(voiceTextKey('denied'))!).draft).toBe('my reasoning')
})
