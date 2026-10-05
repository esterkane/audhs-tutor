import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
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
  return renderHook(() => ({ read: usePreferences(), save: useSetPreference(), otherSave: useSetPreference() }), {
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


it.each([
  { key: 'ui.font_scale', value: 'normal' },
  { key: 'ui.theme', value: 'dark' },
])('serializes full-snapshot saves across hook instances: $key', async second => {
  const writes: Array<{ key: string; value: unknown }> = []
  let finishFirst!: () => void
  const values: Record<string, unknown> = { 'ui.font_scale': 'normal', 'ui.theme': 'light' }
  vi.stubGlobal('fetch', vi.fn((_url: string, init?: RequestInit) => {
    if (init?.method !== 'PUT') return Promise.resolve(jsonResponse({ values, specs: [] }))
    const body = JSON.parse(String(init.body)) as { key: string; value: unknown }
    writes.push(body)
    values[body.key] = body.value
    const snapshot = { ...values }
    if (writes.length === 1) return new Promise<Response>(resolve => {
      finishFirst = () => resolve(jsonResponse({ values: snapshot, specs: [] }))
    })
    return Promise.resolve(jsonResponse({ values: snapshot, specs: [] }))
  }))
  const { result } = setup()
  await waitFor(() => expect(result.current.read.isSuccess).toBe(true))
  let first!: Promise<unknown>
  let last!: Promise<unknown>
  act(() => { first = result.current.save.mutateAsync({ key: 'ui.font_scale', value: 'large' }) })
  await waitFor(() => expect(writes).toHaveLength(1))
  try {
    await act(async () => {
      last = result.current.otherSave.mutateAsync(second)
      await new Promise(resolve => setTimeout(resolve, 0))
    })
    expect(writes).toHaveLength(1)
  } finally {
    await act(async () => { finishFirst(); await first; await last })
  }
  expect(writes).toEqual([{ key: 'ui.font_scale', value: 'large' }, second])
  await waitFor(() => expect(result.current.read.data?.values).toEqual(values))
  expect(result.current.read.data?.values[second.key]).toBe(second.value)
})

it('a failed save releases the next explicit intent without automatic retry', async () => {
  let writes = 0
  let finishFirst!: (response: Response) => void
  vi.stubGlobal('fetch', vi.fn((_url: string, init?: RequestInit) => {
    if (init?.method !== 'PUT') return Promise.resolve(jsonResponse({ values: { 'ui.font_scale': 'normal' }, specs: [] }))
    if (++writes === 1) return new Promise<Response>(resolve => { finishFirst = resolve })
    return Promise.resolve(jsonResponse({ values: { 'ui.font_scale': 'normal' }, specs: [] }))
  }))
  const { result } = setup()
  await waitFor(() => expect(result.current.read.isSuccess).toBe(true))
  let first!: Promise<boolean>
  let second!: Promise<unknown>
  act(() => {
    first = result.current.save.mutateAsync({ key: 'ui.font_scale', value: 'large' }).then(() => true, () => false)
    second = result.current.otherSave.mutateAsync({ key: 'ui.font_scale', value: 'normal' })
  })
  await waitFor(() => expect(writes).toBe(1))
  await act(async () => {
    finishFirst(jsonResponse({ error: { code: 'unavailable', message: 'Save unavailable' } }, 503))
    expect(await first).toBe(false)
    await second
  })
  expect(writes).toBe(2)
  await waitFor(() => expect(result.current.otherSave.isSuccess).toBe(true))
  expect(result.current.read.data?.values['ui.font_scale']).toBe('normal')
})


it('a refresh started during a save cannot overwrite the confirmed snapshot', async () => {
  let finishSave!: (response: Response) => void
  let finishRead!: (response: Response) => void
  let reads = 0
  vi.stubGlobal('fetch', vi.fn((_url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') return new Promise<Response>(resolve => { finishSave = resolve })
    if (++reads === 1) return Promise.resolve(jsonResponse({ values: { 'ui.font_scale': 'normal' }, specs: [] }))
    return new Promise<Response>(resolve => { finishRead = resolve })
  }))
  const { result } = setup()
  await waitFor(() => expect(result.current.read.isSuccess).toBe(true))
  let saved!: Promise<unknown>
  act(() => { saved = result.current.save.mutateAsync({ key: 'ui.font_scale', value: 'large' }) })
  await waitFor(() => expect(finishSave).toBeDefined())
  act(() => { void result.current.read.refetch() })
  await waitFor(() => expect(reads).toBe(2))
  await act(async () => {
    finishSave(jsonResponse({ values: { 'ui.font_scale': 'large' }, specs: [] }))
    await saved
  })
  await act(async () => {
    finishRead(jsonResponse({ values: { 'ui.font_scale': 'normal' }, specs: [] }))
    await new Promise(resolve => setTimeout(resolve, 0))
  })
  expect(result.current.read.data?.values['ui.font_scale']).toBe('large')
})

it.each(['planner.new_material_min', 'ui.font_scale'])('invalidates plan previews only for planning changes: %s', async key => {
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(jsonResponse({ values: {}, specs: [] }))))
  const { result } = setup()
  await waitFor(() => expect(result.current.read.isSuccess).toBe(true))
  const client = clients[0]
  const previewKey = ['plan', 'preview', 'steady', 3]
  client.setQueryData(previewKey, { blocks: [] })
  client.setQueryData(['session', 'existing'], { plan: ['unchanged'] })
  await act(async () => { await result.current.save.mutateAsync({ key, value: key.startsWith('planner.') ? 25 : 'large' }) })
  expect(client.getQueryState(previewKey)?.isInvalidated).toBe(key.startsWith('planner.'))
  expect(client.getQueryState(['session', 'existing'])?.isInvalidated).toBe(false)
  expect(client.getQueryData(['session', 'existing'])).toEqual({ plan: ['unchanged'] })
})


it('refreshes an active plan preview after a successful planning save', async () => {
  const client = new QueryClient()
  clients.push(client)
  let minutes = 20
  const preview = vi.fn(async () => ({ minutes }))
  vi.stubGlobal('fetch', vi.fn(() => {
    minutes = 25
    return Promise.resolve(jsonResponse({ values: { 'planner.new_material_min': minutes }, specs: [] }))
  }))
  const { result } = renderHook(() => ({
    plan: useQuery({ queryKey: ['plan', 'preview', 'steady', 3], queryFn: preview, staleTime: Infinity }),
    save: useSetPreference(),
  }), { wrapper: ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider> })
  await waitFor(() => expect(result.current.plan.data?.minutes).toBe(20))
  await act(async () => { await result.current.save.mutateAsync({ key: 'planner.new_material_min', value: 25 }) })
  await waitFor(() => expect(result.current.plan.data?.minutes).toBe(25))
  expect(preview).toHaveBeenCalledTimes(2)
})
