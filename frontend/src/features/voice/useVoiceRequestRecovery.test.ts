import { act, renderHook } from '@testing-library/react'
import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { apiFetch } from '../../lib/api'
import { useVoiceRequestRecovery, voiceRequestKey } from './useVoiceRequestRecovery'
vi.mock('../../lib/api', () => ({ apiFetch: vi.fn() }))
const id = '12345678-1234-1234-1234-123456789abc'
beforeEach(() => { sessionStorage.clear(); vi.mocked(apiFetch).mockReset() })
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })
it('persists before admission and restores without fetching; checks only on explicit action', async () => {
  const first = renderHook(() => useVoiceRequestRecovery('scope', 'session'))
  act(() => { expect(first.result.current.begin(id)).toBe(true) })
  expect(sessionStorage.getItem(voiceRequestKey('scope'))).toBe(id)
  act(() => { expect(first.result.current.begin(crypto.randomUUID())).toBe(false) })
  first.unmount()
  const next = renderHook(() => useVoiceRequestRecovery('scope', 'session'))
  expect(next.result.current.pending).toBe(id)
  expect(apiFetch).not.toHaveBeenCalled()
  vi.mocked(apiFetch).mockResolvedValue({ request_id: id, status: 'completed', text: 'Saved reply' })
  await act(() => next.result.current.check())
  expect(apiFetch).toHaveBeenCalledExactlyOnceWith(`/api/voice/requests/${id}?session_id=session`, { signal: expect.any(AbortSignal) })
  expect(next.result.current.result?.text).toBe('Saved reply')
  expect(next.result.current.pending).toBe(id)
})
it('does not send on storage denial without explicit memory-only choice', () => {
  const hook = renderHook(() => useVoiceRequestRecovery('scope', 'session'))
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error() })
  act(() => { expect(hook.result.current.begin(id)).toBe(false) })
  expect(hook.result.current.pending).toBeNull()
  act(() => hook.result.current.useMemoryOnly())
  act(() => { expect(hook.result.current.begin(id)).toBe(true) })
  expect(hook.result.current.pending).toBe(id)
})
it('ignores an obsolete lookup after dismiss and a different request', async () => {
  const hook = renderHook(() => useVoiceRequestRecovery('scope', 'session'))
  let resolve!: (v: unknown) => void
  vi.mocked(apiFetch).mockImplementation(() => new Promise((r) => { resolve = r }))
  act(() => { hook.result.current.begin(id) })
  let checking!: Promise<unknown>
  act(() => { checking = hook.result.current.check() })
  act(() => { hook.result.current.discard(); hook.result.current.begin(crypto.randomUUID()) })
  await act(async () => { resolve({ request_id: id, status: 'completed', text: 'Old' }); await checking })
  expect(hook.result.current.result).toBeNull()
})
it('retains pending on failed lookup or clear and ignores another turn terminal', async () => {
  const hook = renderHook(() => useVoiceRequestRecovery('scope', 'session'))
  act(() => { hook.result.current.begin(id); hook.result.current.finish(crypto.randomUUID()) })
  vi.mocked(apiFetch).mockRejectedValue(new Error('offline'))
  await act(() => hook.result.current.check())
  expect(hook.result.current.pending).toBe(id)
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error() })
  act(() => { expect(hook.result.current.discard()).toBe(false) })
  expect(hook.result.current.pending).toBe(id)
})
it.each(['not_found', 'unresolved', 'partial', 'completed'])('preserves %s status without regenerating', async (status) => {
  const hook = renderHook(() => useVoiceRequestRecovery('scope', 'session'))
  act(() => { hook.result.current.begin(id) })
  vi.mocked(apiFetch).mockResolvedValue({ request_id: id, status })
  await act(() => hook.result.current.check())
  expect(hook.result.current.result?.status).toBe(status)
  expect(apiFetch).toHaveBeenCalledTimes(1)
})

it('releases a stalled lookup and ignores its late result after retry', async () => {
  vi.useFakeTimers()
  const hook = renderHook(() => useVoiceRequestRecovery('scope', 'session'))
  act(() => { hook.result.current.begin(id) })
  let resolve!: (value: unknown) => void
  vi.mocked(apiFetch).mockImplementationOnce(() => new Promise((r) => { resolve = r }))
  let check!: Promise<unknown>
  act(() => { check = hook.result.current.check() })
  await act(async () => { await vi.advanceTimersByTimeAsync(15001); await check })
  expect(hook.result.current.checking).toBe(false)
  expect(hook.result.current.pending).toBe(id)
  vi.mocked(apiFetch).mockResolvedValueOnce({ request_id: id, status: 'partial', text: 'Current' })
  await act(() => hook.result.current.check())
  await act(async () => { resolve({ request_id: id, status: 'completed', text: 'Late' }) })
  expect(hook.result.current.result?.text).toBe('Current')
})
it('can start after explicitly clearing malformed stored identity', () => {
  sessionStorage.setItem(voiceRequestKey('scope'), 'malformed')
  const hook = renderHook(() => useVoiceRequestRecovery('scope', 'session'))
  act(() => { expect(hook.result.current.begin(id)).toBe(false) })
  act(() => { expect(hook.result.current.discard()).toBe(true) })
  act(() => { expect(hook.result.current.begin(id)).toBe(true) })
})
