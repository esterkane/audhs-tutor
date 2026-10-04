import { expect, it } from 'vitest'
import { initialLesson, parseLesson } from './lessonCheckpoint'
it('restores controls without playback state', () => {
  expect(parseLesson({ ...initialLesson, step: 'harmonics', hint: true, running: true })).toEqual({ ...initialLesson, step: 'harmonics', hint: true })
})
it.each([
  { ...initialLesson, step: 'removed' },
  { ...initialLesson, hint: 'yes' },
  { ...initialLesson, settings: { ...initialLesson.settings, frequency: 0 } },
  { ...initialLesson, settings: { ...initialLesson.settings, amplitude: 1 } },
  { ...initialLesson, settings: { ...initialLesson.settings, fftSize: 999 } },
  { ...initialLesson, settings: { ...initialLesson.settings, waveform: 'unknown' } },
])('rejects invalid recovered controls', value => expect(() => parseLesson(value)).toThrow())
