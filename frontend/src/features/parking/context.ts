import type { Schemas } from '../../lib/api'
export type ThoughtContext = NonNullable<Schemas['ParkIn']['original_context']>
const id = (value: unknown): value is string => typeof value === 'string' && /^[A-Za-z0-9_.:-]{1,128}$/.test(value)
export function validThoughtContext(value: unknown): value is ThoughtContext {
  if (!value || typeof value !== 'object') return false
  const c = value as Record<string, unknown>
  if (c.version !== 1 || typeof c.label !== 'string' || !c.label.length || c.label.length > 200) return false
  if (c.kind === 'area') return id(c.area_id)
  if (c.kind === 'answer') return id(c.answer_id)
  if (c.kind === 'workspace') return id(c.workspace_id)
  return c.kind === 'project' && id(c.course_id) && id(c.section_id) && ['guide', 'notebook'].includes(String(c.view))
}
export function captureThoughtContext(path: string, search: string, label: string): ThoughtContext | undefined {
  const p = new URLSearchParams(search)
  const base = { version: 1 as const, label: label.slice(0, 200) || 'Original material' }
  let context: unknown
  if (path === '/areas') context = { ...base, kind: 'area', area_id: p.get('area') }
  else if (path === '/programs') context = { ...base, kind: 'project', course_id: p.get('course'), section_id: p.get('step'), view: p.get('view') === 'notebook' ? 'notebook' : 'guide' }
  else if (/^\/answers\/[^/]+$/.test(path)) context = { ...base, kind: 'answer', answer_id: path.split('/')[2] }
  else if (path === '/playground' && !p.has('lesson_session') && !p.has('lesson_skill')) context = { ...base, kind: 'workspace', workspace_id: p.get('workspace') }
  return validThoughtContext(context) ? context : undefined
}
export function thoughtContextPath(context: ThoughtContext): string | undefined {
  if (!validThoughtContext(context)) return undefined
  const c = context
  if (c.kind === 'area') return `/areas?area=${encodeURIComponent(c.area_id)}`
  if (c.kind === 'answer') return `/answers/${encodeURIComponent(c.answer_id)}`
  if (c.kind === 'workspace') return `/playground?workspace=${encodeURIComponent(c.workspace_id)}`
  return `/programs?${new URLSearchParams({ course: c.course_id, step: c.section_id, ...(c.view === 'notebook' ? { view: 'notebook' } : {}) })}`
}
