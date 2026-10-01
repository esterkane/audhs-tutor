import { initial, parsePreset, type Preset } from './engine'
export const LIBRARY_KEY = 'audhs:visualizer:library:v2'
export const LEGACY_KEY = 'audhs:visualizer:preset:v1'
export type SavedVisual = { id: string; name: string; favorite: boolean; preset: Preset }
export type Library = { version: 2; active: string | null; items: SavedVisual[] }
export function readLibrary(storage: Pick<Storage, 'getItem'>): Library {
  const raw = storage.getItem(LIBRARY_KEY)
  if (raw) {
    const value = JSON.parse(raw) as Library
    if (value.version !== 2 || !Array.isArray(value.items) || value.items.length > 100)
      throw new Error(
        'Unsupported preset library. Export your current preset before changing browser storage.',
      )
    const ids = new Set<string>()
    const items = value.items.map((item) => {
      if (
        typeof item.id !== 'string' ||
        ids.has(item.id) ||
        typeof item.name !== 'string' ||
        !item.name.trim() ||
        item.name.length > 80 ||
        typeof item.favorite !== 'boolean'
      )
        throw new Error('Invalid preset library. Existing storage was kept.')
      ids.add(item.id)
      return { ...item, preset: parsePreset(JSON.stringify(item.preset)) }
    })
    return {
      version: 2,
      active: typeof value.active === 'string' && ids.has(value.active) ? value.active : null,
      items,
    }
  }
  const legacy = storage.getItem(LEGACY_KEY)
  return {
    version: 2,
    active: legacy ? 'legacy' : null,
    items: legacy
      ? [
          {
            id: 'legacy',
            name: 'Recovered: ' + parsePreset(legacy).name.slice(0, 69),
            favorite: false,
            preset: parsePreset(legacy),
          },
        ]
      : [],
  }
}
export function writeLibrary(storage: Pick<Storage, 'setItem'>, library: Library) {
  if (library.items.length > 100)
    throw new Error('Library is full (100 presets). Export a preset to keep another copy.')
  storage.setItem(LIBRARY_KEY, JSON.stringify(library))
}
export function restoredPreset(): Preset {
  try {
    const library = readLibrary(localStorage)
    return library.items.find((x) => x.id === library.active)?.preset ?? initial
  } catch {
    return initial
  }
}
