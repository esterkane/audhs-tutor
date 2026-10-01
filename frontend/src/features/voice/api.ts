import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'

export type ReadinessOut = Schemas['ReadinessOut']
export type VerifyOut = Schemas['VerifyOut']
export type MicTestOut = Schemas['MicTestOut']

export function useVoiceReadiness() {
  return useQuery({
    queryKey: ['voice', 'readiness'],
    queryFn: () => apiFetch<ReadinessOut>('/api/voice/readiness'),
  })
}

export function useVoiceActions() {
  const qc = useQueryClient()
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['voice'] })
    void qc.invalidateQueries({ queryKey: ['preferences'] })
  }
  const verify = useMutation({
    mutationFn: () => apiFetch<VerifyOut>('/api/voice/verify', { method: 'POST' }),
  })
  const testMic = useMutation({
    mutationFn: async (wav: Blob) => {
      const res = await fetch('/api/voice/test-mic', {
        method: 'POST',
        body: wav,
        headers: { 'Content-Type': 'audio/wav' },
      })
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { error?: { message?: string } }
        throw new Error(body.error?.message ?? `${res.status} ${res.statusText}`)
      }
      return (await res.json()) as MicTestOut
    },
  })
  const activate = useMutation({
    mutationFn: (enabled: boolean) =>
      apiFetch<ReadinessOut>('/api/voice/activate', { method: 'POST', body: JSON.stringify({ enabled }) }),
    onSuccess: invalidate,
  })
  return { verify, testMic, activate }
}
