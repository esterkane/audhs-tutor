import { describe, expect, it } from 'vitest'
import { references, suggestedReferences } from './referenceCatalog'

describe('curated local references', () => {
  it('matches whole terms locally and does not invent a generic result', () => {
    expect(suggestedReferences('Explain NumPy array indexing').map((r) => r.id)).toEqual(['numpy-basics'])
    expect(suggestedReferences('Explain Python dictionaries').map((r) => r.id)).toEqual(['python-tutorial'])
    expect(suggestedReferences('How does feature scaling work?').map((r) => r.id)).toEqual([
      'sklearn-preprocessing',
    ])
    expect(suggestedReferences('What is a pythonicologist?')).toEqual([])
    expect(suggestedReferences('How do I play a chord?')).toEqual([])
  })
  it('never puts private input into outbound URLs', () => {
    const result = suggestedReferences('Python secret-project personal notes &token=secret')
    expect(result[0].url).toBe('https://docs.python.org/3/tutorial/')
    for (const card of references) {
      const url = new URL(card.url)
      expect(url.protocol).toBe('https:')
      expect(url.search).toBe('')
      expect(url.username).toBe('')
      expect(card.inspectedAt).toBe('2026-10-12')
    }
  })
})
