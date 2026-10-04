import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useThoughtDraft } from './draft'

afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear() })
const draft = { text: 'Keep context', sessionId: 'original-session', skillId: 'original-skill', unconfirmed: true }
it('restores exact context and uncertainty, then removes a confirmed draft', () => {
  const first = renderHook(useThoughtDraft)
  act(() => first.result.current.update(draft))
  first.unmount()
  const second = renderHook(useThoughtDraft)
  expect(second.result.current.draft).toEqual(draft)
  act(() => second.result.current.update({ ...draft, text: '', unconfirmed: false }))
  expect(sessionStorage.getItem('parking-draft:v1')).toBeNull()
})
it('does not overwrite or use an invalid checkpoint until explicit editing', () => {
  sessionStorage.setItem('parking-draft:v1', '{bad')
  const { result } = renderHook(useThoughtDraft)
  expect(result.current.draft.text).toBe('')
  expect(result.current.storageError).toContain('could not be restored')
  expect(sessionStorage.getItem('parking-draft:v1')).toBe('{bad')
  act(() => result.current.update(draft))
  expect(result.current.storageError).toBe('')
})
it('retains in-memory edits and discloses storage failure', () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('denied') })
  const { result } = renderHook(useThoughtDraft)
  act(() => result.current.update(draft))
  expect(result.current.draft).toEqual(draft)
  expect(result.current.storageError).toContain('Copy it before reloading')
})
it('rejects oversized restored content', () => {
  sessionStorage.setItem('parking-draft:v1', JSON.stringify({ version: 1, draft: { ...draft, text: 'a'.repeat(501) } }))
  const { result } = renderHook(useThoughtDraft)
  expect(result.current.draft.text).toBe('')
  expect(result.current.storageError).not.toBe('')
})

it('retains a save identity across reload and rejects invalid identities', () => {
  const first = renderHook(useThoughtDraft)
  act(() => first.result.current.update({ ...draft, requestKey: 'same-intent' }))
  first.unmount()
  expect(renderHook(useThoughtDraft).result.current.draft.requestKey).toBe('same-intent')
  sessionStorage.setItem('parking-draft:v1', JSON.stringify({ version: 1, draft: { ...draft, requestKey: '' } }))
  expect(renderHook(useThoughtDraft).result.current.storageError).not.toBe('')
})
