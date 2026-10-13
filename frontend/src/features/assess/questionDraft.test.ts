import { afterEach, expect, it, vi } from 'vitest'
import type { AssessmentView } from '../../lib/api'
import { clearQuestionDraft, questionDrafts, questionIdentity, questionDraftFailed, saveQuestionDraft } from './questionDraft'
const original: AssessmentView = { id: 'a', skill_id: 's', kind: 'mcq', question: 'Odd?', options: ['3','2'], content_version: 'one', confidence_required: false }
afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear() })
it('separates versions, retains labels, and clears only the graded version', () => {
  const revised = { ...original, content_version: 'two', question: 'Even?', options: ['3','4'] }
  saveQuestionDraft('versions', original, '0', 2)
  saveQuestionDraft('versions', revised, '1', 0)
  expect(questionDrafts('versions').map(row => row.answerLabel)).toEqual(['3', '4'])
  clearQuestionDraft('versions', revised)
  expect(questionDrafts('versions')).toEqual([expect.objectContaining({ identity: questionIdentity(original), answer: '0', hints: 2 })])
})
it('uses content as well as server token for identity', () => {
  expect(questionIdentity(original)).not.toBe(questionIdentity({ ...original, options: ['2', '3'] }))
})
it('retains memory and warning on storage failure, recovering on successful save', () => {
  const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('quota') })
  saveQuestionDraft('failed', original, '0', 1)
  expect(questionDraftFailed('failed')).toBe(true)
  expect(questionDrafts('failed')[0].answer).toBe('0')
  spy.mockRestore()
  saveQuestionDraft('failed', original, '', 1)
  expect(questionDraftFailed('failed')).toBe(false)
  expect(questionDrafts('failed')[0].answer).toBe('')
})
it('does not apply malformed stored history', () => {
  sessionStorage.setItem('malformed', JSON.stringify([{ answer: '0' }]))
  expect(questionDrafts('malformed')).toEqual([])
})
