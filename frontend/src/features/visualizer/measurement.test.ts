import { expect, it } from 'vitest'
import { summarize } from './measurement'
it('reports digital RMS and bin frequency independently from animation normalization', () => {
  const wave = Float32Array.from({ length: 1024 }, (_, i) => 0.4 * Math.sin((2 * Math.PI * 32 * i) / 1024))
  const db = new Float32Array(512).fill(-100)
  db[32] = -14
  const result = summarize(wave, db, 32000, 1024)
  expect(result.rms).toBeCloseTo(0.4 / Math.sqrt(2), 5)
  expect(result.peakHz).toBe(1000)
  expect(summarize(new Float32Array(1024), new Float32Array(512).fill(-Infinity), 32000, 1024).peakHz).toBe(0)
})
