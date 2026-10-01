import { useCallback, useEffect, useRef, useState } from 'react'
import type { ResponseStatus } from './TutorResponseStatus'
import { streamTurn, type TurnDone, type TurnMeta, type TurnRequest } from '../../lib/api'

type Status = ResponseStatus
type Answer = { text: string; meta: TurnMeta | null; done: TurnDone | null; status: Status }
type State = Answer & { error: string | null; previous: Answer | null; startedAt: number | null }
const empty: State = {
  text: '',
  meta: null,
  done: null,
  error: null,
  status: 'idle',
  previous: null,
  startedAt: null,
}

export function useTutorStream(idleMs = 60_000) {
  const [state, setState] = useState<State>(empty)
  const snapshot = useRef<State>(empty)
  const active = useRef<{ ctl: AbortController; cancel: () => void } | null>(null)
  const lastRequest = useRef<TurnRequest | null>(null)
  const update = useCallback((patch: Partial<State>) => {
    snapshot.current = { ...snapshot.current, ...patch }
    setState(snapshot.current)
  }, [])
  useEffect(
    () => () => {
      active.current?.cancel()
      active.current = null
    },
    [],
  )

  const run = useCallback(
    async (req: TurnRequest) => {
      active.current?.cancel()
      const ctl = new AbortController()
      let timer: ReturnType<typeof setTimeout> | undefined
      let terminal = false
      const own = {
        ctl,
        cancel: () => {
          clearTimeout(timer)
          ctl.abort()
        },
      }
      active.current = own
      const current = () => active.current === own && !ctl.signal.aborted && !terminal
      const old = snapshot.current
      const previous: Answer | null = old.text
        ? {
            text: old.text,
            meta: old.meta,
            done: old.done,
            status: old.status === 'streaming' ? 'stopped' : old.status,
          }
        : old.previous
      lastRequest.current = { ...req }
      update({ ...empty, previous, status: 'streaming', startedAt: performance.now() })
      const fail = (message: string) => {
        if (!current()) return
        terminal = true
        clearTimeout(timer)
        update({ error: message, status: snapshot.current.text ? 'partial' : 'failed' })
        ctl.abort()
      }
      const touch = () => {
        clearTimeout(timer)
        timer = setTimeout(
          () => fail('No response arrived for a minute. Your received text is kept; retry when ready.'),
          idleMs,
        )
      }
      touch()
      try {
        await streamTurn(
          req,
          {
            onMeta: (meta) => {
              if (current()) {
                touch()
                update({ meta })
              }
            },
            onToken: (token) => {
              if (current()) {
                touch()
                update({ text: snapshot.current.text + token })
              }
            },
            onDone: (done) => {
              if (!current()) return
              terminal = true
              clearTimeout(timer)
              update({ done, status: done.outcome === 'partial' ? 'partial' : 'complete' })
            },
            onError: (e) => fail(e.message),
          },
          ctl.signal,
        )
        if (current()) fail('The response ended before completion. Your received text is kept.')
      } catch (e) {
        if (current()) fail((e as Error).message || 'The response was interrupted.')
      } finally {
        clearTimeout(timer)
        if (active.current === own) active.current = null
      }
    },
    [idleMs, update],
  )

  const stop = useCallback(() => {
    if (!active.current) return
    active.current.cancel()
    active.current = null
    if (snapshot.current.status === 'streaming') update({ status: 'stopped' })
  }, [update])
  const retry = useCallback(() => (lastRequest.current ? run(lastRequest.current) : Promise.resolve()), [run])
  return { ...state, busy: state.status === 'streaming', run, stop, retry }
}
