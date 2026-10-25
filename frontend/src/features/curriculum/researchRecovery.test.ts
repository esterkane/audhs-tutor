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
  expect(validResearch(research({ model_call_id: 'call', calculation: 'python.literal-expression.v1' }))).toBe(false)
  expect(validResearch(research({ model_call_id: null, reference: 'python.string-identity.v1' }))).toBe(true)
  expect(validResearch(research({ model_call_id: 'call', reference: 'python.string-identity.v1' }))).toBe(false)
  expect(validResearch(research({ model_call_id: null, reference: 'unknown' }))).toBe(false)
  expect(validResearch(research({ model_call_id: null, calculation: 'python.string-repetition.v1', reference: 'python.string-identity.v1' }))).toBe(false)
  expect(validResearch(research({ model_call_id: null }))).toBe(false)
  expect(validResearch(research({ model_call_id: 'model-call', calculation: 'python.string-repetition.v1' }))).toBe(false)
  expect(validResearch(research({ model_call_id: null, calculation: 'unknown' }))).toBe(false)
})
