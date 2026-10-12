import type { Schemas } from '../../lib/api'
import { useLessonDraft } from '../tutor/useLessonDraft'
type Hit = Schemas['SearchHit']

export function useSelectedPassages(scope: string) {
  const draft = useLessonDraft(`${scope}:sources`, 'selected sources')
  let selected: Hit[] = []
  let invalid = false
  try {
    const value: unknown = JSON.parse(draft.input || '[]')
    if (
      !Array.isArray(value) ||
      value.length > 6 ||
      value.some(
        (h) =>
          !h ||
          typeof h.chunk_id !== 'string' ||
          typeof h.text !== 'string' ||
          typeof h.citation !== 'string',
      )
    )
      throw new Error('Invalid selection')
    selected = value as Hit[]
  } catch {
    invalid = true
  }
  return { selected, error: draft.error, invalid, set: (hits: Hit[]) => draft.setInput(JSON.stringify(hits)) }
}

export async function sourceSelection(hits: Hit[]): Promise<Schemas['AskSources'] | undefined> {
  if (!hits.length) return undefined
  const hashes = await Promise.all(
    hits.map(async (hit) => {
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(hit.text))
      return [
        hit.chunk_id,
        Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join(''),
      ]
    }),
  )
  return { passage_ids: hits.map((h) => h.chunk_id), passage_hashes: Object.fromEntries(hashes) }
}
