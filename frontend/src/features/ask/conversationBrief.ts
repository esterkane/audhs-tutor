import { useEffect, useState } from 'react'
export const briefFields = [
  ['task', 'Current task', 500],
  ['notes', 'Notes to retain (not checked facts)', 1500],
  ['examples', 'Hypothetical examples or assumptions', 1000],
  ['unresolved', 'Question still unresolved', 500],
] as const
export type Brief = { version: 1; task: string; notes: string; examples: string; unresolved: string }
export const emptyBrief = (): Brief => ({ version: 1, task: '', notes: '', examples: '', unresolved: '' })
export function validBrief(value: unknown): boolean {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const obj = value as Record<string, unknown>
  return Object.keys(obj).every(key => key === 'version' || briefFields.some(([field]) => field === key)) &&
    (obj.version === undefined || obj.version === 1) &&
    briefFields.every(([key, , limit]) => obj[key] === undefined || (typeof obj[key] === 'string' && obj[key].length <= limit))
}
export function savedBrief(metadata?: Record<string, unknown>): Brief | null {
  const envelope = metadata?.conversation_brief
  if (!envelope || typeof envelope !== 'object') return null
  const entry = envelope as Record<string, unknown>
  if (!['supplied', 'inherited', 'cleared'].includes(String(entry.mode)) || entry.origin !== 'learner_supplied_unverified' || typeof entry.hash !== 'string' || !/^[a-f0-9]{64}$/.test(entry.hash)) return null
  const value = entry.value
  if (!validBrief(value)) return null
  const obj = value as Record<string, unknown>
  if (obj.version !== 1 || !briefFields.every(([key]) => typeof obj[key] === 'string')) return null
  return value as Brief
}
export function parseBriefDraft(text: string): Brief | null {
  if (!text) return null
  const value: unknown = JSON.parse(text)
  if (!validBrief(value)) throw new Error('Saved conversation notes need attention. Clear them or restore the previous context before sending.')
  return { ...emptyBrief(), ...value as Partial<Brief> }
}


export async function checkedSavedBrief(metadata?: Record<string, unknown>): Promise<Brief | null> {
  const brief = savedBrief(metadata)
  if (!brief) return null
  const normalized = { version: brief.version, task: brief.task, notes: brief.notes, examples: brief.examples, unresolved: brief.unresolved }
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(normalized)))
  const hash = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('')
  return hash === (metadata!.conversation_brief as Record<string, unknown>).hash ? brief : null
}
export function useSavedBrief(metadata?: Record<string, unknown>) {
  const [result, setResult] = useState<{ metadata: typeof metadata; value: Brief | null } | null>(null)
  useEffect(() => {
    let active = true
    void checkedSavedBrief(metadata).then(value => { if (active) setResult({ metadata, value }) })
      .catch(() => { if (active) setResult({ metadata, value: null }) })
    return () => { active = false }
  }, [metadata])
  const supplied = metadata?.conversation_brief != null
  return { value: result && result.metadata === metadata ? result.value : null, ready: !supplied || !!(result && result.metadata === metadata) }
}
