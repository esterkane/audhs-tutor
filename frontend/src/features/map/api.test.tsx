import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { READ_TIMEOUT_MS } from '../../lib/boundedRead'
import { useSkillMap } from './api'

const clients: QueryClient[] = []
function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  clients.push(client)
  return renderHook(() => ({ read: useSkillMap() }), {
    wrapper: ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>,
  })
}
afterEach(() => {
  cleanup()
  clients.splice(0).forEach(client => client.clear())
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

it('bounds a hung map read without an automatic retry loop', async () => {
  vi.useFakeTimers()
  const fetcher = vi.fn(() => new Promise<Response>(() => {}))
  vi.stubGlobal('fetch', fetcher)
  const { result } = setup()
  await act(async () => { await vi.advanceTimersByTimeAsync(READ_TIMEOUT_MS + 100) })
  expect(result.current.read.isError).toBe(true)
  expect(result.current.read.error?.message).toContain('took too long')
  await act(async () => { await vi.advanceTimersByTimeAsync(READ_TIMEOUT_MS * 2) })
  expect(fetcher).toHaveBeenCalledTimes(1)
})
