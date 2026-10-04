import { afterEach, expect, it, vi } from 'vitest'
import { cleanContext, restoreHistory, useRecentContexts } from './history'
const context = (id: string) => ({ version: 1 as const, kind: 'source' as const, chunk_id: id, label: id })
afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear(); useRecentContexts.setState({ items: [], storageError: false }) })
it('bounds visits, deduplicates identity and refreshes a changed label', () => {
  for (let i = 0; i < 20; i++) useRecentContexts.getState().remember(context(String(i)))
  useRecentContexts.getState().remember({ ...context('15'), label: 'New label' })
  expect(useRecentContexts.getState().items).toHaveLength(12)
  expect(useRecentContexts.getState().items[0].label).toBe('New label')
  expect(restoreHistory().items).toEqual(useRecentContexts.getState().items)
})
it('does not persist arbitrary source content or accept invalid identities', () => {
  expect(cleanContext({ ...context('ok'), text: 'private content', url: 'https://example.com' })).toEqual(context('ok'))
  useRecentContexts.getState().remember(context('../bad'))
  expect(useRecentContexts.getState().items).toEqual([])
  sessionStorage.setItem('audhs-recent-contexts:v1', '{bad')
  expect(restoreHistory()).toEqual({ items: [], storageError: true })
})
it('retains current navigation in memory when storage fails, without promising persistence', () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('denied') })
  useRecentContexts.getState().remember(context('one'))
  expect(useRecentContexts.getState().items).toEqual([context('one')])
  expect(useRecentContexts.getState().storageError).toBe(true)
})
it('clear removes history and reports failure if old persisted data cannot be removed', () => {
  useRecentContexts.getState().remember(context('one'))
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('denied') })
  useRecentContexts.getState().clear()
  expect(useRecentContexts.getState().items).toEqual([])
  expect(useRecentContexts.getState().storageError).toBe(true)
  vi.restoreAllMocks()
  useRecentContexts.getState().clear()
  expect(restoreHistory().items).toEqual([])
})
