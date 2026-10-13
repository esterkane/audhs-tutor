import { useState } from 'react'

type Draft = { notes: string; energyAfter: number | null; recall: number | null }
const empty = (): Draft => ({ notes: '', energyAfter: null, recall: null })
export const recapDraftKey = (id: string) => `audhs-recap:v1:${id}`
const warning = 'Your recap draft could not be stored in this browser tab. Keep a copy before leaving or reloading.'
const rating = (value: unknown) => value === null || (Number.isInteger(value) && Number(value) >= 1 && Number(value) <= 5)
function load(id: string | null) {
  try {
    const raw = id ? sessionStorage.getItem(recapDraftKey(id)) : null
    if (!raw) return { id, draft: empty(), error: '', unreadable: false }
    const value = JSON.parse(raw)
    if (value.version !== 1 || typeof value.notes !== 'string' || !rating(value.energyAfter) || !rating(value.recall)) throw new Error('Invalid draft')
    return { id, draft: { notes: value.notes, energyAfter: value.energyAfter, recall: value.recall } as Draft, error: '', unreadable: false }
  } catch {
    return { id, draft: empty(), error: 'An earlier recap draft could not be read. Keep a copy of new notes before leaving; the earlier stored draft will not be overwritten.', unreadable: true }
  }
}

/** Tab-lifetime recovery only; never submits ratings or changes learning evidence. */
export function useRecapDraft(id: string | null) {
  const [state, setState] = useState(() => load(id))
  if (state.id !== id) setState(load(id))
  function edit(change: Partial<Draft>) {
    const draft = { ...state.draft, ...change }
    let error = state.error
    if (id && !state.unreadable) {
      try {
        sessionStorage.setItem(recapDraftKey(id), JSON.stringify({ version: 1, ...draft }))
        error = ''
      } catch { error = warning }
    }
    setState({ ...state, draft, error })
  }
  function clear() {
    if (!id || state.unreadable) return
    try { sessionStorage.removeItem(recapDraftKey(id)) } catch { /* Retain recoverable draft if deletion is denied. */ }
  }
  return { ...state.draft, error: state.error, edit, clear }
}
