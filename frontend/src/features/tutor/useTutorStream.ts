import { useCallback, useEffect, useRef, useState } from 'react'
import { streamTurn, type TurnDone, type TurnMeta, type TurnRequest } from '../../lib/api'

export function useTutorStream() {
  const [text, setText] = useState('')
  const [meta, setMeta] = useState<TurnMeta | null>(null)
  const [done, setDone] = useState<TurnDone | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const abort = useRef<AbortController | null>(null)

  useEffect(() => () => abort.current?.abort(), [])

  const run = useCallback(async (req: TurnRequest) => {
    abort.current?.abort()
    const ctl = new AbortController()
    abort.current = ctl
    setText('')
    setMeta(null)
    setDone(null)
    setError(null)
    setBusy(true)
    try {
      await streamTurn(
        req,
        {
          onMeta: setMeta,
          onToken: (t) => setText((prev) => prev + t),
          onDone: setDone,
          onError: (e) => setError(e.message),
        },
        ctl.signal,
      )
    } catch (e) {
      if ((e as Error).name !== 'AbortError') setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }, [])

  const stop = useCallback(() => abort.current?.abort(), [])
  return { text, meta, done, error, busy, run, stop }
}
