import { act, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { jsonResponse } from '../../test/utils'
import { reviewRecoveryKey, useReviewSubmission } from './useReviewSubmission'

const body = { session_id: 'review-session', rating: 3, hint_count: 1, confidence_pre: 2, latency_ms: 100 }
const reply = {
  item_id: 'card',
  due: '2030-01-01',
  state: 'review',
  stability: 3,
  predicted_retrievability: 0.7,
}
function setup(session = body.session_id) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return renderHook(({ session }) => useReviewSubmission(session), {
    initialProps: { session },
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  })
}
beforeEach(() => sessionStorage.clear())
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

it('persists before sending, blocks changed retries and recovers after remount without another POST', async () => {
  const fetcher = vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.method === 'POST') {
      const saved = JSON.parse(sessionStorage.getItem(reviewRecoveryKey(body.session_id))!)
      expect(saved.body).toEqual(body)
      expect((init.headers as Record<string, string>)['Idempotency-Key']).toBe(saved.id)
      throw new Error('Lost response')
    }
    return jsonResponse({ status: 'completed', result: reply })
  })
  vi.stubGlobal('fetch', fetcher)
  const hook = setup()
  await act(async () => {
    await expect(
      hook.result.current.mutateAsync({ itemId: 'card', body, questionLabel: 'Original card' }),
    ).rejects.toThrow('Lost response')
  })
  await act(async () => {
    await expect(
      hook.result.current.mutateAsync({ itemId: 'card', body: { ...body, rating: 4 } }),
    ).rejects.toThrow('earlier submission')
  })
  hook.unmount()
  const restored = setup()
  expect(restored.result.current.recovery.pending?.question).toBe('Original card')
  await act(async () => {
    await restored.result.current.recovery.check()
  })
  expect(restored.result.current.recovery.lookup?.result).toEqual(reply)
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1)
})

it('only resends explicitly after not_found using the exact body and identity', async () => {
  const id = crypto.randomUUID()
  sessionStorage.setItem(
    reviewRecoveryKey(body.session_id),
    JSON.stringify({ version: 1, id, itemId: 'card', body, question: 'Original' }),
  )
  const fetcher = vi.fn(async (_url: string, init?: RequestInit) =>
    jsonResponse(init?.method === 'POST' ? reply : { status: 'not_found' }),
  )
  vi.stubGlobal('fetch', fetcher)
  const hook = setup()
  await act(async () => {
    await hook.result.current.recovery.resend()
  })
  expect(fetcher).not.toHaveBeenCalled()
  await act(async () => {
    await hook.result.current.recovery.check()
  })
  await act(async () => {
    await hook.result.current.recovery.resend()
  })
  expect(fetcher.mock.calls[1][1]?.body).toBe(JSON.stringify(body))
  expect((fetcher.mock.calls[1][1]?.headers as Record<string, string>)['Idempotency-Key']).toBe(id)
})

for (const failure of ['getItem', 'setItem', 'removeItem', 'malformed'] as const) {
  it(`handles ${failure} failure with explicit memory fallback`, async () => {
    const session = `review-${failure}`
    if (failure === 'malformed') sessionStorage.setItem(reviewRecoveryKey(session), '{broken')
    else
      vi.spyOn(Storage.prototype, failure).mockImplementation(() => {
        throw new Error('blocked')
      })
    const fetcher = vi.fn(async () => jsonResponse(reply))
    vi.stubGlobal('fetch', fetcher)
    const hook = setup(session)
    await act(async () => {
      await hook.result.current
        .mutateAsync({ itemId: 'card', body: { ...body, session_id: session } })
        .catch(() => null)
    })
    if (failure === 'removeItem') act(() => hook.result.current.recovery.clear())
    expect(hook.result.current.recovery.error).toBeTruthy()
    const id = hook.result.current.recovery.pending?.id
    act(() => hook.result.current.recovery.continueInMemory())
    expect(hook.result.current.recovery.memoryOnly).toBe(true)
    if (failure === 'removeItem') expect(hook.result.current.recovery.pending?.id).toBe(id)
    else {
      expect(fetcher).not.toHaveBeenCalled()
      await act(async () => {
        await hook.result.current.mutateAsync({ itemId: 'card', body: { ...body, session_id: session } })
      })
      expect(fetcher).toHaveBeenCalledTimes(1)
    }
  })
}

it('rejects a late response after changing sessions and leaves the original intent recoverable', async () => {
  let release!: (response: Response) => void
  vi.stubGlobal(
    'fetch',
    vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          release = resolve
        }),
    ),
  )
  const hook = setup()
  let sent!: Promise<unknown>
  await act(async () => {
    sent = hook.result.current.mutateAsync({ itemId: 'card', body }).catch((error) => error)
  })
  hook.rerender({ session: 'other-session' })
  await act(async () => {
    release(jsonResponse(reply))
    await sent
  })
  expect(await sent).toBeInstanceOf(Error)
  expect(hook.result.current.recovery.pending).toBeNull()
  expect(sessionStorage.getItem(reviewRecoveryKey(body.session_id))).not.toBeNull()
})

it('retains a delivered intent until checkpoint acknowledgement and refuses stale acknowledgement', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse(reply)),
  )
  const hook = setup()
  let requestId = ''
  await act(async () => {
    requestId = (await hook.result.current.mutateAsync({ itemId: 'card', body })).requestId
  })
  expect(hook.result.current.recovery.lookup?.status).toBe('completed')
  expect(JSON.parse(sessionStorage.getItem(reviewRecoveryKey(body.session_id))!).id).toBe(requestId)
  const replacement = { ...hook.result.current.recovery.pending!, id: crypto.randomUUID() }
  sessionStorage.setItem(reviewRecoveryKey(body.session_id), JSON.stringify(replacement))
  act(() => hook.result.current.recovery.clear(requestId))
  expect(hook.result.current.recovery.pending?.id).toBe(replacement.id)
  expect(sessionStorage.getItem(reviewRecoveryKey(body.session_id))).not.toBeNull()
})

it('bounds an unresponsive request and preserves its identity without automatic retry', async () => {
  vi.useFakeTimers()
  const fetcher = vi.fn(() => new Promise<Response>(() => {}))
  vi.stubGlobal('fetch', fetcher)
  const hook = setup()
  let result!: Promise<unknown>
  await act(async () => {
    result = hook.result.current.mutateAsync({ itemId: 'card', body }).catch((error) => error)
  })
  await act(async () => {
    await vi.advanceTimersByTimeAsync(15000)
  })
  expect(await result).toBeInstanceOf(Error)
  expect(hook.result.current.recovery.pending?.body).toEqual(body)
  expect(fetcher).toHaveBeenCalledTimes(1)
  expect(hook.result.current.recovery.storageError).toBe('')
})
