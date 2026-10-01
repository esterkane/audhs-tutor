import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { TutorRequest } from './api'
import { useRequestRecovery } from './useRequestRecovery'

const body: TutorRequest = {
  session_id: 's',
  exercise: 'Groups',
  code: 'x=1',
  question: 'Why?',
  prefer_saved: false,
  questioning_style: 'explicit',
  intent: 'chat',
  output: '',
  output_stale: false,
}
const view = { snapshot: 'original', submitted: 'Why?', display: 'Why?', mode: 'explicit' as const }
afterEach(() => {
  vi.restoreAllMocks()
  sessionStorage.clear()
})

it('freezes payload, retains identity after remount and requires explicit discard for changed work', () => {
  const first = renderHook(() => useRequestRecovery('test'))
  let key = ''
  const source = { ...body }
  act(() => {
    key = first.result.current.prepare(source, view).key
  })
  source.code = 'changed'
  expect(first.result.current.pending?.body.code).toBe('x=1')
  first.unmount()
  const second = renderHook(() => useRequestRecovery('test'))
  expect(second.result.current.pending?.key).toBe(key)
  act(() => {
    expect(second.result.current.prepare(body, view).key).toBe(key)
  })
  expect(() => second.result.current.prepare(source, view)).toThrow(/earlier request/)
  act(() => second.result.current.accept('stale-key'))
  expect(second.result.current.pending?.key).toBe(key)
  act(() => second.result.current.accept(key))
  expect(second.result.current.pending).toBeNull()
  act(() => {
    expect(second.result.current.prepare(source, view).key).not.toBe(key)
  })
})

it('retains in-memory identity if storage is unavailable and discloses reload limit', () => {
  const hook = renderHook(() => useRequestRecovery('test'))
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('denied')
  })
  let key = ''
  act(() => {
    key = hook.result.current.prepare(body, view).key
  })
  expect(hook.result.current.error).toMatch(/reload is unavailable/)
  act(() => {
    expect(hook.result.current.prepare(body, view).key).toBe(key)
  })
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
    throw new Error('denied')
  })
  act(() => hook.result.current.discard())
  expect(hook.result.current.pending?.key).toBe(key)
})

it('blocks unreadable persisted identities rather than silently generating again', () => {
  sessionStorage.setItem('tutor-request:v1:test', 'broken')
  const hook = renderHook(() => useRequestRecovery('test'))
  expect(hook.result.current.needsDiscard).toBe(true)
  expect(() => hook.result.current.prepare(body, view)).toThrow(/unreadable/)
  act(() => hook.result.current.discard())
  act(() => hook.result.current.prepare(body, view))
  expect(hook.result.current.pending?.body).toEqual(body)
})

it('offers explicitly chosen in-memory tutoring when all storage access is denied', () => {
  for (const method of ['getItem', 'setItem', 'removeItem'] as const)
    vi.spyOn(Storage.prototype, method).mockImplementation(() => {
      throw new Error('denied')
    })
  const hook = renderHook(() => useRequestRecovery('denied'))
  expect(hook.result.current.canUseMemoryOnly).toBe(true)
  expect(() => hook.result.current.prepare(body, view)).toThrow()
  act(() => hook.result.current.continueInMemory())
  let key = ''
  act(() => {
    key = hook.result.current.prepare(body, view).key
  })
  expect(hook.result.current.error).toMatch(/while this page stays open/)
  act(() => expect(hook.result.current.prepare(body, view).key).toBe(key))
  act(() => hook.result.current.accept(key))
  expect(hook.result.current.pending).toBeNull()
  act(() => expect(hook.result.current.prepare(body, view).key).not.toBe(key))
})
