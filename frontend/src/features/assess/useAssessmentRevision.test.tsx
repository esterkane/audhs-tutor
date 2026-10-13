import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { useAssessmentRevision } from './useAssessmentRevision'

const source = { attempt_id: 'original', root_attempt_id: 'original', answer: 'Submitted answer', item: { id: 'question' } }
function mount(attemptId = 'original') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return renderHook(({ id }) => useAssessmentRevision('block', 'session', id, true), {
    initialProps: { id: attemptId },
    wrapper: ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>,
  })
}
function respond() {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(source), { status: 200 })))
}
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  sessionStorage.clear()
})

it('restores an edited draft and retrieves the original only by GET', async () => {
  respond()
  const first = mount()
  act(() => first.result.current.start())
  await waitFor(() => expect(first.result.current.answer).toBe('Submitted answer'))
  act(() => first.result.current.edit('Revised locally'))
  first.unmount()
  const restored = mount()
  await waitFor(() => expect(restored.result.current.data).not.toBeNull())
  expect(restored.result.current.answer).toBe('Revised locally')
  for (const [, init] of vi.mocked(fetch).mock.calls) expect(init?.method).toBeUndefined()
})

it('keeps an in-memory draft and reports failed storage writes', async () => {
  respond()
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Full') })
  const state = mount()
  act(() => state.result.current.start())
  await waitFor(() => expect(state.result.current.data).not.toBeNull())
  act(() => state.result.current.edit('Keep this work'))
  expect(state.result.current.answer).toBe('Keep this work')
  expect(state.result.current.storageError).toContain('Copy it before leaving')
})

it('does not discard a draft when cancellation cannot remove its stored copy', async () => {
  respond()
  const state = mount()
  act(() => state.result.current.start())
  await waitFor(() => expect(state.result.current.data).not.toBeNull())
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('Blocked') })
  act(() => expect(state.result.current.clear()).toBe(false))
  expect(state.result.current.editing).toBe(true)
  expect(state.result.current.storageError).toContain('could not be cleared')
  act(() => expect(state.result.current.clear(true)).toBe(true))
  expect(state.result.current.editing).toBe(false)
})

it('does not reopen editing when a cancelled source request completes late', async () => {
  let finish!: (response: Response) => void
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => { finish = resolve })))
  const state = mount()
  act(() => state.result.current.start())
  await waitFor(() => expect(fetch).toHaveBeenCalledOnce())
  act(() => state.result.current.clear())
  await act(async () => finish(new Response(JSON.stringify(source), { status: 200 })))
  expect(state.result.current.editing).toBe(false)
  expect(state.result.current.data).toBeNull()
})

it('rejects corrupt saved drafts and ignores drafts for an older checked attempt', () => {
  sessionStorage.setItem('assessment-revision:v1:block', '{broken')
  const corrupt = mount()
  expect(corrupt.result.current.editing).toBe(false)
  expect(corrupt.result.current.storageError).toContain('could not be restored')
  corrupt.unmount()
  sessionStorage.setItem('assessment-revision:v1:block', JSON.stringify({ version: 1, attemptId: 'older', answer: 'Old draft' }))
  const old = mount()
  expect(old.result.current.editing).toBe(false)
  expect(old.result.current.data).toBeNull()
})

it('retains a revision draft across source failure and an explicit retry', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(new Response('Unavailable', { status: 503 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(source), { status: 200 })))
  sessionStorage.setItem('assessment-revision:v1:block', JSON.stringify({ version: 1, attemptId: 'original', answer: 'Keep my revision' }))
  const state = mount()
  await waitFor(() => expect(state.result.current.source.isError).toBe(true))
  expect(state.result.current.answer).toBe('Keep my revision')
  expect(state.result.current.data).toBeNull()
  await act(async () => { await state.result.current.source.refetch() })
  await waitFor(() => expect(state.result.current.data).not.toBeNull())
  expect(state.result.current.answer).toBe('Keep my revision')
})


it('keeps provisional lineage separate and restores its edited draft', async () => {
  const advisory = { feedback_id: 'advisory', root_feedback_id: 'root-advisory', answer: 'Original', item: { id: 'question' } }
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(advisory), { status: 200 })))
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>
  const first = renderHook(() => useAssessmentRevision('advisory-block', 'session', 'advisory', true, 'provisional'), { wrapper })
  act(() => first.result.current.start())
  await waitFor(() => expect(first.result.current.answer).toBe('Original'))
  expect(first.result.current.revisionRequest).toEqual({ revision_of_feedback_id: 'root-advisory' })
  expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/feedback/advisory/revision')
  act(() => first.result.current.edit('Revised'))
  first.unmount()
  const restored = renderHook(() => useAssessmentRevision('advisory-block', 'session', 'advisory', true, 'provisional'), { wrapper })
  expect(restored.result.current.answer).toBe('Revised')
  restored.unmount()
  const otherKind = renderHook(() => useAssessmentRevision('advisory-block', 'session', 'advisory', true, 'assessed'), { wrapper })
  expect(otherKind.result.current.editing).toBe(false)
})
