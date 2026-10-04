import { expect, it } from 'vitest'
import { captureThoughtContext, thoughtContextPath, validThoughtContext } from './context'

it('preserves exact project notebook identity without incidental query data', () => {
  const context = captureThoughtContext('/programs', '?course=example&step=cleaning&view=notebook&ignored=1', 'Data')!
  expect(thoughtContextPath(context)).toBe('/programs?course=example&step=cleaning&view=notebook')
})
it('does not infer a session or accept external paths as identities', () => {
  expect(captureThoughtContext('/session', '', 'Lesson')).toBeUndefined()
  expect(captureThoughtContext('/playground', '?workspace=complete&lesson_session=old', 'Code')).toBeUndefined()
  expect(captureThoughtContext('/areas', '?area=https://example.com', 'Area')).toBeUndefined()
  expect(validThoughtContext({version: 1, kind: 'area', area_id: '../escape', label: 'Bad'})).toBe(false)
})
it('builds only known internal destination kinds', () => {
  expect(thoughtContextPath(captureThoughtContext('/answers/id-1', '', 'Explanation')!)).toBe('/answers/id-1')
  expect(captureThoughtContext('/models', '', 'Models')).toBeUndefined()
})

it('distinguishes task starter from full course notebook and guide', () => {
  const context = captureThoughtContext('/programs', '?course=c&step=s&view=task', 'Starter')!
  expect(thoughtContextPath(context)).toBe('/programs?course=c&step=s&view=task')
})

it('audio lesson links use a known step and no playback instruction', () => {
  const context = captureThoughtContext('/playground/visualizer', '?capture_audio_lesson=harmonics', 'Harmonics')!
  expect(thoughtContextPath(context)).toBe('/playground/visualizer?saved_lesson=harmonics')
  expect(captureThoughtContext('/playground/visualizer', '?capture_audio_lesson=unknown', 'Unknown')).toBeUndefined()
})
