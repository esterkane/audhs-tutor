/** Best-effort tab-local draft storage. Storage failure must never hide a successful grade. */
type Draft = { answer: string; hints: number }
const fallback = new Map<string, Draft>()
export function readDraft(key: string): Draft {
  const memory = fallback.get(key)
  if (memory) return memory
  try {
    const parsed = JSON.parse(sessionStorage.getItem(key) ?? 'null') as Partial<Draft> | null
    if (parsed && typeof parsed.answer === 'string')
      return { answer: parsed.answer, hints: Math.max(0, Number(parsed.hints) || 0) }
  } catch {
    /* restricted storage: keep working in memory */
  }
  return { answer: '', hints: 0 }
}
export function writeDraft(key: string, update: Partial<Draft>) {
  const next = { ...readDraft(key), ...update }
  fallback.set(key, next)
  try {
    sessionStorage.setItem(key, JSON.stringify(next))
  } catch {
    /* memory copy remains */
  }
}
export function clearDraft(key: string) {
  fallback.set(key, { answer: '', hints: 0 })
  try {
    sessionStorage.removeItem(key)
    fallback.delete(key)
  } catch {
    /* grading already succeeded */
  }
}
