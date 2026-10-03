import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { AudioControls } from '../audio/AudioControls'
import { ReadAloud } from './ReadAloud'
import { useAudioSettings } from '../audio/settings'

const audio = vi.hoisted(() => ({
  pause: vi.fn(async () => {}),
  resume: vi.fn(async () => {}),
  enqueue: vi.fn(),
  close: vi.fn(),
  unlock: vi.fn(async () => {}),
  idle: null as (() => void) | null,
}))
vi.mock('./audio', () => ({
  Player: class {
    set onIdle(value: (() => void) | null) {
      audio.idle = value
    }
    get onIdle() {
      return audio.idle
    }
    pause = audio.pause
    resume = audio.resume
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
  useAudioSettings.setState({ muted: false, volume: 0.5 })
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

it('shows preparation separately from queued playback and explains silent output', async () => {
  let resolve!: (r: Response) => void
  vi.stubGlobal(
    'fetch',
    vi.fn(
      () =>
        new Promise<Response>((done) => {
          resolve = done
        }),
    ),
  )
  useAudioSettings.setState({ muted: true, volume: 0.5 })
  renderApp(<ReadAloud text="Explain the example." />)
  fireEvent.click(screen.getByRole('button', { name: 'Listen to explanation' }))
  expect(screen.getByText('Preparing audio…')).toBeVisible()
  expect(screen.getByText(/Audio is muted/)).toBeVisible()
  await waitFor(() => expect(resolve).toBeDefined())
  await act(async () => resolve(jsonResponse({ pcm16_b64: 'AAA=', sample_rate: 24000 })))
  expect(screen.getByText('Audio playback in progress.')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Stop audio' }))
  expect(screen.getByText('Audio stopped. Listen again starts from the beginning.')).toBeVisible()
  useAudioSettings.setState({ muted: false })
})

it('distinguishes a gap between passages from completion and releases finished playback', async () => {
  let second!: (r: Response) => void
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(jsonResponse({ pcm16_b64: 'AAA=', sample_rate: 24000 }))
    .mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          second = resolve
        }),
    )
  vi.stubGlobal('fetch', fetcher)
  renderApp(<ReadAloud text={'word '.repeat(250)} />)
  fireEvent.click(screen.getByRole('button', { name: 'Listen to explanation' }))
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
  act(() => audio.idle?.())
  expect(screen.getByText('Preparing the next passage…')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Stop audio' })).toBeVisible()
  await act(async () => second(jsonResponse({ pcm16_b64: 'AAA=', sample_rate: 24000 })))
  expect(screen.getByText('Audio playback in progress.')).toBeVisible()
  act(() => audio.idle?.())
  expect(screen.getByText('Audio finished.')).toBeVisible()
  expect(audio.close).toHaveBeenCalled()
  expect(screen.getByRole('button', { name: 'Listen to explanation' })).toBeVisible()
})
it('shows synthesis failure and allows retry without claiming playback', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Voice service unavailable')))
  renderApp(<ReadAloud text="Try listening." />)
  fireEvent.click(screen.getByRole('button', { name: 'Listen to explanation' }))
  await screen.findByText('Audio could not finish.')
  expect(screen.getByRole('alert')).toHaveTextContent('Voice service unavailable')
  expect(screen.getByRole('button', { name: 'Listen to explanation' })).toBeVisible()
})

it('keeps arriving speech paused and resumes without another synthesis request', async () => {
  let resolve!: (r: Response) => void
  const fetcher = vi.fn(
    () =>
      new Promise<Response>((done) => {
        resolve = done
      }),
  )
  vi.stubGlobal('fetch', fetcher)
  renderApp(<ReadAloud text="Pause this explanation." />)
  fireEvent.click(screen.getByRole('button', { name: 'Listen to explanation' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Pause audio' }))
  await screen.findByRole('button', { name: 'Resume audio' })
  await act(async () => resolve(jsonResponse({ pcm16_b64: 'AAA=', sample_rate: 24000 })))
  expect(screen.getByText('Audio paused. Resume continues from the same position.')).toBeVisible()
  expect(audio.pause).toHaveBeenCalledOnce()
  fireEvent.click(screen.getByRole('button', { name: 'Resume audio' }))
  await screen.findByRole('button', { name: 'Pause audio' })
  expect(audio.resume).toHaveBeenCalledOnce()
  expect(fetcher).toHaveBeenCalledOnce()
})
it('ignores a pending pause completion after Stop', async () => {
  let finish!: () => void
  audio.pause.mockImplementationOnce(
    () =>
      new Promise<void>((resolve) => {
        finish = resolve
      }),
  )
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse({ pcm16_b64: 'AAA=', sample_rate: 24000 })),
  )
  renderApp(<ReadAloud text="Stop while pausing." />)
  fireEvent.click(screen.getByRole('button', { name: 'Listen to explanation' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Pause audio' }))
  fireEvent.click(screen.getByRole('button', { name: 'Stop audio' }))
  await act(async () => finish())
  expect(screen.queryByRole('button', { name: 'Resume audio' })).not.toBeInTheDocument()
  expect(screen.getByText('Audio stopped. Listen again starts from the beginning.')).toBeVisible()
})

it('starting another reading stops the previous request and ignores its late response', async () => {
  const responses: ((r: Response) => void)[] = []
  const signals: AbortSignal[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((_url: string, init: RequestInit) => {
      signals.push(init.signal as AbortSignal)
      return new Promise<Response>((resolve) => responses.push(resolve))
    }),
  )
  renderApp(
    <>
      <ReadAloud text="Explanation." label="Read explanation" />
      <ReadAloud text="Question?" label="Read question" />
    </>,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Read explanation' }))
  await waitFor(() => expect(responses).toHaveLength(1))
  fireEvent.click(screen.getByRole('button', { name: 'Read question' }))
  await waitFor(() => expect(responses).toHaveLength(2))
  expect(signals[0].aborted).toBe(true)
  expect(signals[1].aborted).toBe(false)
  expect(screen.getByText('Audio stopped because another reading started.')).toBeVisible()
  await act(async () => responses[0](jsonResponse({ pcm16_b64: 'AAA=', sample_rate: 24000 })))
  expect(audio.enqueue).not.toHaveBeenCalled()
  await act(async () => responses[1](jsonResponse({ pcm16_b64: 'AAA=', sample_rate: 24000 })))
  expect(audio.enqueue).toHaveBeenCalledOnce()
})

it('shared controls pause, resume and stop the same reading without regenerating', async () => {
  const fetcher = vi.fn(async () => jsonResponse({ pcm16_b64: 'AAA=', sample_rate: 24000 }))
  vi.stubGlobal('fetch', fetcher)
  renderApp(
    <>
      <AudioControls />
      <ReadAloud text="Read once." />
    </>,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Listen to explanation' }))
  await waitFor(() => expect(audio.enqueue).toHaveBeenCalledOnce())
  fireEvent.click(screen.getAllByRole('button', { name: 'Pause reading', hidden: true })[0])
  await waitFor(() =>
    expect(screen.getAllByRole('button', { name: 'Resume reading', hidden: true })).toHaveLength(2),
  )
  fireEvent.click(screen.getAllByRole('button', { name: 'Resume reading', hidden: true })[0])
  await waitFor(() =>
    expect(screen.getAllByRole('button', { name: 'Pause reading', hidden: true })).toHaveLength(2),
  )
  fireEvent.click(screen.getAllByRole('button', { name: 'Stop reading', hidden: true })[0])
  expect(screen.queryByRole('button', { name: 'Stop reading', hidden: true })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Listen to explanation' })).toBeVisible()
  expect(audio.pause).toHaveBeenCalledOnce()
  expect(audio.resume).toHaveBeenCalledOnce()
  expect(fetcher).toHaveBeenCalledOnce()
})
