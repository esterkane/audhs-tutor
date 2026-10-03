import { expect, it, vi } from 'vitest'
import { claimReading, updateReading, useReadingControls } from './readingOwner'

it('stale releases cannot discard the current reading', () => {
  const first = vi.fn()
  const second = vi.fn()
  const releaseFirst = claimReading(first)
  const releaseSecond = claimReading(second)
  expect(first).toHaveBeenCalledOnce()
  releaseFirst()
  const releaseThird = claimReading(vi.fn())
  expect(second).toHaveBeenCalledOnce()
  releaseSecond()
  releaseThird()
})
it('releasing a finished reading prevents later stop callbacks', () => {
  const stop = vi.fn()
  claimReading(stop)()
  claimReading(vi.fn())()
  expect(stop).not.toHaveBeenCalled()
})

it('only the current lease can publish shared controls', () => {
  const old = claimReading(vi.fn())
  const current = claimReading(vi.fn())
  const controls = {
    status: 'Preparing',
    paused: false,
    changing: false,
    ready: true,
    stop: vi.fn(),
    togglePause: vi.fn(),
  }
  updateReading(current, controls)
  updateReading(old, { ...controls, status: 'Stale' })
  expect(useReadingControls.getState().reading?.status).toBe('Preparing')
  old()
  expect(useReadingControls.getState().reading).not.toBeNull()
  current()
  expect(useReadingControls.getState().reading).toBeNull()
})
