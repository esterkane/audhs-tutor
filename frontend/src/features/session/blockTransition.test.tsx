import { act, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { TRANSITION_WAIT_NOTICE_MS, useBlockTransition } from './api'

function setup() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: 3 } } })
  return renderHook(() => useBlockTransition('session'), {
    wrapper: ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>,
  })
}
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })

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
