import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { TRANSITION_WAIT_NOTICE_MS, useBlockTransition } from './api'
import type { SessionOut } from '../../lib/api'

function setup() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: 3 } } })
  return renderHook(() => useBlockTransition('session'), {
    wrapper: ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>,
  })
}
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })

it.each(['before', 'during'])('a read started %s the transition cannot restore the old block', async timing => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const old = { id: 'session', state: { phase: 'review', block_id: 'session:1' } } as SessionOut
  const keys = [['session', 'session'], ['session-current']]
  keys.forEach(key => client.setQueryData(key, old))
  const releases: (() => void)[] = []
  let reads: Promise<unknown>[] = []
  function staleReads() {
    reads = keys.map(queryKey => client.fetchQuery({ queryKey, queryFn: () => new Promise<SessionOut>(resolve => {
      releases.push(() => resolve(old))
    }) }).catch(() => undefined))
  }
  let confirm!: () => void
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => {
    confirm = () => resolve(new Response(JSON.stringify({ phase: 'teach', block_id: 'session:2', allowed: true }), { status: 200 }))
  })))
  const view = renderHook(() => useBlockTransition('session'), { wrapper: ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider> })
  if (timing === 'before') staleReads()
  let transition!: ReturnType<typeof view.result.current.next>
  await act(async () => { transition = view.result.current.next({ from_index: 1 }) })
  await waitFor(() => expect(confirm).toBeTypeOf('function'))
  if (timing === 'during') staleReads()
  await act(async () => { confirm(); await transition })
  releases.forEach(release => release())
  await Promise.all(reads)
  for (const key of keys) expect(client.getQueryData<SessionOut>(key)?.state.phase).toBe('teach')
  view.unmount()
  client.clear()
})

it('announces only prolonged waits, shares double clicks, and resets after settlement', async () => {
  vi.useFakeTimers()
  let complete!: (response: Response) => void
  const fetcher = vi.fn(() => new Promise<Response>((resolve) => { complete = resolve }))
  vi.stubGlobal('fetch', fetcher)
  const view = setup()
  let first!: ReturnType<typeof view.result.current.next>
  let second!: ReturnType<typeof view.result.current.next>
  await act(async () => {
    first = view.result.current.next({ from_index: 0 })
    second = view.result.current.next({ from_index: 0 })
  })
  expect(second).toBe(first)
  await act(async () => { await vi.advanceTimersByTimeAsync(TRANSITION_WAIT_NOTICE_MS - 1) })
  expect(view.result.current.waitingLong).toBe(false)
  await act(async () => { await vi.advanceTimersByTimeAsync(1) })
  expect(view.result.current.waitingLong).toBe(true)
  expect(view.result.current.pending).toBe(true)
  expect(fetcher).toHaveBeenCalledTimes(1)
  await act(async () => {
    complete(new Response(JSON.stringify({ allowed: true, block_index: 1, phase: 'review' }), { status: 200 }))
    await first
    await vi.advanceTimersByTimeAsync(0)
  })
  expect(view.result.current.pending).toBe(false)
  expect(view.result.current.waitingLong).toBe(false)
  view.unmount()
})

it('does not retry a failed transition even when global mutation retries are enabled', async () => {
  vi.useFakeTimers()
  const fetcher = vi.fn(async () => { throw new Error('Delivery lost') })
  vi.stubGlobal('fetch', fetcher)
  const view = setup()
  await act(async () => {
    await expect(view.result.current.extend(0)).rejects.toThrow('Delivery lost')
    await vi.advanceTimersByTimeAsync(TRANSITION_WAIT_NOTICE_MS * 2)
  })
  expect(fetcher).toHaveBeenCalledTimes(1)
  expect(view.result.current.waitingLong).toBe(false)
  expect(view.result.current.error?.message).toBe('Delivery lost')
  view.unmount()
})
