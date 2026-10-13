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

it('keeps a visual binding and retry identity across remount without resending', async () => {
  const { useVisualRequestRecovery } = await import('../playground/useRequestRecovery')
  const scope = `visual:${crypto.randomUUID()}`
  const body = { binding: { schema_version: 'answer-visual-binding.v1' as const, answer_id: 'answer', question_sha256: 'a'.repeat(64), answer_sha256: 'b'.repeat(64), lineage_sha256: 'c'.repeat(64), learning_purpose: null } }
  const first = renderHook(() => useVisualRequestRecovery(scope))
  let key = ''
  act(() => { key = first.result.current.prepare(body, { display: 'Visual', submitted: '', snapshot: '', mode: 'explicit' }).key })
  first.unmount()
  const second = renderHook(() => useVisualRequestRecovery(scope))
  expect(second.result.current.pending?.key).toBe(key)
  expect(second.result.current.pending?.body).toEqual(body)
  act(() => second.result.current.accept(key))
  expect(second.result.current.pending).toBeNull()
})

it('retains an exact visual review across navigation without changing the decision or note', async () => {
  const { useVisualReviewRecovery } = await import('../playground/useRequestRecovery')
  const scope = `visual-review:${crypto.randomUUID()}`
  const body = { action: 'review' as const, document_id: 'doc', version_id: 'version', expected_revision: 2,
    content_sha256: 'a'.repeat(64), snapshot_sha256: 'b'.repeat(64), decision: 'reject' as const, confirm: true as const, note: 'Do not conflate fitting with applying.' }
  const first = renderHook(() => useVisualReviewRecovery(scope))
  let key = ''
  act(() => { key = first.result.current.prepare(body, { display: 'Needs correction', submitted: '', snapshot: '', mode: 'explicit' }).key })
  first.unmount()
  const restored = renderHook(() => useVisualReviewRecovery(scope))
  expect(restored.result.current.pending?.key).toBe(key)
  expect(restored.result.current.pending?.body).toEqual(body)
  act(() => restored.result.current.accept(key))
  expect(restored.result.current.pending).toBeNull()
})
