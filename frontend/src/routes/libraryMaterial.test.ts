import { expect, it } from 'vitest'
import type { Schemas } from '../lib/api'
import { matchesDraft } from './libraryMaterial'

it('searches learner-authored prose without indexing metadata, tutor exchanges, or assessment answers', () => {
  const draft = {
    title: 'Personal notes',
    status: 'draft',
    origin: 'knowledge_authored',
    payload: {
      authoring: {
        title: 'Personal notes',
        upload_id: 'upload-private-identifier',
        research: {
          questions: [
            {
              prompt: 'Compare policies',
              evidence: 'Measured using a restricted role',
              tutor_basis: 'private cached context',
              tutor_exchanges: [{ answer: 'sensitive tutor message' }],
            },
          ],
        },
      },
      assessments: [{ item: { hidden_key: 'hidden quiz answer' } }],
    },
  } as unknown as Schemas['DraftOut']
  for (const query of ['restricted role', 'Compare policies'])
    expect(matchesDraft(draft, query.toLocaleLowerCase())).toBe(true)
  for (const query of [
    'upload-private-identifier',
    'private cached context',
    'sensitive tutor message',
    'hidden quiz answer',
    'tutor_basis',
  ])
    expect(matchesDraft(draft, query.toLocaleLowerCase())).toBe(false)
})
