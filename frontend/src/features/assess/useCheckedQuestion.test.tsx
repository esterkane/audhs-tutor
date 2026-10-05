import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import type { AssessmentView, AttemptResult } from '../../lib/api'
import type { PendingAssessment } from './useAssessmentSubmission'
import { checkedQuestionKey, useCheckedQuestion } from './useCheckedQuestion'

const item: AssessmentView = {
  id: 'a',
  skill_id: 'skill',
  kind: 'mcq',
  question: 'Original question',
  content_version: 'version-1',
  confidence_required: false,
  options: ['One', 'Two'],
}
const pending: PendingAssessment = {
  version: 1,
  id: '00000000-0000-4000-8000-000000000001',
  endpoint: '/api/assess/attempt',
  question: item.question,
  body: { session_id: 's', assessment_id: 'a', content_version: 'version-1', answer: '1', hint_count: 0 },
}
const outcome = {
  assessment_id: 'a',
  attempt_id: 'attempt',
  skill_id: 'skill',
  score: 0,
  feedback: 'Original feedback',
} as AttemptResult
function mount(scope = 'block', skill = 'skill') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return renderHook(() => useCheckedQuestion(scope, 's', skill, true), {
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  })
}
function fetchOutcome(value: unknown) {
  const fetcher = vi.fn<typeof fetch>(
    async () =>
      new Response(JSON.stringify(value), { status: 200, headers: { 'Content-Type': 'application/json' } }),
  )
  vi.stubGlobal('fetch', fetcher)
  return fetcher
}
afterEach(() => {
  sessionStorage.clear()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

it('restores the exact question via a read-only original-result lookup, then explicitly clears it', async () => {
  const fetcher = fetchOutcome({ status: 'completed', result: outcome })
  const first = mount()
  act(() => first.result.current.remember(pending, outcome, item))
  first.unmount()
  const restored = mount()
  await waitFor(() => expect(restored.result.current.result.data).toEqual(outcome))
  expect(restored.result.current.saved?.item).toEqual(item)
  expect(fetcher).toHaveBeenCalledTimes(1)
  expect(String(fetcher.mock.calls[0][0])).toContain(`/api/assess/requests/${pending.id}?session_id=s`)
  expect((fetcher.mock.calls[0] as unknown as [string, RequestInit])[1]?.method).toBeUndefined()
  act(() => {
    expect(restored.result.current.clear()).toBe(true)
  })
  expect(restored.result.current.saved).toBeNull()
  expect(sessionStorage.getItem(checkedQuestionKey('block'))).toBeNull()
  restored.unmount()
})

it.each([
  { status: 'not_found' },
  { status: 'unresolved' },
  { status: 'completed', result: { ...outcome, attempt_id: 'other' } },
])('never grades or accepts an unavailable/mismatched result (%j)', async (response) => {
  const fetcher = fetchOutcome(response)
  const first = mount()
  act(() => first.result.current.remember(pending, outcome, item))
  first.unmount()
  const restored = mount()
  await waitFor(() => expect(restored.result.current.result.isError).toBe(true))
  expect(restored.result.current.result.data).toBeUndefined()
  expect(restored.result.current.saved?.item).toEqual(item)
  expect(fetcher).toHaveBeenCalledTimes(1)
  restored.unmount()
})

it('isolates activities and rejects corrupt or wrong-skill pointers without a request', () => {
  const fetcher = fetchOutcome({})
  const first = mount()
  act(() => first.result.current.remember(pending, outcome, item))
  first.unmount()
  const other = mount('other')
  expect(other.result.current.saved).toBeNull()
  other.unmount()
  const wrong = mount('block', 'other-skill')
  expect(wrong.result.current.error).toMatch(/could not be read/)
  wrong.unmount()
  sessionStorage.setItem(checkedQuestionKey('broken'), '{')
  const broken = mount('broken')
  expect(broken.result.current.error).toMatch(/could not be read/)
  expect(fetcher).not.toHaveBeenCalled()
  broken.unmount()
})

it('reports a failed return-pointer write without throwing away delivered feedback', () => {
  const view = mount()
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('full')
  })
  act(() => view.result.current.remember(pending, outcome, item))
  expect(view.result.current.error).toMatch(/Feedback is here/)
  view.unmount()
})

it('keeps the checked question if its pointer cannot be removed', async () => {
  fetchOutcome({ status: 'completed', result: outcome })
  const first = mount()
  act(() => first.result.current.remember(pending, outcome, item))
  first.unmount()
  const restored = mount()
  await waitFor(() => expect(restored.result.current.result.data).toEqual(outcome))
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('denied') })
  act(() => { expect(restored.result.current.clear()).toBe(false) })
  expect(restored.result.current.saved?.item).toEqual(item)
  expect(restored.result.current.error).toMatch(/could not be cleared/)
  restored.unmount()
})

it('does not apply a late lookup after explicitly leaving the checked question', async () => {
  let complete!: (response: Response) => void
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((resolve) => { complete = resolve })))
  const first = mount()
  act(() => first.result.current.remember(pending, outcome, item))
  first.unmount()
  const restored = mount()
  await waitFor(() => expect(restored.result.current.result.isFetching).toBe(true))
  act(() => { expect(restored.result.current.clear()).toBe(true) })
  await act(async () => { complete(new Response(JSON.stringify({ status: 'completed', result: outcome }), { status: 200 })) })
  expect(restored.result.current.saved).toBeNull()
  expect(restored.result.current.result.data).toBeUndefined()
  restored.unmount()
})
