import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { draftRecoveryKey, useDraftRecovery } from './useDraftRecovery'

const baseline = '{"goal":"original"}'
beforeEach(() => sessionStorage.clear())
afterEach(() => vi.restoreAllMocks())

it('keeps partial text, revision and baseline across remount, isolated by draft identity', () => {
  const first = renderHook(() => useDraftRecovery('one', 1, baseline))
  act(() => first.result.current.edit('{ unfinished JSON'))
  first.unmount()
  const restored = renderHook(() => useDraftRecovery('one', 2, '{"goal":"newer"}'))
  expect(restored.result.current.text).toBe('{ unfinished JSON')
  expect(restored.result.current.baseText).toBe(baseline)
  expect(restored.result.current.baseVersion).toBe(1)
  expect(restored.result.current.restored).toBe(true)
  expect(renderHook(() => useDraftRecovery('two', 1, baseline)).result.current.text).toBe(baseline)
})

it('tracks pristine server updates and clears only the selected draft on explicit reset', () => {
  const hook = renderHook(({ version, text }) => useDraftRecovery('one', version, text), { initialProps: { version: 1, text: baseline } })
  hook.rerender({ version: 2, text: '{"goal":"newer"}' })
  expect(hook.result.current.text).toBe('{"goal":"newer"}')
  act(() => hook.result.current.edit('new local text'))
  sessionStorage.setItem(draftRecoveryKey('other'), 'keep')
  act(() => hook.result.current.reset('{"goal":"saved"}', 3))
  expect(hook.result.current.dirty).toBe(false)
  expect(sessionStorage.getItem(draftRecoveryKey('one'))).toBeNull()
  expect(sessionStorage.getItem(draftRecoveryKey('other'))).toBe('keep')
})

it('preserves current text on quota failure and retries only through an explicit action', () => {
  const hook = renderHook(() => useDraftRecovery('one', 1, baseline))
  const write = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('quota') })
  act(() => hook.result.current.edit('latest text'))
  expect(hook.result.current.text).toBe('latest text')
  expect(hook.result.current.error).toContain('could not be updated')
  write.mockRestore()
  act(() => hook.result.current.saveRecovery())
  expect(hook.result.current.error).toBe('')
  hook.unmount()
  expect(renderHook(() => useDraftRecovery('one', 1, baseline)).result.current.text).toBe('latest text')
})

it.each(['not JSON', JSON.stringify({ version: 2 }), JSON.stringify({ version: 1, draftId: 'wrong', baseVersion: 1, baseText: baseline, text: 'private', savedAt: new Date().toISOString() })])('does not silently overwrite unreadable recovery: %s', (raw) => {
  sessionStorage.setItem(draftRecoveryKey('one'), raw)
  const hook = renderHook(() => useDraftRecovery('one', 1, baseline))
  expect(hook.result.current.error).toContain('could not be read')
  act(() => hook.result.current.edit('new explicit work'))
  expect(sessionStorage.getItem(draftRecoveryKey('one'))).toBe(raw)
  act(() => hook.result.current.saveRecovery())
  expect(JSON.parse(sessionStorage.getItem(draftRecoveryKey('one'))!).text).toBe('new explicit work')
})

it('reports failed removal after save without undoing the acknowledged saved text', () => {
  const hook = renderHook(() => useDraftRecovery('one', 1, baseline))
  act(() => hook.result.current.edit('old edit'))
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('denied') })
  act(() => hook.result.current.reset('acknowledged saved content', 2))
  expect(hook.result.current.text).toBe('acknowledged saved content')
  expect(hook.result.current.dirty).toBe(false)
  expect(hook.result.current.error).toContain('could not be updated')
  hook.unmount()
  const restored = renderHook(() => useDraftRecovery('one', 2, 'acknowledged saved content'))
  expect(restored.result.current.baseVersion).toBe(1)
  expect(restored.result.current.restored).toBe(true)
  // Old text stays version-bound; the editor must require explicit conflict resolution.
})
