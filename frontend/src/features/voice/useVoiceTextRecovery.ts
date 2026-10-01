import { useCallback, useEffect, useRef, useState } from 'react'

export type VoiceText = { draft: string; transcript: string; answer: string; interrupted: boolean }
const blank: VoiceText = { draft: '', transcript: '', answer: '', interrupted: false }
const limit = 250000
export const voiceTextKey = (scope: string) => `voice-text:v1:${scope}`

/** Text only. Socket, microphone, audio buffers and completion receipts are never restored. */
export function useVoiceTextRecovery(scope: string) {
  const key = voiceTextKey(scope)
  const [loaded] = useState(() => {
    try {
      const raw = sessionStorage.getItem(key)
      if (!raw) return { value: blank, restored: false, error: '' }
      if (raw.length > limit) throw new Error('Oversized voice text')
      const value = JSON.parse(raw) as VoiceText
      if (
        !value ||
        !['draft', 'transcript', 'answer'].every((k) => typeof value[k as 'draft'] === 'string') ||
        typeof value.interrupted !== 'boolean'
      )
        throw new Error('Invalid voice text')
      return { value, restored: true, error: '' }
    } catch {
      return {
        value: blank,
        restored: false,
        error: 'Voice text could not be restored from this tab. Keep a copy before leaving.',
      }
    }
  })
  const [error, setError] = useState(loaded.error)
  const snapshot = useRef(loaded.value)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const cleared = useRef(false)
  const flush = useCallback(() => {
    clearTimeout(timer.current)
    timer.current = undefined
    if (cleared.current) return
    try {
      const raw = JSON.stringify(snapshot.current)
      if (raw.length > limit) throw new Error('Oversized voice text')
      sessionStorage.setItem(key, raw)
    } catch {
      setError(
        'Voice text is kept on this page but could not be saved for reload. Keep a copy before leaving.',
      )
    }
  }, [key])
  const save = useCallback(
    (value: VoiceText) => {
      snapshot.current = value
      if (!timer.current) timer.current = setTimeout(flush, 250)
    },
    [flush],
  )
  const clear = useCallback(() => {
    try {
      sessionStorage.removeItem(key)
    } catch {
      setError(
        'Saved voice text could not be cleared. The panel stays open so you can keep a copy and try again.',
      )
      return false
    }
    cleared.current = true
    clearTimeout(timer.current)
    return true
  }, [key])
  useEffect(() => {
    window.addEventListener('pagehide', flush)
    return () => {
      window.removeEventListener('pagehide', flush)
      flush()
    }
  }, [flush])
  return { initial: loaded.value, restored: loaded.restored, error, save, clear }
}
