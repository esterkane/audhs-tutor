import { useLayoutEffect, useRef, useState } from 'react'

export const draftRecoveryKey = (id: string) => `curriculum-edit:v1:${id}`
const LIMIT = 1_000_000
export type DraftRecovery = {
  version: 1
  draftId: string
  baseVersion: number
  baseText: string
  text: string
  savedAt: string
}

function load(id: string): { value: DraftRecovery | null; error: string } {
  try {
    const raw = sessionStorage.getItem(draftRecoveryKey(id))
    if (raw === null) return { value: null, error: '' }
    if (raw.length > 2 * LIMIT + 1000) throw new Error('Oversized recovery')
    const value = JSON.parse(raw) as DraftRecovery
    if (
      !value ||
      value.version !== 1 ||
      value.draftId !== id ||
      !Number.isInteger(value.baseVersion) ||
      value.baseVersion < 1 ||
      typeof value.baseText !== 'string' ||
      value.baseText.length > LIMIT ||
      typeof value.text !== 'string' ||
      value.text.length > LIMIT ||
      typeof value.savedAt !== 'string' ||
      value.savedAt.length > 64 ||
      !Number.isFinite(Date.parse(value.savedAt))
    )
      throw new Error('Invalid recovery')
    return { value, error: '' }
  } catch {
    return {
      value: null,
      error:
        'Earlier recovery text could not be read. Your current text stays on this page. Keep a copy before leaving.',
    }
  }
}

/** Parent editor is keyed by the server-owned draft ID. This never writes to the API.
 * Tab lifetime is the retention boundary; no timed purge or cross-tab merging.
 */
export function useDraftRecovery(id: string, version: number, canonical: string) {
  const [initial] = useState(() => load(id))
  const empty = (): DraftRecovery => ({
    version: 1,
    draftId: id,
    baseVersion: version,
    baseText: canonical,
    text: canonical,
    savedAt: new Date().toISOString(),
  })
  const [state, setState] = useState<DraftRecovery>(() => initial.value ?? empty())
  const [error, setError] = useState(initial.error)
  const [restored, setRestored] = useState(
    Boolean(initial.value && initial.value.text !== initial.value.baseText),
  )
  const unreadable = useRef(Boolean(initial.error))
  const current = useRef(state)
  useLayoutEffect(() => { current.current = state }, [state])
  const dirty = state.text !== state.baseText
  if (
    !dirty &&
    version >= state.baseVersion &&
    (state.baseVersion !== version || state.baseText !== canonical)
  ) {
    const next = empty()
    setState(next)
    setRestored(false)
  }

  function persist(next: DraftRecovery, explicit = false) {
    if (unreadable.current && !explicit) return // Do not silently replace unreadable earlier work.
    try {
      if (next.text.length > LIMIT || next.baseText.length > LIMIT) throw new Error('Oversized recovery')
      if (next.text === next.baseText) sessionStorage.removeItem(draftRecoveryKey(id))
      else sessionStorage.setItem(draftRecoveryKey(id), JSON.stringify(next))
      unreadable.current = false
      setError('')
    } catch {
      setError(
        'Recovery storage could not be updated. Your current text stays on this page. Keep a copy before leaving or reloading.',
      )
    }
  }

  function edit(text: string) {
    const next = { ...current.current, text, savedAt: new Date().toISOString() }
    current.current = next
    setState(next)
    persist(next)
  }
  function reset(text: string, baseVersion: number) {
    const next: DraftRecovery = {
      version: 1,
      draftId: id,
      text,
      baseText: text,
      baseVersion,
      savedAt: new Date().toISOString(),
    }
    current.current = next
    setState(next)
    setRestored(false)
    persist(next, true) // Explicit discard or acknowledged server save.
  }
  return {
    text: state.text,
    baseText: state.baseText,
    baseVersion: state.baseVersion,
    dirty,
    restored,
    error,
    edit,
    reset,
    saveRecovery: () => persist(current.current, true),
  }
}
