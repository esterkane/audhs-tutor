import type { TurnDone } from '../../lib/api'
import type { ResponseStatus } from './TutorResponseStatus'

export type TextCache = {
  text: string
  previousText: string | null
  status: ResponseStatus
  done?: TurnDone | null
}
const statuses = ['idle', 'streaming', 'complete', 'partial', 'failed', 'stopped']
export const cacheWarning = 'Received text could not be saved in this tab. Keep a copy before reloading.'
export const cacheKey = (scope: string) => `lesson-text:v1:${scope}`
export function readTextCache(scope: string): { value: TextCache | null; error: string } {
  try {
    const raw = sessionStorage.getItem(cacheKey(scope))
    if (!raw) return { value: null, error: '' }
    if (raw.length > 250000) throw new Error('Oversized text cache')
    const { completion, ...value } = JSON.parse(raw) as TextCache & {
      completion?: { version?: unknown; reply?: unknown } | null
    }
    if (
      !value ||
      typeof value.text !== 'string' ||
      (value.previousText !== null && typeof value.previousText !== 'string') ||
      !statuses.includes(value.status)
    )
      throw new Error('Invalid text cache')
    let done: unknown = value.done
    if (completion !== undefined) {
      const reply = completion?.reply
      done =
        completion?.version === 1 &&
        reply &&
        typeof reply === 'object' &&
        !Array.isArray(reply) &&
        !('text' in reply)
          ? { ...reply, text: value.text }
          : {}
    }
    if (done != null && (value.status !== 'complete' || !validCompletion(done, value.text))) {
      return {
        value: { ...value, done: null },
        error: 'Completed reply details could not be restored. Received text is still available.',
      }
    }
    return { value: done == null ? value : { ...value, done: done as TurnDone }, error: '' }
  } catch {
    return { value: null, error: 'Previously received text could not be restored from this tab.' }
  }
}
export function writeTextCache(scope: string, value: TextCache) {
  // Completion v1 shares the enclosing exact text instead of duplicating large replies.
  const { done, ...base } = value
  const reply = done ? Object.fromEntries(Object.entries(done).filter(([key]) => key !== 'text')) : null
  const raw = JSON.stringify(
    done && done.text === value.text ? { ...base, completion: { version: 1, reply } } : value,
  )
  if (raw.length > 250000 && done) {
    const textOnly = JSON.stringify(base)
    if (textOnly.length > 250000) throw new Error('Oversized text cache')
    sessionStorage.setItem(cacheKey(scope), textOnly)
    return 'Received text saved, but completed reply details are too large to restore after reload.'
  }
  if (raw.length > 250000) throw new Error('Oversized text cache')
  sessionStorage.setItem(cacheKey(scope), raw)
  return ''
}

// Browser recovery is not new server evidence. Restore only an exact completed reply;
// malformed optional metadata must never discard independently readable text.
function validCompletion(value: unknown, text: string): value is TurnDone {
  if (!value || typeof value !== 'object') return false
  const v = value as Record<string, unknown>
  const strings = (x: unknown): x is string[] => Array.isArray(x) && x.every((s) => typeof s === 'string')
  const nullable = (x: unknown) => x === null || typeof x === 'string'
  const optional = (x: unknown) => x === undefined || nullable(x)
  return (
    v.outcome === 'ok' &&
    v.text === text &&
    typeof v.turn_id === 'string' &&
    v.turn_id.length > 0 &&
    typeof v.tutor_trace_id === 'string' &&
    ['model_call_id', 'registry_id', 'route', 'representation'].every((key) => nullable(v[key])) &&
    ['answer_id', 'save_error', 'save_receipt', 'usage_source', 'cost_status'].every((key) =>
      optional(v[key]),
    ) &&
    (v.memory_answers === undefined || strings(v.memory_answers)) &&
    typeof v.sentences === 'number' &&
    Number.isFinite(v.sentences) &&
    typeof v.latency_ms === 'number' &&
    Number.isFinite(v.latency_ms) &&
    strings(v.flagged) &&
    strings(v.dropped) &&
    Array.isArray(v.sources) &&
    v.sources.every(
      (s) =>
        s &&
        typeof s === 'object' &&
        typeof s.chunk_id === 'string' &&
        typeof s.citation === 'string' &&
        typeof s.trust_tier === 'number' &&
        Number.isFinite(s.trust_tier) &&
        typeof s.score === 'number' &&
        Number.isFinite(s.score) &&
        typeof s.cited === 'boolean' &&
        (s.flagged === undefined || strings(s.flagged)),
    )
  )
}
