import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../../lib/api'
import { useMode } from '../../stores/mode'

export function useStopSession(sessionId: string) {
  const nav = useNavigate()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.endSession(sessionId, {}),
    onSuccess: () => {
      useMode.getState().reset()
      qc.setQueryData(['session-current'], null)
      void qc.invalidateQueries({ queryKey: ['session', sessionId] })
      nav('/')
    },
  })
}
