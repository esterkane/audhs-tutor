import { create } from 'zustand'
import { validThoughtContext, type ThoughtContext } from '../parking/context'

const KEY = 'audhs-recent-contexts:v1'
const LIMIT = 12
/** Copy only the context contract; callers cannot checkpoint incidental source text/URLs. */
export function cleanContext(value: unknown): ThoughtContext | undefined {
  if (!validThoughtContext(value)) return undefined
  const base = { version: 1 as const, label: value.label }
  switch (value.kind) {
    case 'area': return { ...base, kind: value.kind, area_id: value.area_id }
    case 'source': return { ...base, kind: value.kind, chunk_id: value.chunk_id }
    case 'answer': return { ...base, kind: value.kind, answer_id: value.answer_id }
    case 'workspace': return { ...base, kind: value.kind, workspace_id: value.workspace_id }
    case 'audio_lesson': return { ...base, kind: value.kind, lesson: value.lesson }
    case 'project': return { ...base, kind: value.kind, course_id: value.course_id, section_id: value.section_id, view: value.view }
    case 'lesson': return { ...base, kind: value.kind, session_id: value.session_id, skill_id: value.skill_id, block_index: value.block_index, block_started_at: value.block_started_at }
  }
}
export function contextIdentity(context: ThoughtContext): string {
  const clean = cleanContext(context)
  if (!clean) return ''
  const { label: _label, ...identity } = clean
  void _label
  return JSON.stringify(identity)
}
type State = { items: ThoughtContext[]; storageError: boolean }
export function restoreHistory(): State {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return { items: [], storageError: false }
    if (raw.length > 20000) throw new Error('Oversized history')
    const value = JSON.parse(raw)
    if (value.version !== 1 || !Array.isArray(value.items) || value.items.length > LIMIT) throw new Error('Invalid history')
    const items: ThoughtContext[] = []
    for (const entry of value.items) {
      const context = cleanContext(entry)
      if (!context) throw new Error('Invalid context')
      if (!items.some(item => contextIdentity(item) === contextIdentity(context))) items.push(context)
    }
    return { items, storageError: false }
  } catch { return { items: [], storageError: true } }
}
/** Tab-local navigation only. Does not save work, change goals or write learning evidence. */
export const useRecentContexts = create<State & { remember: (value: unknown) => void; clear: () => void }>((set, get) => {
  function save(items: ThoughtContext[]) {
    let storageError = false
    try {
      if (items.length) sessionStorage.setItem(KEY, JSON.stringify({ version: 1, items }))
      else sessionStorage.removeItem(KEY)
    } catch { storageError = true }
    set({ items, storageError })
  }
  return {
    ...restoreHistory(),
    remember: value => {
      const context = cleanContext(value)
      if (!context) return
      const previous = get()
      if (!previous.storageError && JSON.stringify(previous.items[0]) === JSON.stringify(context)) return
      save([context, ...previous.items.filter(item => contextIdentity(item) !== contextIdentity(context))].slice(0, LIMIT))
    },
    clear: () => save([]),
  }
})
