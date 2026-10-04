import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { READ_TIMEOUT_MS } from '../../lib/boundedRead'
import { jsonResponse } from '../../test/utils'
import { usePreferences, useSetPreference } from './api'

const clients: QueryClient[] = []
function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  clients.push(client)
  return renderHook(() => ({ read: usePreferences(), save: useSetPreference() }), {
    wrapper: ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>,
  })
}
afterEach(() => {
  cleanup()
  clients.splice(0).forEach(client => client.clear())
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

it('bounds a hung preference read without an automatic retry loop', async () => {
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

it('a late refresh cannot overwrite a successful preference save', async () => {
  let reads = 0
  let finishRead!: (response: Response) => void
  let pendingSignal: AbortSignal | undefined
  vi.stubGlobal('fetch', vi.fn((_url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') return Promise.resolve(jsonResponse({ values: { 'ui.font_scale': 'large' }, specs: [] }))
    if (++reads === 1) return Promise.resolve(jsonResponse({ values: { 'ui.font_scale': 'normal' }, specs: [] }))
    pendingSignal = init?.signal as AbortSignal
    return new Promise<Response>(resolve => { finishRead = resolve })
  }))
  const { result } = setup()
  await waitFor(() => expect(result.current.read.isSuccess).toBe(true))
  act(() => { void result.current.read.refetch() })
  await waitFor(() => expect(reads).toBe(2))
  await act(async () => { await result.current.save.mutateAsync({ key: 'ui.font_scale', value: 'large' }) })
  expect(pendingSignal?.aborted).toBe(true)
  await act(async () => {
    finishRead(jsonResponse({ values: { 'ui.font_scale': 'normal' }, specs: [] }))
    await new Promise(resolve => setTimeout(resolve, 0))
  })
  expect(result.current.read.data?.values['ui.font_scale']).toBe('large')
})
