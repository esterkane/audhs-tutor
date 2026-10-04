import { parseLesson, type LessonCheckpoint } from './lessonCheckpoint'
import { parsePreset, type Preset } from './engine'
import type { DraftHistoryState } from './useDraftHistory'

export const WORKSPACE_KEY = 'audhs:visualizer:workspace:v1'
export type WorkspaceCheckpoint = {
  version: 1
  preset: Preset
  history: DraftHistoryState
  view: 'Watch' | 'Learn' | 'Create'
  renderer: 'graph' | 'milkdrop'
  fileExpected?: boolean
  lesson?: LessonCheckpoint
  savedId: string | null
}
function parse(raw: string): WorkspaceCheckpoint {
  if (raw.length > 2_000_000) throw new Error('Workspace too large')
  const value = JSON.parse(raw) as WorkspaceCheckpoint
  if (value.version !== 1 || !['Watch', 'Learn', 'Create'].includes(value.view) ||
      !['graph', 'milkdrop'].includes(value.renderer) ||
      !(value.savedId === null || (typeof value.savedId === 'string' && value.savedId.length <= 100)) ||
      !value.history || typeof value.history.text !== 'string' || value.history.text.length > 16000)
    throw new Error('Unsupported workspace')
  if (value.fileExpected !== undefined && typeof value.fileExpected !== 'boolean') throw new Error('Invalid source checkpoint')
  if (value.lesson !== undefined) value.lesson = parseLesson(value.lesson)
  for (const list of [value.history.past, value.history.future]) {
    if (!Array.isArray(list) || list.length > 50) throw new Error('Invalid history')
    for (const text of list) {
      if (typeof text !== 'string') throw new Error('Invalid snapshot')
      parsePreset(text)
    }
  }
  return { ...value, preset: parsePreset(JSON.stringify(value.preset)) }
}

// Resource-free checkpoint: never retains an AudioContext, audio lease or file bytes.
export function createWorkspaceCheckpointStore(storage: () => Pick<Storage, 'getItem' | 'setItem'>) {
  let memory: WorkspaceCheckpoint | null = null
  let blocked = false
  return {
    read(): WorkspaceCheckpoint | null {
      if (memory) return memory
      try {
        const raw = storage().getItem(WORKSPACE_KEY)
        return raw ? (memory = parse(raw)) : null
      } catch {
        blocked = true // Preserve unknown/corrupt data; never silently overwrite it.
        return null
      }
    },
    write(value: WorkspaceCheckpoint): boolean {
      memory = value
      if (blocked) return false
      try {
        const raw = JSON.stringify(value)
        parse(raw)
        storage().setItem(WORKSPACE_KEY, raw)
        return true
      } catch {
        return false
      }
    },
    clearMemory() { memory = null; blocked = false },
  }
}
export const workspaceCheckpoint = createWorkspaceCheckpointStore(() => localStorage)
