import { useLessonRequestRecovery, type PendingTutorRequest } from '../playground/useRequestRecovery'
import { cacheWarning, readTextCache, writeTextCache } from './streamCache'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { ResponseStatus } from './TutorResponseStatus'
import { streamTurn, type TurnDone, type TurnMeta, type TurnRequest } from '../../lib/api'

type Status = ResponseStatus
type Answer = { text: string; meta: TurnMeta | null; done: TurnDone | null; status: Status }
type State = Answer & {
  error: string | null
  previous: Answer | null
  startedAt: number | null
  restored: boolean
}
const empty: State = {
  restored: false,
  text: '',
  meta: null,
  done: null,
  error: null,
  status: 'idle',
  previous: null,
  startedAt: null,
}

export function useTutorStream(idleMs = 60_000, scope?: string) {
  const recovery = useLessonRequestRecovery(`lesson:${scope ?? 'ephemeral'}`, scope !== undefined)
  const [cached] = useState(() => (scope === undefined ? { value: null, error: '' } : readTextCache(scope)))
  const [initial] = useState<State>(() =>
    cached.value
      ? {
          ...empty,
          restored: true,
          text: cached.value.text,
          done: cached.value.done ?? null,
          status: cached.value.status === 'streaming' ? 'partial' : cached.value.status,
          previous: cached.value.previousText
            ? { text: cached.value.previousText, meta: null, done: null, status: 'stopped' }
            : null,
        }
      : empty,
  )
  const [state, setState] = useState<State>(initial)
  const [storageError, setStorageError] = useState(cached.error)
  const snapshot = useRef<State>(initial)
  const storageTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const active = useRef<{ ctl: AbortController; cancel: () => void } | null>(null)
  const flush = useCallback(() => {
    clearTimeout(storageTimer.current)
    storageTimer.current = undefined
    if (scope === undefined) return
    try {
      const warning = writeTextCache(scope, {
        text: snapshot.current.text,
        previousText: snapshot.current.previous?.text ?? null,
        status: snapshot.current.status,
        done:
          snapshot.current.status === 'complete' && snapshot.current.done?.outcome === 'ok'
            ? snapshot.current.done
            : null,
      })
      setStorageError(warning)
    } catch {
      setStorageError(cacheWarning)
    }
  }, [scope])
  const update = useCallback(
    (patch: Partial<State>) => {
      snapshot.current = { ...snapshot.current, ...patch }
      setState(snapshot.current)
      if (snapshot.current.status !== 'streaming') flush()
      else if (!storageTimer.current) storageTimer.current = setTimeout(flush, 250)
    },
    [flush],
  )
  useEffect(() => {
    window.addEventListener('pagehide', flush)
    return () => {
      window.removeEventListener('pagehide', flush)
      flush()
    }
  }, [flush])
  useEffect(
    () => () => {
      active.current?.cancel()
      active.current = null
    },
    [],
  )

  const execute = useCallback(
    async (pending: PendingTutorRequest<TurnRequest>) => {
      const req = pending.body
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
              update({
                done,
                text: done.outcome === 'partial' ? snapshot.current.text : done.text,
                status: done.outcome === 'partial' ? 'partial' : 'complete',
              })
              recovery.accept(pending.key)
            },
            onError: (e) => fail(e.message),
          },
          ctl.signal,
          scope === undefined ? undefined : pending.key,
        )
        if (current()) fail('The response ended before completion. Your received text is kept.')
      } catch (e) {
        if (current()) fail((e as Error).message || 'The response was interrupted.')
      } finally {
        clearTimeout(timer)
        if (active.current === own) active.current = null
      }
    },
    [idleMs, update, recovery, scope],
  )

  const stop = useCallback(() => {
    if (!active.current) return
    active.current.cancel()
    active.current = null
    if (snapshot.current.status === 'streaming') update({ status: 'stopped' })
  }, [update])
  const run = useCallback(
    async (req: TurnRequest) => {
      try {
        if (scope === undefined) recovery.discard()
        const pending = recovery.prepare(req, {
          snapshot: scope ?? '',
          submitted: req.text,
          display: req.text,
          mode: 'explicit',
        })
        await execute(pending)
      } catch (e) {
        update({ error: (e as Error).message })
      }
    },
    [execute, recovery, scope, update],
  )
  const retry = useCallback(
    () => (recovery.pending ? execute(recovery.pending) : Promise.resolve()),
    [execute, recovery],
  )
  return { ...state, busy: state.status === 'streaming', run, stop, retry, recovery, storageError }
}
