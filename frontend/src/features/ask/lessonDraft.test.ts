import { describe, expect, it } from 'vitest'
import { emptyLesson, lessonBody, validLessonBody, validLessonForm } from './lessonDraft'
const binding = { schema_version: 'answer-lesson-binding.v1' as const, answer_id: 'a', question_sha256: 'a'.repeat(64), answer_sha256: 'b'.repeat(64), lineage_sha256: 'c'.repeat(64), source_state_sha256: 'd'.repeat(64) }
const form = { ...emptyLesson(), title: 'Training only', objective: 'Apply training statistics', explanation: 'Separate training from held-out data.', worked_example: 'Training ages 20 and 40 give median 30.', question: 'Which median fills held-out ages?', criteria: 'Use training ages only\nApply the same median' }
describe('private lesson request recovery', () => {
  it('keeps incomplete authoring work but rejects an incomplete submission', () => {
    expect(validLessonForm(emptyLesson())).toBe(true)
    expect(() => lessonBody(emptyLesson(), binding)).toThrow('Complete every field')
  })
  it('retains exact content and rejects foreign or malformed bindings', () => {
    const body = lessonBody(form, binding)
    expect(validLessonBody(body, 'a')).toBe(true)
    expect(body.question).toBe(form.question)
    expect(body.criteria).toEqual(['Use training ages only', 'Apply the same median'])
    expect(validLessonBody(body, 'other')).toBe(false)
    expect(validLessonBody({ ...body, binding: { ...binding, answer_sha256: 'bad' } }, 'a')).toBe(false)
    expect(validLessonBody({ ...body, extra: true }, 'a')).toBe(false)
  })
  it('rejects duplicate criteria and oversized UTF-8 bodies', () => {
    expect(() => lessonBody({ ...form, criteria: 'Train only\ntrain only' }, binding)).toThrow()
    expect(() => lessonBody({ ...form, criteria: Array.from({length: 12}, (_, i) => `${i}${'界'.repeat(3990)}`).join('\n') }, binding)).toThrow('64 KiB')
  })
})
