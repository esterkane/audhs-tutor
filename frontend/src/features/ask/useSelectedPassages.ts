import type { Schemas } from '../../lib/api'
import { useLessonDraft } from '../tutor/useLessonDraft'
export type SelectablePassage = Pick<Schemas['SearchHit'], 'chunk_id' | 'text' | 'citation'> & { quarantined?: boolean }

export function useSelectedPassages(scope: string) {
  const draft = useLessonDraft(`${scope}:sources`, 'selected sources')
  let selected: SelectablePassage[] = []
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
    selected = value as SelectablePassage[]
  } catch {
    invalid = true
  }
  return { selected, error: draft.error, invalid, set: (hits: SelectablePassage[]) => draft.setInput(JSON.stringify(hits)) }
}

export async function sourceSelection(hits: SelectablePassage[]): Promise<Schemas['AskSources'] | undefined> {
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


// Historical snapshots are data, not reconstructed search results or current trust claims.
export function previousPassages(raw: unknown): SelectablePassage[] | null {
  if (raw == null) return []
  if (!Array.isArray(raw) || raw.length > 6) return null
  const seen = new Set<string>()
  const passages: SelectablePassage[] = []
  for (const value of raw) {
    if (!value || typeof value.chunk_id !== 'string' || !value.chunk_id || value.chunk_id.length > 128 ||
      seen.has(value.chunk_id) || typeof value.text !== 'string' || !value.text || value.text.length > 16000 ||
      typeof value.citation !== 'string' || !value.citation || value.citation.length > 16000) return null
    seen.add(value.chunk_id)
    passages.push({ chunk_id: value.chunk_id, text: value.text, citation: value.citation })
  }
  if (passages.reduce((size, passage) => size + passage.text.length + passage.citation.length, 0) > 16000) return null
  return passages
}
