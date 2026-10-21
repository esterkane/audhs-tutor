import { act, renderHook } from '@testing-library/react'
import { expect, it } from 'vitest'
import { useLessonDraft } from './useLessonDraft'

it('retains the original lesson-answer storage limit and preserves oversized input in this tab', () => {
  const scope = 'default-limit-' + crypto.randomUUID()
  const text = 'x'.repeat(100001)
  const view = renderHook(() => useLessonDraft(scope))
  act(() => view.result.current.setInput(text))
  expect(view.result.current.input).toBe(text)
  expect(view.result.current.error).toContain('could not be saved for reload')
  expect(sessionStorage.getItem('lesson-draft:v1:' + scope)).toBeNull()
  view.unmount()
  const restored = renderHook(() => useLessonDraft(scope))
  expect(restored.result.current.input).toBe(text)
  expect(restored.result.current.error).toContain('could not be saved for reload')
})
