import { afterEach, expect, it, vi } from 'vitest'
import { clearDraft, readDraft, writeDraft } from './draft'

afterEach(() => vi.restoreAllMocks())
it('keeps answers and delivered hints together when browser storage is blocked', () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('blocked')
  })
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('quota')
  })
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
    throw new Error('blocked')
  })
  expect(readDraft('blocked')).toEqual({ answer: '', hints: 0 })
  writeDraft('blocked', { answer: 'my work', hints: 2 })
  expect(readDraft('blocked')).toEqual({ answer: 'my work', hints: 2 })
  expect(() => clearDraft('blocked')).not.toThrow()
  expect(readDraft('blocked')).toEqual({ answer: '', hints: 0 })
})
