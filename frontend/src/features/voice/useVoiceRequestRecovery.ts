import { useCallback, useEffect, useRef, useState } from 'react'
import { apiFetch, type Schemas } from '../../lib/api'

export const voiceRequestKey = (scope: string) => `voice-request:v1:${scope}`
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/** Persist identity before sending. Lookup is read-only and never opens a voice connection. */
export function useVoiceRequestRecovery(scope: string, sessionId: string) {
  const key = voiceRequestKey(scope)
  const [loaded] = useState(() => {
    try {
      const id = sessionStorage.getItem(key)
      if (id !== null && !uuid.test(id)) throw new Error()
      return { id, error: '' }
    } catch {
      return { id: null, error: 'Voice request recovery could not read this tab’s storage.' }
    }
  })
  const restoreBlocked = useRef(!!loaded.error)
  const controller = useRef<AbortController | null>(null)
  const [pending, setPending] = useState(loaded.id)
  const current = useRef(loaded.id)
  const [error, setError] = useState(loaded.error)
  const [memoryOnly, setMemoryOnly] = useState(false)
  const [checking, setChecking] = useState(false)
  const [result, setResult] = useState<Schemas['VoiceResultOut'] | null>(null)
  const generation = useRef(0)
  useEffect(() => () => { generation.current++; controller.current?.abort() }, [])
  const begin = useCallback((id: string) => {
    if (current.current || (restoreBlocked.current && !memoryOnly)) return false
    if (!memoryOnly) {
      try { sessionStorage.setItem(key, id) }
      catch {
        setError('The request was not sent: its recovery identity could not be saved. You can explicitly continue for this page only.')
        return false
      }
    }
    current.current = id
    setPending(id)
    setResult(null)
    setError('')
    return true
  }, [key, memoryOnly])
  const discard = useCallback(() => {
    try { sessionStorage.removeItem(key) }
    catch {
      if (!memoryOnly) {
        setError('The recovery request could not be cleared. Keep your text and try again, or continue for this page only.')
        return false
      }
    }
    generation.current++
    controller.current?.abort()
    restoreBlocked.current = false
    current.current = null
    setPending(null)
    setChecking(false)
    setResult(null)
    setError('')
    return true
  }, [key, memoryOnly])
  const finish = useCallback((id: string) => {
    if (current.current === id) discard()
  }, [discard])
  const check = useCallback(async () => {
    const id = current.current
    if (!id) return
    const attempt = ++generation.current
    controller.current?.abort()
    const abort = new AbortController()
    controller.current = abort
    let deadline: ReturnType<typeof setTimeout> | undefined
    setChecking(true)
    setError('')
    try {
      const value = await Promise.race([
        apiFetch<Schemas['VoiceResultOut']>(
          `/api/voice/requests/${encodeURIComponent(id)}?session_id=${encodeURIComponent(sessionId)}`,
          { signal: abort.signal },
        ),
        new Promise<never>((_, reject) => {
          deadline = setTimeout(() => { abort.abort(); reject(new Error('Lookup timed out')) }, 15000)
        }),
      ])
      if (attempt !== generation.current || current.current !== id) return
      if (value.request_id !== id) throw new Error('Mismatched result')
      setResult(value)
      return value
    } catch {
      if (attempt === generation.current)
        setError('Could not check the saved voice result. Your received text and draft are kept; try checking again.')
    } finally {
      clearTimeout(deadline)
      if (attempt === generation.current) setChecking(false)
    }
  }, [sessionId])
  return { pending, error, memoryOnly, checking, result, begin, finish, discard, check,
    useMemoryOnly: () => { setMemoryOnly(true); setError('') } }
}
