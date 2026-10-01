import type { ResponseStatus } from './TutorResponseStatus'

export type TextCache = { text: string; previousText: string | null; status: ResponseStatus }
const statuses = ['idle', 'streaming', 'complete', 'partial', 'failed', 'stopped']
export const cacheWarning = 'Received text could not be saved in this tab. Keep a copy before reloading.'
export const cacheKey = (scope: string) => `lesson-text:v1:${scope}`
export function readTextCache(scope: string): { value: TextCache | null; error: string } {
  try {
    const raw = sessionStorage.getItem(cacheKey(scope))
    if (!raw) return { value: null, error: '' }
    if (raw.length > 250000) throw new Error('Oversized text cache')
    const value = JSON.parse(raw) as TextCache
    if (
      !value ||
      typeof value.text !== 'string' ||
      (value.previousText !== null && typeof value.previousText !== 'string') ||
      !statuses.includes(value.status)
    )
      throw new Error('Invalid text cache')
    return { value, error: '' }
  } catch {
    return { value: null, error: 'Previously received text could not be restored from this tab.' }
  }
}
export function writeTextCache(scope: string, value: TextCache) {
  const raw = JSON.stringify(value)
  if (raw.length > 250000) throw new Error('Oversized text cache')
  sessionStorage.setItem(cacheKey(scope), raw)
}
