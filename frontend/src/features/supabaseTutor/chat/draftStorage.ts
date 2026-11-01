export interface RetainedDraft {
  draft: string
  pending: { text: string; afterTutorCount: number } | null
}
const empty = (): RetainedDraft => ({ draft: '', pending: null })

export function readDraft(key?: string): RetainedDraft {
  if (!key) return empty()
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) ?? 'null')
    if (!value || typeof value !== 'object') return empty()
    const record = value as Partial<RetainedDraft>
    const pending = record.pending
    return {
      draft: typeof record.draft === 'string' ? record.draft : '',
      pending:
        pending &&
        typeof pending.text === 'string' &&
        Number.isInteger(pending.afterTutorCount) &&
        pending.afterTutorCount >= 0
          ? { text: pending.text, afterTutorCount: pending.afterTutorCount }
          : null,
    }
  } catch {
    return empty()
  }
}

export function writeDraft(key: string | undefined, value: RetainedDraft): boolean {
  if (!key) return true
  try {
    if (!value.draft && !value.pending) localStorage.removeItem(key)
    else localStorage.setItem(key, JSON.stringify(value))
    return true
  } catch {
    return false
  }
}
