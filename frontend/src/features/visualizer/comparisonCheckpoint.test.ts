import { expect, it } from 'vitest'
import { initialComparison, parseComparison } from './comparisonCheckpoint'
import { initialLesson, parseLesson } from './lessonCheckpoint'
it('round-trips prediction, hint and reveal state inside a lesson checkpoint', () => {
  const comparison = { ...initialComparison, active: 'feature' as const, prediction: 'Smaller' as const, hint: true, compared: true }
  expect(parseLesson({ ...initialLesson, comparison }).comparison).toEqual(comparison)
  expect(parseLesson(initialLesson)).toEqual(initialLesson)
})
it.each([
  { ...initialComparison, version: 2 },
  { ...initialComparison, active: 'deleted' },
  { ...initialComparison, prediction: 'Correct' },
  { ...initialComparison, compared: 1 },
])('rejects unsupported comparison state', value => expect(() => parseComparison(value)).toThrow())
