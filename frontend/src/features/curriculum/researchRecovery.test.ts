import { expect, it } from 'vitest'
import { validResearch } from './researchRecovery'

it('restores both historical model replies and checked calculations, rejecting mixed identities', () => {
  function research(exchange: object) {
    return { passage: 'Original source.', topic: 'Python', current: 0, questions: [{
      id: 'q', prompt: 'What is the result?', findings: '', evidence: '', unresolved: '', section: '',
      tutor_exchanges: [{ action: 'discuss', request: '', answer: { discussion: 'Saved reply.', needs_check: '', next_question: '', section: '', source_quotes: ['Original source.'] }, ...exchange }],
    }] }
  }
  expect(validResearch(research({ model_call_id: 'historical-model-call' }))).toBe(true)
  expect(validResearch(research({ model_call_id: null, calculation: 'python.string-repetition.v1' }))).toBe(true)
  expect(validResearch(research({ model_call_id: null, calculation: 'python.literal-expression.v1' }))).toBe(true)
  expect(validResearch(research({ model_call_id: null, calculation: 'vector.dot-cosine.v1' }))).toBe(true)
  expect(validResearch(research({ model_call_id: 'call', calculation: 'vector.dot-cosine.v1' }))).toBe(false)
  expect(validResearch(research({ model_call_id: 'call', calculation: 'python.literal-expression.v1' }))).toBe(false)
  expect(validResearch(research({ model_call_id: null, reference: 'python.string-identity.v1' }))).toBe(true)
  expect(validResearch(research({ model_call_id: 'call', reference: 'python.string-identity.v1' }))).toBe(false)
  expect(validResearch(research({ model_call_id: null, reference: 'unknown' }))).toBe(false)
  expect(validResearch(research({ model_call_id: null, calculation: 'python.string-repetition.v1', reference: 'python.string-identity.v1' }))).toBe(false)
  expect(validResearch(research({ model_call_id: null }))).toBe(false)
  expect(validResearch(research({ model_call_id: 'model-call', calculation: 'python.string-repetition.v1' }))).toBe(false)
  expect(validResearch(research({ model_call_id: null, calculation: 'unknown' }))).toBe(false)
})


it('allows a temporary empty question only for browser editing recovery', () => {
  const value = { passage: 'Source', topic: 'Topic', current: 0, questions: [{ id: 'q', prompt: '', findings: 'Kept', evidence: '', unresolved: '', section: '' }] }
  expect(validResearch(value)).toBe(false)
  expect(validResearch(value, { allowBlankPrompt: true })).toBe(true)
  expect(validResearch({ ...value, questions: [{ ...value.questions[0], prompt: 123 }] }, { allowBlankPrompt: true })).toBe(false)
})
