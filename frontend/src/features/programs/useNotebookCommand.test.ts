import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { jsonResponse } from '../../test/utils'
import { useNotebookCommand } from './useNotebookCommand'

const service = '11111111-1111-4111-8111-111111111111'
beforeEach(() => sessionStorage.clear())
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); vi.useRealTimers() })

it('recovers a lost acknowledgement after remount using GET only', async () => {
  let body: Record<string, unknown>
  const fetcher = vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.method === 'POST') { body = JSON.parse(init.body as string); throw new Error('Lost reply') }
    return jsonResponse({ ...body, status: 'ready', message: 'Ready', url: 'http://127.0.0.1:8890/?token=private' })
  })
  vi.stubGlobal('fetch', fetcher)
  const onStatus = vi.fn()
  const first = renderHook(() => useNotebookCommand('course', onStatus))
  act(() => first.result.current.start(service, false))
  await waitFor(() => expect(first.result.current.error).toContain('acknowledgement'))
  first.unmount()
  const second = renderHook(() => useNotebookCommand('course', onStatus))
  expect(second.result.current.pending?.install).toBe(false)
  act(() => second.result.current.check())
  await waitFor(() => expect(second.result.current.pending).toBeNull())
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1)
  expect(sessionStorage.length).toBe(0)
  expect(onStatus).toHaveBeenCalledOnce()
})

it('bounds a stalled POST and prevents double activation', async () => {
  vi.useFakeTimers()
  const fetcher = vi.fn(() => new Promise<Response>(() => {}))
  vi.stubGlobal('fetch', fetcher)
  const { result } = renderHook(() => useNotebookCommand('course', vi.fn()))
  act(() => { result.current.start(service, true); result.current.start(service, true) })
  await act(async () => { await vi.advanceTimersByTimeAsync(15001) })
  expect(result.current.busy).toBe(false)
  expect(result.current.pending?.install).toBe(true)
  expect(result.current.error).toContain('may still be running')
  expect(fetcher).toHaveBeenCalledOnce()
})

it('does not start when storage fails until explicitly choosing memory-only recovery', async () => {
  const fetcher = vi.fn(async () => { throw new Error('Offline') })
  vi.stubGlobal('fetch', fetcher)
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Denied') })
  const { result } = renderHook(() => useNotebookCommand('course', vi.fn()))
  act(() => result.current.start(service, false))
  expect(fetcher).not.toHaveBeenCalled()
  expect(result.current.blocked).toBe(true)
  act(() => result.current.continueInMemory())
  act(() => result.current.start(service, false))
  await waitFor(() => expect(result.current.error).toContain('acknowledgement'))
  expect(fetcher).toHaveBeenCalledOnce()
})

it('ignores a late setup response after leaving the course', async () => {
  let finish!: (response: Response) => void
  let body: Record<string, unknown>
  vi.stubGlobal('fetch', vi.fn((_url: string, init: RequestInit) => {
    body = JSON.parse(init.body as string)
    return new Promise<Response>(resolve => { finish = resolve })
  }))
  const onStatus = vi.fn()
  const hook = renderHook(() => useNotebookCommand('course', onStatus))
  act(() => hook.result.current.start(service, false))
  hook.unmount()
  await act(async () => { finish(jsonResponse({ ...body, status: 'ready', message: 'Ready', url: null })) })
  expect(onStatus).not.toHaveBeenCalled()
  expect(sessionStorage.getItem('audhs.notebook-command.v1:course')).toBeTruthy()
})

it('keeps an unknown request after backend restart and never resends it', async () => {
  const pending = { request_id: '22222222-2222-4222-8222-222222222222', service_id: service, course_id: 'course', install: true }
  sessionStorage.setItem('audhs.notebook-command.v1:course', JSON.stringify(pending))
  const fetcher = vi.fn(async (...args: [string]) => { expect(args[0]).toContain("/requests/"); return jsonResponse({ error: { code: 'notebook_outcome_unknown', message: 'Backend restarted' } }, 409) })
  vi.stubGlobal('fetch', fetcher)
  const { result } = renderHook(() => useNotebookCommand('course', vi.fn()))
  act(() => result.current.check())
  await waitFor(() => expect(result.current.busy).toBe(false))
  expect(result.current.pending).toEqual(pending)
  act(() => result.current.start(service, true))
  expect(fetcher).toHaveBeenCalledOnce()
  expect(fetcher.mock.calls[0][0]).toContain('/requests/')
})

it('does not clear a saved command for another course or service', () => {
  const pending = { request_id: '22222222-2222-4222-8222-222222222222', service_id: service, course_id: 'course', install: false }
  sessionStorage.setItem('audhs.notebook-command.v1:course', JSON.stringify(pending))
  const { result } = renderHook(() => useNotebookCommand('course', vi.fn()))
  act(() => result.current.observe({ ...pending, course_id: 'other', status: 'ready', message: 'Ready', url: null }))
  expect(result.current.pending).toEqual(pending)
  act(() => result.current.observe({ ...pending, status: 'ready', message: 'Ready', url: null }))
  expect(result.current.pending).toBeNull()
})

it('allows explicit memory recovery when terminal receipt cleanup fails', async () => {
  const pending = { request_id: '22222222-2222-4222-8222-222222222222', service_id: service, course_id: 'course', install: false }
  sessionStorage.setItem('audhs.notebook-command.v1:course', JSON.stringify(pending))
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('Denied') })
  const fetcher = vi.fn(async () => jsonResponse({ ...pending, status: 'ready', message: 'Ready', url: null }))
  vi.stubGlobal('fetch', fetcher)
  const { result } = renderHook(() => useNotebookCommand('course', vi.fn()))
  act(() => result.current.check())
  await waitFor(() => expect(result.current.blocked).toBe(true))
  expect(result.current.pending).toEqual(pending)
  act(() => result.current.continueInMemory())
  expect(result.current.pending).toBeNull()
  expect(result.current.blocked).toBe(false)
  expect(fetcher).toHaveBeenCalledOnce()
})

it('releases a proven rejected command after explicit memory fallback', async () => {
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('Denied') })
  const fetcher = vi.fn(async () => jsonResponse({ error: { code: 'notebook_busy', message: 'Another setup is active' } }, 409))
  vi.stubGlobal('fetch', fetcher)
  const { result } = renderHook(() => useNotebookCommand('course', vi.fn()))
  act(() => result.current.start(service, false))
  await waitFor(() => expect(result.current.blocked).toBe(true))
  expect(result.current.pending).not.toBeNull()
  act(() => result.current.continueInMemory())
  expect(result.current.pending).toBeNull()
  expect(fetcher).toHaveBeenCalledOnce()
  act(() => result.current.start(service, false))
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
})
