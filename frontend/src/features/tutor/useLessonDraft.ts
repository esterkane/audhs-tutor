import { useRef, useState, type SetStateAction } from 'react'

/** Scope is fixed by the parent panel key: session, block instance and skill. */
export function useLessonDraft(scope: string) {
  const key = `lesson-draft:v1:${scope}`
  const [initial] = useState(() => {
    try {
      const text = sessionStorage.getItem(key) ?? ''
      if (text.length > 100000) throw new Error('Oversized draft')
      return { text, error: '' }
    } catch {
      return { text: '', error: 'Your lesson draft could not be restored. Keep a copy before leaving.' }
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
      setError('')
    } catch {
      setError('Your draft is kept on this page but could not be saved for reload. Keep a copy.')
    }
  }
  return { input, setInput, error }
}
