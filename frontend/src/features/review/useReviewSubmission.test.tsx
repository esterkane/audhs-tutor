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

it('archives a definitely rejected original rating across reload and never automatically resends it', async () => {
  const fetcher = vi.fn(
    async () =>
      new Response(
        JSON.stringify({ error: { code: 'review_content_changed', message: 'Card changed', details: {} } }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      ),
  )
  vi.stubGlobal('fetch', fetcher)
  const hook = setup('version-review')
  await act(async () => {
    await hook.result.current
      .mutateAsync({
        itemId: 'card',
        body: { ...body, session_id: 'version-review', content_version: 'old' },
        questionLabel: 'Original wording',
      })
      .catch(() => null)
  })
  expect(hook.result.current.recovery.stale).toBe(true)
  act(() => hook.result.current.recovery.clear())
  expect(hook.result.current.recovery.pending).toBeNull()
  hook.unmount()
  const restored = setup('version-review')
  expect(restored.result.current.recovery.previousRating?.question).toBe('Original wording')
  expect(restored.result.current.recovery.previousRating?.body.content_version).toBe('old')
  act(() => restored.result.current.recovery.dismissPrevious())
  expect(restored.result.current.recovery.previousRating).toBeNull()
  expect(fetcher).toHaveBeenCalledTimes(1)
})

it('keeps rejected pending identity if archiving fails', () => {
  const session = 'archive-failure'
  sessionStorage.setItem(
    reviewRecoveryKey(session),
    JSON.stringify({
      version: 1,
      id: crypto.randomUUID(),
      itemId: 'card',
      question: 'Original',
      body: { ...body, session_id: session },
      rejectedContent: true,
    }),
  )
  const hook = setup(session)
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('full')
  })
  act(() => hook.result.current.recovery.clear())
  expect(hook.result.current.recovery.pending?.question).toBe('Original')
  expect(hook.result.current.recovery.error).toContain('could not be cleared')
})

it('does not treat unknown conflicts as a definite content rejection', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async () =>
        new Response(JSON.stringify({ error: { code: 'request_in_progress', message: 'Unknown state' } }), {
          status: 409,
          headers: { 'Content-Type': 'application/json' },
        }),
    ),
  )
  const hook = setup('unknown-conflict')
  await act(async () => {
    await hook.result.current
      .mutateAsync({ itemId: 'card', body: { ...body, session_id: 'unknown-conflict' } })
      .catch(() => null)
  })
  expect(hook.result.current.recovery.stale).toBe(false)
  expect(hook.result.current.recovery.pending).not.toBeNull()
})

it('retains two rejected snapshots until each is explicitly dismissed', () => {
  const session = 'archive-two'
  const first = {
    version: 1,
    id: crypto.randomUUID(),
    itemId: 'one',
    question: 'First',
    body: { ...body, session_id: session },
    rejectedContent: true,
  }
  sessionStorage.setItem(reviewRecoveryKey(session), JSON.stringify(first))
  const hook = setup(session)
  act(() => hook.result.current.recovery.clear())
  const second = { ...first, id: crypto.randomUUID(), question: 'Second' }
  sessionStorage.setItem(reviewRecoveryKey(session), JSON.stringify(second))
  act(() => hook.result.current.recovery.reload())
  act(() => hook.result.current.recovery.clear())
  hook.unmount()
  const restored = setup(session)
  expect(restored.result.current.recovery.archivedRatings.map((x) => x.question)).toEqual(['First', 'Second'])
  act(() => restored.result.current.recovery.dismissPrevious(first.id))
  expect(restored.result.current.recovery.archivedRatings.map((x) => x.question)).toEqual(['Second'])
})

it('archives in explicit page memory when browser storage is denied', () => {
  const session = 'archive-memory'
  sessionStorage.setItem(
    reviewRecoveryKey(session),
    JSON.stringify({
      version: 1,
      id: crypto.randomUUID(),
      itemId: 'one',
      question: 'Original',
      body: { ...body, session_id: session },
      rejectedContent: true,
    }),
  )
  const hook = setup(session)
  act(() => hook.result.current.recovery.continueInMemory())
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('denied')
  })
  act(() => hook.result.current.recovery.clear())
  expect(hook.result.current.recovery.pending).toBeNull()
  expect(hook.result.current.recovery.archivedRatings[0].question).toBe('Original')
})

it('refuses to overwrite a damaged archive and retains pending', () => {
  const session = 'damaged-archive'
  sessionStorage.setItem('review-previous-rating:v1:' + session, '{broken')
  sessionStorage.setItem(
    reviewRecoveryKey(session),
    JSON.stringify({
      version: 1,
      id: crypto.randomUUID(),
      itemId: 'one',
      question: 'New',
      body: { ...body, session_id: session },
      rejectedContent: true,
    }),
  )
  const hook = setup(session)
  act(() => hook.result.current.recovery.clear())
  expect(hook.result.current.recovery.pending?.question).toBe('New')
  expect(sessionStorage.getItem('review-previous-rating:v1:' + session)).toBe('{broken')
})

it('preserves visible earlier archives when explicitly switching to page memory', () => {
  const session = 'fallback-preserves-archive'
  const first = {
    version: 1,
    id: crypto.randomUUID(),
    itemId: 'one',
    question: 'Earlier',
    body: { ...body, session_id: session },
    rejectedContent: true,
  }
  sessionStorage.setItem('review-previous-rating:v1:' + session, JSON.stringify([first]))
  sessionStorage.setItem(
    reviewRecoveryKey(session),
    JSON.stringify({ ...first, id: crypto.randomUUID(), question: 'New' }),
  )
  const hook = setup(session)
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('denied')
  })
  act(() => hook.result.current.recovery.continueInMemory())
  act(() => hook.result.current.recovery.clear())
  expect(hook.result.current.recovery.archivedRatings.map((x) => x.question)).toEqual(['Earlier', 'New'])
})
