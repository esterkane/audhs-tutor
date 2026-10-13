import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { recapDraftKey, useRecapDraft } from './useRecapDraft'
beforeEach(() => sessionStorage.clear())
afterEach(() => vi.restoreAllMocks())
it('restores all fields only for the same session and clears explicitly', () => {
  const a = renderHook(() => useRecapDraft('a'))
  act(() => a.result.current.edit({ notes: 'Compare examples', energyAfter: 2, recall: 4 }))
  a.unmount()
  const b = renderHook(({ id }) => useRecapDraft(id), { initialProps: { id: 'b' } })
  expect(b.result.current.notes).toBe('')
  b.rerender({ id: 'a' })
  expect(b.result.current).toMatchObject({ notes: 'Compare examples', energyAfter: 2, recall: 4 })
  act(() => b.result.current.clear())
  expect(sessionStorage.getItem(recapDraftKey('a'))).toBeNull()
})
it('retains current edits and warns when writes fail', () => {
  const hook = renderHook(() => useRecapDraft('a'))
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('full') })
  act(() => hook.result.current.edit({ notes: 'Keep this' }))
  expect(hook.result.current.notes).toBe('Keep this')
  expect(hook.result.current.error).toContain('Keep a copy')
})
it('does not overwrite an unreadable earlier draft', () => {
  sessionStorage.setItem(recapDraftKey('a'), '{bad')
  const hook = renderHook(() => useRecapDraft('a'))
  act(() => hook.result.current.edit({ notes: 'New note' }))
  expect(hook.result.current.error).toContain('could not be read')
  act(() => hook.result.current.clear())
  expect(sessionStorage.getItem(recapDraftKey('a'))).toBe('{bad')
})
it('retains a draft if removing it is denied', () => {
  const hook = renderHook(() => useRecapDraft('a'))
  act(() => hook.result.current.edit({ notes: 'Original' }))
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('denied') })
  expect(() => act(() => hook.result.current.clear())).not.toThrow()
  expect(sessionStorage.getItem(recapDraftKey('a'))).toContain('Original')
})
