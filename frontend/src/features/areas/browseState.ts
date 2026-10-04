import { create } from 'zustand'

const KEY = 'audhs-browse-areas:v1'
type Snapshot = { current: string; recent: string[] }
function restore(): Snapshot & { storageError: boolean } {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return { current: '', recent: [], storageError: false }
    const value = JSON.parse(raw)
    if (value.version !== 1 || typeof value.current !== 'string' || !Array.isArray(value.recent) || !value.recent.every((id: unknown) => typeof id === 'string')) throw new Error('Invalid browsing history')
    return { current: value.current, recent: [...new Set<string>(value.recent)].slice(0, 5), storageError: false }
  } catch {
    return { current: '', recent: [], storageError: true }
  }
}
/** Navigation history only: never a learning goal or session checkpoint. */
export const useBrowseAreas = create<Snapshot & { storageError: boolean; remember: (id: string) => void }>((set, get) => ({
  ...restore(),
  remember: current => {
    const previous = get()
    if (previous.current === current) return
    const recent = current ? [current, ...previous.recent.filter(id => id !== current)].slice(0, 5) : previous.recent
    let storageError = false
    try { sessionStorage.setItem(KEY, JSON.stringify({ version: 1, current, recent })) } catch { storageError = true }
    set({ current, recent, storageError })
  },
}))
