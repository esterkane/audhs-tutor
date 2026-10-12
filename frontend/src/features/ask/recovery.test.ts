import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useAskRequestRecovery } from '../playground/useRequestRecovery'

afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear() })

it('retains the exact failed-storage retry through navigation without sending it', () => {
  const scope = `ask-test:${crypto.randomUUID()}`
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('denied') })
  const first = renderHook(() => useAskRequestRecovery(scope))
  let key = ''
  act(() => { key = first.result.current.prepare({ question: 'Explain a byte' }, { display: 'Explain a byte', submitted: '', snapshot: '', mode: 'explicit' }).key })
  first.unmount()
  const restored = renderHook(() => useAskRequestRecovery(scope))
  expect(restored.result.current.pending?.key).toBe(key)
  expect(restored.result.current.pending?.body.question).toBe('Explain a byte')
  expect(restored.result.current.error).toContain('Reload recovery may be unavailable')
  act(() => restored.result.current.accept(key))
  restored.unmount()
  const accepted = renderHook(() => useAskRequestRecovery(scope))
  expect(accepted.result.current.pending).toBeNull()
})
