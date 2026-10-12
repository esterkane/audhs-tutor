import { useRef, useState, type SetStateAction } from 'react'

// Only failed browser writes live here; never persisted or submitted automatically.
// The existing session/block/skill scope prevents recovery into a different activity.
const unsaved = new Map<string, string>()
const reloadWarning = 'Your draft is kept while navigating in this tab but could not be saved for reload. Keep a copy.'

/** Scope is fixed by the parent panel key: session, block instance and skill. */
export function useLessonDraft(scope: string, label = 'lesson') {
  const key = `lesson-draft:v1:${scope}`
  const [initial] = useState(() => {
    if (unsaved.has(key)) return { text: unsaved.get(key)!, error: reloadWarning }
    try {
      const text = sessionStorage.getItem(key) ?? ''
      if (text.length > 100000) throw new Error('Oversized draft')
      return { text, error: '' }
    } catch {
      return { text: '', error: `Your ${label} draft could not be restored. Keep a copy before leaving.` }
    }
  })
  const [input, update] = useState(initial.text)
  const current = useRef(initial.text)
  const [error, setError] = useState(initial.error)
  function setInput(value: SetStateAction<string>) {
    const next = typeof value === 'function' ? value(current.current) : value
    current.current = next
    update(next)
    try {
      if (next.length > 100000) throw new Error('Oversized draft')
      sessionStorage.setItem(key, next)
      unsaved.delete(key)
      setError('')
    } catch {
      unsaved.set(key, next)
      setError(reloadWarning)
    }
  }
  return { input, setInput, error }
}
