import { act, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { WaitingElapsed } from './WaitingElapsed'

afterEach(() => vi.useRealTimers())
it('measures elapsed time rather than counting callbacks, and cleans up', () => {
  vi.useFakeTimers()
  const clock = vi.spyOn(performance, 'now').mockReturnValue(1000)
  const view = render(<WaitingElapsed startedAt={1000} />)
  clock.mockReturnValue(41000)
  act(() => document.dispatchEvent(new Event('visibilitychange')))
  expect(screen.getByText(/Waiting 40 seconds/)).toHaveAttribute('aria-live', 'off')
  view.unmount()
  expect(vi.getTimerCount()).toBe(0)
  clock.mockRestore()
})
