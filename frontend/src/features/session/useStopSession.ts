import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type SessionOut } from '../../lib/api'
import { useMode } from '../../stores/mode'

export function useStopSession(sessionId: string, onRecapSaved?: (session: SessionOut) => void) {
  const nav = useNavigate()
  const qc = useQueryClient()
  const active = useRef(false)
  const pendingCleanup = useRef(new Set<() => void>())
  useEffect(() => {
    active.current = true
    const cleanups = pendingCleanup.current
    return () => { active.current = false; cleanups.forEach(cleanup => cleanup()); cleanups.clear() }
  }, [sessionId])
  return useMutation({
    mutationFn: (body?: Parameters<typeof api.endSession>[1]) => api.endSession(sessionId, body ?? {}),
    onMutate: () => {
      const key = window.history.state?.key
      const url = window.location.href
      let moved = false
      const onHistoryMove = () => { moved = true }
      window.addEventListener('popstate', onHistoryMove)
      const cleanup = () => {
        moved = true
        window.removeEventListener('popstate', onHistoryMove)
        pendingCleanup.current.delete(cleanup)
      }
      pendingCleanup.current.add(cleanup)
      return { endedSessionId: sessionId, cleanup,
        stillHere: () => !moved && window.history.state?.key === key && window.location.href === url }
    },
    onSuccess: (result, body, intent) => {
      const endedId = intent.endedSessionId
      const currentId = useMode.getState().sessionId
      if (currentId === endedId) useMode.getState().reset()
      qc.setQueryData<SessionOut | null>(['session-current'], current =>
        current?.id === endedId ? null : current,
      )
      void qc.invalidateQueries({ queryKey: ['session', endedId] })
      void qc.invalidateQueries({ queryKey: ['session-current'] })
      // Ending still commits after leaving, but its response cannot own a newer view/session.
      if (active.current && intent.stillHere() && sessionId === endedId && (!currentId || currentId === endedId)) {
        if (body !== undefined && onRecapSaved) onRecapSaved(result)
        else nav('/')
      }
    },
    onSettled: (_result, _error, _variables, intent) => intent?.cleanup(),
  })
}
