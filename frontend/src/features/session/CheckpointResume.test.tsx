import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse } from '../../test/utils'
import type { SessionOut } from '../../lib/api'
import { useCheckpoint } from './api'

afterEach(() => vi.unstubAllGlobals())

it('publishes confirmed assessment phase for an immediate cached resume', async () => {
  const qc = new QueryClient()
  const current = {
    id: 's1', checkpoint: {},
    state: { block_id: 's1:2', block_index: 2, phase: 'teach' },
  } as SessionOut
  qc.setQueryData(['session', 's1'], current)
  vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({
    block_id: 's1:2', block_index: 2, phase: 'assess', skill_id: 'k1',
  })))
  function ChangePhase() {
    const mutation = useCheckpoint()
    return <button onClick={() => mutation.mutate({ id: 's1', body: { phase: 'assess', block_index: 2 } })}>Try question</button>
  }
  render(<QueryClientProvider client={qc}><ChangePhase /></QueryClientProvider>)
  fireEvent.click(screen.getByRole('button', { name: 'Try question' }))
  await waitFor(() => expect(qc.getQueryData<SessionOut>(['session', 's1'])?.state.phase).toBe('assess'))
  expect(qc.getQueryData<SessionOut>(['session', 's1'])?.checkpoint?.phase).toBe('assess')
  // A late checkpoint response from the old block must not undo an advance.
  qc.setQueryData(['session', 's1'], { ...current, state: { ...current.state, block_id: 's1:3', phase: 'recap' } })
  fireEvent.click(screen.getByRole('button', { name: 'Try question' }))
  await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledTimes(2))
  expect(qc.getQueryData<SessionOut>(['session', 's1'])?.state.phase).toBe('recap')
})

it('ignores stale reads started during an in-flight checkpoint write', async () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const current = { id: 'race', checkpoint: {}, state: { block_id: 'race:0', phase: 'teach' } } as SessionOut
  qc.setQueryData(['session', 'race'], current)
  qc.setQueryData(['session-current'], current)
  let confirm!: () => void
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => { confirm = () => resolve(jsonResponse({ block_id: 'race:0', phase: 'assess' })) })))
  function Change() {
    const mutation = useCheckpoint()
    return <button onClick={() => mutation.mutate({ id: 'race', body: { phase: 'assess' } })}>Change phase</button>
  }
  render(<QueryClientProvider client={qc}><Change /></QueryClientProvider>)
  fireEvent.click(screen.getByRole('button', { name: 'Change phase' }))
  await waitFor(() => expect(confirm).toBeTypeOf('function'))
  let releaseCurrent!: () => void
  const currentRead = qc.fetchQuery({ queryKey: ['session-current'], queryFn: () => new Promise<SessionOut>(resolve => { releaseCurrent = () => resolve(current) }) }).catch(() => undefined)
  let releaseRead!: () => void
  const read = qc.fetchQuery({ queryKey: ['session', 'race'], queryFn: () => new Promise<SessionOut>(resolve => { releaseRead = () => resolve(current) }) }).catch(() => undefined)
  confirm()
  await waitFor(() => expect(qc.getQueryData<SessionOut>(['session', 'race'])?.state.phase).toBe('assess'))
  releaseRead()
  releaseCurrent()
  await Promise.all([read, currentRead])
  expect(qc.getQueryData<SessionOut>(['session', 'race'])?.state.phase).toBe('assess')
  expect(qc.getQueryData<SessionOut>(['session-current'])?.state.phase).toBe('assess')
})
