import { afterEach, expect, it, vi } from 'vitest'
import { useBrowseAreas } from './browseState'
afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear(); useBrowseAreas.setState({ current: '', recent: [], storageError: false }) })
it('retains five recent identities without duplicate visits', () => {
  for (const id of ['a', 'b', 'c', 'd', 'e', 'f', 'b']) useBrowseAreas.getState().remember(id)
  expect(useBrowseAreas.getState().recent).toEqual(['b', 'f', 'e', 'd', 'c'])
  expect(JSON.parse(sessionStorage.getItem('audhs-browse-areas:v1')!).current).toBe('b')
})
it('keeps browsing usable when tab storage fails', () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Denied') })
  useBrowseAreas.getState().remember('a')
  expect(useBrowseAreas.getState().current).toBe('a')
  expect(useBrowseAreas.getState().storageError).toBe(true)
})
