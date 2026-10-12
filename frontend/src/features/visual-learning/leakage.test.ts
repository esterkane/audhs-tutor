import { describe, it, expect } from 'vitest'
import { centering, feedback } from './leakage'
describe('mean-centering information boundary', () => {
  it('held-out changes cannot change training-only parameters', () => {
    for (let value = 6; value <= 20; value++) {
      const result = centering('train', value)
      expect(result.mean).toBe(3)
      expect(result.transformed).toEqual([value - 3, value - 1])
    }
  })
  it('including held-out data changes the learned value', () => {
    expect(centering('all', 10).mean).toBe(7)
    expect(centering('all', 20).mean).toBe(12)
  })
  it('rejects unsupported and nonfinite inputs', () => {
    for (const n of [NaN, Infinity, 5, 21]) expect(() => centering('train', n)).toThrow()
    expect(() => feedback('unknown')).toThrow()
  })
})
