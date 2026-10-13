import type { AssessmentView } from '../../lib/api'

export type QuestionDraft = { identity: string; question: string; answer: string; answerLabel: string; hints: number }
const memory = new Map<string, QuestionDraft[]>()
const failures = new Set<string>()
export function questionIdentity(item: AssessmentView): string {
  return JSON.stringify([item.id, item.content_version ?? null, item.kind, item.question, item.options ?? null, item.criteria ?? null])
}
export function questionDrafts(key: string): QuestionDraft[] {
  const cached = memory.get(key)
  if (cached) return cached
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(key) ?? '[]')
    if (Array.isArray(value) && value.every(row => row && typeof row.identity === 'string' && typeof row.question === 'string' && typeof row.answer === 'string' && typeof row.answerLabel === 'string' && Number.isInteger(row.hints) && row.hints >= 0)) return value as QuestionDraft[]
  } catch { /* absent or unavailable storage */ }
  return []
}
function persist(key: string, rows: QuestionDraft[]) {
  memory.set(key, rows)
  try { sessionStorage.setItem(key, JSON.stringify(rows)); failures.delete(key); memory.delete(key) }
  catch { failures.add(key) }
}
export function questionDraftFailed(key: string): boolean { return failures.has(key) }
export function saveQuestionDraft(key: string, item: AssessmentView, answer: string, hints: number) {
  const identity = questionIdentity(item)
  const row = { identity, question: item.question, answer, answerLabel: item.options?.[Number(answer)] ?? answer, hints }
  persist(key, [...questionDrafts(key).filter(old => old.identity !== identity), row])
}
export function clearQuestionDraft(key: string, item: AssessmentView) {
  persist(key, questionDrafts(key).filter(row => row.identity !== questionIdentity(item)))
}
