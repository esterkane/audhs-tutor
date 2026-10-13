import type { Schemas } from '../../lib/api'
export const lessonDomains = { ai_ml: 'AI and machine learning', programming: 'Programming', language: 'Language', guitar: 'Guitar', movement: 'Movement', meta: 'Learning and other topics' } as const
export type LessonForm = { title: string; domain: keyof typeof lessonDomains; objective: string; explanation: string; worked_example: string; question: string; criteria: string }
export type LessonBody = Omit<LessonForm, 'criteria'> & { criteria: string[]; binding: Schemas['AnswerLessonBinding'] }
export const emptyLesson = (): LessonForm => ({ title: '', domain: 'ai_ml', objective: '', explanation: '', worked_example: '', question: '', criteria: '' })
export function validLessonForm(value: unknown): value is LessonForm {
  if (!value || typeof value !== 'object') return false
  const v = value as LessonForm
  return Object.keys(v).length === 7 && Object.hasOwn(lessonDomains, v.domain)
    && ['title', 'objective', 'explanation', 'worked_example', 'question', 'criteria'].every(k => typeof v[k as 'title'] === 'string' && v[k as 'title'].length <= 50000)
}
export function lessonBody(form: LessonForm, binding: Schemas['AnswerLessonBinding']): LessonBody {
  const criteria = form.criteria.split('\n').map(s => s.trim()).filter(Boolean)
  if (!validLessonForm(form) || !form.title.trim() || form.title.length > 300 || !form.objective.trim() || form.objective.length > 1000
    || !['explanation', 'worked_example', 'question'].every(k => form[k as 'question'].trim() && form[k as 'question'].length <= 4000)
    || !criteria.length || criteria.length > 12 || criteria.some(c => c.length > 4000) || new Set(criteria.map(c => c.toLowerCase())).size !== criteria.length)
    throw new Error('Complete every field. Use a title up to 300 characters, an objective up to 1,000, other fields up to 4,000, and 1–12 distinct criteria (one per line).')
  const body = { ...form, criteria, binding }
  if (new TextEncoder().encode(JSON.stringify(body)).length > 65536) throw new Error('The draft exceeds the 64 KiB request limit. Shorten the text before saving.')
  return body
}
export function validLessonBody(value: unknown, answerId: string): value is LessonBody {
  try {
    const v = value as LessonBody
    if (!v || !v.binding || !Array.isArray(v.criteria) || !v.criteria.every(c => typeof c === 'string') || Object.keys(v).length !== 8) return false
    const b = v.binding
    if (Object.keys(b).length !== 6 || b.schema_version !== 'answer-lesson-binding.v1' || b.answer_id !== answerId
      || ![b.question_sha256, b.answer_sha256, b.lineage_sha256, b.source_state_sha256].every(h => typeof h === 'string' && /^[a-f0-9]{64}$/.test(h))) return false
    const { binding, ...fields } = v
    lessonBody({ ...fields, criteria: v.criteria.join('\n') }, binding)
    return true
  } catch { return false }
}
