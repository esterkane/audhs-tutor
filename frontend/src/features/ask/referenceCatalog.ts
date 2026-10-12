/** Curated link metadata only. No remote search, page fetch, or answer certification. */
export type ReferenceCard = {
  id: string
  title: string
  url: string
  publisher: string
  why: string
  versionNote: string
  inspectedAt: string
  reuseNote: string
  terms: readonly string[]
}

export const references: readonly ReferenceCard[] = [
  {
    id: 'python-tutorial',
    title: 'Python tutorial',
    url: 'https://docs.python.org/3/tutorial/',
    publisher: 'Python Software Foundation',
    why: 'Language fundamentals, control flow, functions and data structures. Assumes some programming experience.',
    versionNote: 'Rolling Python 3 documentation; select the version matching your local environment.',
    inspectedAt: '2026-10-12',
    reuseNote:
      'Documentation: PSF License v2; code examples additionally Zero Clause BSD. Linked content remains third-party material.',
    terms: ['python', 'dictionary', 'dictionaries', 'list comprehension', 'python function'],
  },
  {
    id: 'numpy-basics',
    title: 'NumPy array basics',
    url: 'https://numpy.org/doc/stable/user/absolute_beginners.html',
    publisher: 'NumPy',
    why: 'Array creation, shapes, indexing and basic array operations with examples.',
    versionNote: 'Rolling stable documentation; API details may differ from your installed version.',
    inspectedAt: '2026-10-12',
    reuseNote:
      'Redistribution permissions have not been assessed. Opening this link does not import its content.',
    terms: ['numpy', 'ndarray', 'array shape', 'array indexing'],
  },
  {
    id: 'sklearn-preprocessing',
    title: 'Data preprocessing with scikit-learn',
    url: 'https://scikit-learn.org/stable/modules/preprocessing.html',
    publisher: 'scikit-learn',
    why: 'Compare feature scaling, encoding and other preprocessing transformations.',
    versionNote: 'Rolling stable documentation; use the version matching your notebook environment.',
    inspectedAt: '2026-10-12',
    reuseNote:
      'Redistribution permissions have not been assessed. This link does not establish fairness or correctness of a cleaning decision.',
    terms: ['scikit-learn', 'sklearn', 'preprocessing', 'feature scaling', 'standardization', 'one-hot'],
  },
]

export function suggestedReferences(question: string): readonly ReferenceCard[] {
  // Matching happens entirely in this process; no question-derived URL or query is created.
  const normalized = question.toLocaleLowerCase().replace(/[^\p{L}\p{N}-]+/gu, ' ')
  const padded = ` ${normalized} `
  return references.filter((card) => card.terms.some((term) => padded.includes(` ${term} `))).slice(0, 3)
}
