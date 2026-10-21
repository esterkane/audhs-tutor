import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, expect, it, vi } from 'vitest'
import { useAcceptedKnowledge } from './acceptedKnowledgeApi'
import { useDraftActions } from './api'
import { jsonResponse } from '../../test/utils'

function Harness() {
  const reading = useAcceptedKnowledge('skill')
  const { publish } = useDraftActions()
  return <><p>{reading.isPending ? 'Loading' : reading.isError ? 'Failed' : reading.data?.explanation}</p>
    <button onClick={() => void reading.refetch()}>Retry</button>
    <button onClick={() => publish.mutate({id:'draft', expected_version:1})}>Activate revision</button></>
}
function setup() {
  const client = new QueryClient({defaultOptions:{queries:{retry:false, staleTime:Infinity}}})
  const view = render(<QueryClientProvider client={client}><Harness /></QueryClientProvider>)
  return {client, ...view}
}
const material = (explanation: string) => ({explanation, draft_id:'draft', title:'Notes', objective:'Goal',
  worked_example:'Example', question:'Question', notes:'Notes', sources:[], learning_object_version:1})
afterEach(() => {vi.useRealTimers(); vi.unstubAllGlobals()})

it('bounds a stalled transport and retries explicitly without another automatic request', async () => {
  vi.useFakeTimers()
  const fetcher = vi.fn().mockImplementationOnce(() => new Promise<Response>(() => {}))
    .mockResolvedValue(jsonResponse(material('Recovered accepted text')))
  vi.stubGlobal('fetch', fetcher)
  setup()
  await act(async () => {await vi.advanceTimersByTimeAsync(15010)})
  expect(screen.getByText('Failed')).toBeVisible()
  expect(fetcher).toHaveBeenCalledTimes(1)
  expect(fetcher.mock.calls[0][1].signal.aborted).toBe(true)
  fireEvent.click(screen.getByRole('button',{name:'Retry'}))
  await act(async () => {await vi.advanceTimersByTimeAsync(10)})
  expect(screen.getByText('Recovered accepted text')).toBeVisible()
  expect(fetcher).toHaveBeenCalledTimes(2)
})

it('cancels the accepted-material read when leaving the lesson', async () => {
  const fetcher = vi.fn(() => new Promise<Response>(() => {}))
  vi.stubGlobal('fetch', fetcher)
  const view = setup()
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))
  const signal = (fetcher.mock.calls[0] as unknown as [string, RequestInit])[1].signal!
  view.unmount()
  expect(signal.aborted).toBe(true)
})

it('refreshes even a fresh cached accepted lesson after activating a revision', async () => {
  let activated = false
  const fetcher = vi.fn(async (url: string) => {
    if (url.endsWith('/publish')) {activated = true; return jsonResponse({})}
    return jsonResponse(material(activated ? 'Revised accepted text' : 'Original accepted text'))
  })
  vi.stubGlobal('fetch', fetcher)
  setup()
  expect(await screen.findByText('Original accepted text')).toBeVisible()
  fireEvent.click(screen.getByRole('button',{name:'Activate revision'}))
  expect(await screen.findByText('Revised accepted text')).toBeVisible()
  expect(fetcher).toHaveBeenCalledTimes(3)
})
