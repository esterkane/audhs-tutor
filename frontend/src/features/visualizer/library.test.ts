import { beforeEach, expect, it, vi } from 'vitest'
import { LIBRARY_KEY, LEGACY_KEY, readLibrary, restoredPreset, writeLibrary } from './library'
import { initial } from './engine'
beforeEach(() => localStorage.clear())
it('migrates a legacy preset without overwriting it and restores the selected v2 entry', () => {
  localStorage.setItem(LEGACY_KEY, JSON.stringify({ ...initial, name: 'My old work' }))
  const library = readLibrary(localStorage)
  expect(library.items[0].preset.name).toBe('My old work')
  writeLibrary(localStorage, library)
  expect(restoredPreset().name).toBe('My old work')
  expect(localStorage.getItem(LEGACY_KEY)).toContain('My old work')
})
it('rejects corrupt/unknown storage instead of silently replacing it', () => {
  localStorage.setItem(LIBRARY_KEY, '{"version":99}')
  expect(() => readLibrary(localStorage)).toThrow('Unsupported')
  expect(localStorage.getItem(LIBRARY_KEY)).toBe('{"version":99}')
})
it('propagates storage denial and does not mutate the in-memory entry', () => {
  const library = readLibrary(localStorage)
  const storage = {
    setItem: vi.fn(() => {
      throw new Error('denied')
    }),
  }
  expect(() => writeLibrary(storage, library)).toThrow('denied')
  expect(library.items).toEqual([])
})
