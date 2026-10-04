import { useState } from 'react'

export type ThoughtDraft = { text: string; sessionId: string | null; skillId: string | null; unconfirmed: boolean }
const KEY = 'parking-draft:v1'
const empty: ThoughtDraft = { text: '', sessionId: null, skillId: null, unconfirmed: false }
const validId = (value: unknown) => value === null || (typeof value === 'string' && value.length > 0 && value.length <= 128)
function restore(): { draft: ThoughtDraft; error: string } {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return { draft: empty, error: '' }
    if (raw.length > 5000) throw new Error('Oversized draft')
    const value = JSON.parse(raw)
    const d = value.draft
    if (value.version !== 1 || !d || typeof d.text !== 'string' || d.text.length > 500 || !validId(d.sessionId) || !validId(d.skillId) || typeof d.unconfirmed !== 'boolean') throw new Error('Invalid draft')
    return { draft: d, error: '' }
  } catch {
    return { draft: empty, error: 'The previous thought draft could not be restored. Restoring this page did not submit anything. Check Saved thoughts if an earlier save was unconfirmed.' }
  }
}

/** Tab-local draft only. Restoration never performs a server mutation. */
export function useThoughtDraft() {
  const [initial] = useState(restore)
  const [draft, setDraft] = useState(initial.draft)
  const [storageError, setStorageError] = useState(initial.error)
  function update(next: ThoughtDraft) {
    setDraft(next)
    try {
      if (next.text) sessionStorage.setItem(KEY, JSON.stringify({ version: 1, draft: next }))
      else sessionStorage.removeItem(KEY)
      setStorageError('')
    } catch {
      setStorageError('This thought could not be checkpointed in this tab. Copy it before reloading; an older draft may return.')
    }
  }
  return { draft, update, storageError }
}
