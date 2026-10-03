import { expect, it, vi } from 'vitest'
import { claimReading } from './readingOwner'

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
