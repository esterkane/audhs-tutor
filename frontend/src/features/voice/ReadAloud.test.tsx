import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { ReadAloud } from './ReadAloud'

const audio = vi.hoisted(() => ({ enqueue: vi.fn(), close: vi.fn(), unlock: vi.fn(async () => {}) }))
vi.mock('./audio', () => ({
  Player: class {
    onIdle = null
    enqueue = audio.enqueue
    close = audio.close
    unlock = audio.unlock
    pending() {
      return 1
    }
  },
  b64ToPcm16: () => new Int16Array([0]),
}))
afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})
it('never autoplays and ignores a synthesis response after Stop audio', async () => {
  let resolve!: (r: Response) => void
  const fetcher = vi.fn(
    () =>
      new Promise<Response>((done) => {
        resolve = done
      }),
  )
  vi.stubGlobal('fetch', fetcher)
  renderApp(<ReadAloud text="A short explanation." />)
  expect(fetcher).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Listen to explanation' }))
  await waitFor(() => expect(fetcher).toHaveBeenCalledOnce())
  fireEvent.click(screen.getByRole('button', { name: 'Stop audio' }))
  await act(async () => resolve(jsonResponse({ pcm16_b64: 'AAA=', sample_rate: 24000 })))
  expect(audio.enqueue).not.toHaveBeenCalled()
  expect(audio.close).toHaveBeenCalled()
  expect(screen.getByRole('button', { name: 'Listen to explanation' })).toBeVisible()
})
it('closing the explanation stops playback and aborts a pending request', async () => {
  let signal: AbortSignal | undefined
  vi.stubGlobal(
    'fetch',
    vi.fn((_url: string, init: RequestInit) => {
      signal = init.signal as AbortSignal
      return new Promise(() => {})
    }),
  )
  const { unmount } = renderApp(<ReadAloud text="Read this only on request." />)
  fireEvent.click(screen.getByRole('button', { name: 'Listen to explanation' }))
  await waitFor(() => expect(signal).toBeDefined())
  unmount()
  expect(signal?.aborted).toBe(true)
  expect(audio.close).toHaveBeenCalled()
})

it('speaks the question and resets playback when selected content changes', async () => {
  const fetcher = vi.fn<(url: string, init: RequestInit) => Promise<Response>>(async () =>
    jsonResponse({ pcm16_b64: 'AAA=', sample_rate: 24000 }),
  )
  vi.stubGlobal('fetch', fetcher)
  const view = renderApp(<ReadAloud text="Why does missingness matter?" label="Listen to question" />)
  fireEvent.click(screen.getByRole('button', { name: 'Listen to question' }))
  await waitFor(() => expect(audio.enqueue).toHaveBeenCalled())
  expect(JSON.parse(fetcher.mock.calls[0][1].body as string).text).toBe('Why does missingness matter?')
  view.rerender(
    <ReadAloud text="Why does missingness matter? Hint: compare groups." label="Listen to question" />,
  )
  expect(audio.close).toHaveBeenCalled()
  expect(screen.getByRole('button', { name: 'Listen to question' })).toBeVisible()
  expect(fetcher).toHaveBeenCalledOnce()
})
