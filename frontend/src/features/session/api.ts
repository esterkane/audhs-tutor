import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef } from 'react'
import { api, apiFetch, type Schemas, type SessionOut } from '../../lib/api'

export type BlockState = Schemas['BlockState']

export const REVIEW_BLOCK_TYPES = ['retrieval', 'interleaved_review']

/** The screen for a server phase. The plan complete → recap; nothing running → session. */
export function routeForPhase(
  state: Pick<BlockState, 'phase' | 'plan_complete' | 'block_status'> | null | undefined,
) {
  if (!state) return '/session'
  if (state.plan_complete) return '/recap'
  if (state.block_status !== 'running') return '/session'
  if (state.phase === 'review') return '/review'
  if (state.phase === 'recap') return '/recap'
  return '/session'
}

export function useSession(sessionId: string | null) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => api.session(sessionId!),
    enabled: !!sessionId,
  })
}

export function useCurrentSession() {
  return useQuery({ queryKey: ['session-current'], queryFn: () => api.current() })
}

export function useCheckpoint() {
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string
      body: { phase?: string; skill_id?: string | null; block_index?: number }
    }) => api.checkpoint(id, body),
  })
}

export function useStartSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['session-start'],
    mutationFn: api.startSession,
    onSuccess: (s) => qc.setQueryData(['session-current'], s),
  })
}

export function useEndSession() {
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string
      body: { energy_after: number; self_report: number; notes?: string }
    }) => api.endSession(id, body),
  })
}

/**
 * Block transitions are server-authoritative (kernel/blocks.py): every call returns the new
 * BlockState, which is written straight into the cached session so the UI never renders a stale
 * block index. `next` is idempotent on `from_index`, so a double-click cannot advance twice.
 */
export function useBlockTransition(sessionId: string | null) {
  const qc = useQueryClient()
  // one transition at a time: a second click while the first request is in flight gets the same
  // promise (React state alone updates too late to stop a synchronous double-click)
  const inFlight = useRef<Promise<BlockState> | null>(null)
  const post = (path: string) => (body: Record<string, unknown>) =>
    apiFetch<BlockState>(`/api/plan/blocks/${path}`, {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, ...body }),
    })
  const onSuccess = (state: BlockState) => {
    if (sessionId)
      qc.setQueryData<SessionOut>(['session', sessionId], (old) => (old ? { ...old, state } : old))
    void qc.invalidateQueries({ queryKey: ['session-current'] })
  }
  const start = useMutation({ mutationFn: post('start'), onSuccess })
  const next = useMutation({ mutationFn: post('next'), onSuccess })
  const end = useMutation({ mutationFn: post('end'), onSuccess })
  const extend = useMutation({ mutationFn: post('extend'), onSuccess })
  const once = (run: () => Promise<BlockState>) => {
    if (inFlight.current) return inFlight.current
    const p = run().finally(() => {
      inFlight.current = null
    })
    inFlight.current = p
    return p
  }
  return {
    start: (index: number) => once(() => start.mutateAsync({ index })),
    next: (body: {
      from_index: number | null
      reason?: string
      grasp_passed?: boolean
      actual_min?: number
    }) => once(() => next.mutateAsync(body)),
    end: (body: { index: number; reason?: string; switched_early?: boolean; grasp_passed?: boolean }) =>
      once(() => end.mutateAsync(body)),
    extend: (index: number, minutes = 5) => once(() => extend.mutateAsync({ index, minutes })),
    pending: start.isPending || next.isPending || end.isPending || extend.isPending,
    error: (start.error ?? next.error ?? end.error ?? extend.error) as Error | null,
  }
}

/** Plan helpers for Home's "which first?" offer. */
export function firstIndex(plan: Array<{ type: string }>, pred: (t: string) => boolean): number | null {
  const i = plan.findIndex((b) => pred(b.type))
  return i >= 0 ? i : null
}
