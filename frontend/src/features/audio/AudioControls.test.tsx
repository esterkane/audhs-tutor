import { act, fireEvent, render, screen, cleanup } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { claimReading, updateReading, useReadingControls } from '../voice/readingOwner'
import { AudioControls } from './AudioControls'
import { useAudioSettings } from './settings'
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  useAudioSettings.setState({ volume: 0.5, rate: 1, muted: false, saved: true })
})
it('shows shared settings in each surface and prevents a misleading muted sound test', () => {
  render(
    <>
      <AudioControls />
      <AudioControls />
    </>,
  )
  fireEvent.change(screen.getAllByLabelText('Audio volume')[0], { target: { value: '0.25' } })
  expect(screen.getAllByLabelText('Audio volume')[1]).toHaveValue('0.25')
  fireEvent.click(screen.getAllByRole('button', { name: 'Mute', hidden: true })[0])
  expect(screen.getAllByRole('button', { name: 'Test sound', hidden: true })[0]).toBeDisabled()
  expect(screen.getAllByRole('button', { name: 'Unmute', hidden: true })).toHaveLength(2)
})

it('does not start a test tone after its controls unmount during resume', async () => {
  let resume!: () => void
  const start = vi.fn()
  const close = vi.fn(async () => {})
  const gain = { gain: { value: 0 }, connect: vi.fn() }
  vi.stubGlobal(
    'AudioContext',
    class {
      destination = {}
      currentTime = 0
      createGain() {
        return gain
      }
      createOscillator() {
        return { frequency: { value: 0 }, connect: () => gain, start, stop: vi.fn() }
      }
      resume() {
        return new Promise<void>((resolve) => {
          resume = resolve
        })
      }
      close = close
    },
  )
  const view = render(<AudioControls />)
  fireEvent.click(screen.getByRole('button', { name: 'Test sound', hidden: true }))
  view.unmount()
  await act(async () => {
    resume()
  })
  expect(start).not.toHaveBeenCalled()
  expect(close).toHaveBeenCalledOnce()
})

function fakeToneContexts() {
  const contexts: Array<{
    resolve: () => void
    reject: (error: Error) => void
    close: ReturnType<typeof vi.fn>
    oscillator: {
      frequency: { value: number }
      connect: () => { connect: ReturnType<typeof vi.fn> }
      start: ReturnType<typeof vi.fn>
      stop: ReturnType<typeof vi.fn>
      onended: (() => void) | null
    }
  }> = []
  vi.stubGlobal(
    'AudioContext',
    class {
      destination = {}
      currentTime = 0
      gain = { gain: { value: 0 }, connect: vi.fn() }
      oscillator = {
        frequency: { value: 0 },
        connect: () => this.gain,
        start: vi.fn(),
        stop: vi.fn(),
        onended: null as (() => void) | null,
      }
      close = vi.fn(async () => {})
      resolve!: () => void
      reject!: (error: Error) => void
      constructor() {
        contexts.push(this)
      }
      createGain() {
        return this.gain
      }
      createOscillator() {
        return this.oscillator
      }
      resume() {
        return new Promise<void>((resolve, reject) => {
          this.resolve = resolve
          this.reject = reject
        })
      }
    },
  )
  return contexts
}

it('a replacement cancels a pending sound test without reviving it', async () => {
  const contexts = fakeToneContexts()
  render(<AudioControls />)
  fireEvent.click(screen.getByRole('button', { name: 'Test sound', hidden: true }))
  let release!: () => void
  act(() => {
    release = claimReading(() => {}, 'a reading')
    updateReading(release, { kind: 'voice', status: 'Other activity', stop: release })
  })
  await act(async () => contexts[0].resolve())
  expect(contexts[0].oscillator.start).not.toHaveBeenCalled()
  expect(contexts[0].close).toHaveBeenCalledOnce()
  expect(screen.getByText('Sound test stopped because a reading started.')).toBeInTheDocument()
  expect(useReadingControls.getState().reading?.status).toBe('Other activity')
  act(() => release())
})

it('a rejected old resume cannot close a newer sound test', async () => {
  const contexts = fakeToneContexts()
  render(<AudioControls />)
  const test = screen.getByRole('button', { name: 'Test sound', hidden: true })
  fireEvent.click(test)
  fireEvent.click(test)
  await act(async () => {
    contexts[0].reject(new Error('old failure'))
    contexts[1].resolve()
  })
  expect(contexts[0].close).toHaveBeenCalledOnce()
  expect(contexts[1].close).not.toHaveBeenCalled()
  expect(contexts[1].oscillator.start).toHaveBeenCalledOnce()
  expect(screen.queryByText(/old failure/)).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Stop sound test', hidden: true }))
  expect(contexts[1].close).toHaveBeenCalledOnce()
  expect(useReadingControls.getState().reading).toBeNull()
})

it('shared Stop cancels the tone, and an old ended event cannot clear the next owner', async () => {
  const contexts = fakeToneContexts()
  render(
    <>
      <AudioControls />
      <AudioControls />
    </>,
  )
  fireEvent.click(screen.getAllByRole('button', { name: 'Test sound', hidden: true })[0])
  await act(async () => contexts[0].resolve())
  const lateEnded = contexts[0].oscillator.onended!
  expect(screen.queryByRole('button', { name: 'Pause reading', hidden: true })).not.toBeInTheDocument()
  fireEvent.click(screen.getAllByRole('button', { name: 'Stop sound test', hidden: true })[1])
  expect(contexts[0].close).toHaveBeenCalledOnce()
  fireEvent.click(screen.getAllByRole('button', { name: 'Test sound', hidden: true })[1])
  await act(async () => contexts[1].resolve())
  act(() => lateEnded())
  expect(contexts[1].close).not.toHaveBeenCalled()
  expect(useReadingControls.getState().reading?.kind).toBe('test')
  act(() => contexts[1].oscillator.onended!())
  expect(useReadingControls.getState().reading).toBeNull()
})

it('a current resume failure releases the sound-test owner and explains the error', async () => {
  const contexts = fakeToneContexts()
  render(<AudioControls />)
  fireEvent.click(screen.getByRole('button', { name: 'Test sound', hidden: true }))
  await act(async () => contexts[0].reject(new Error('output unavailable')))
  expect(contexts[0].close).toHaveBeenCalledOnce()
  expect(useReadingControls.getState().reading).toBeNull()
  expect(screen.getByText('Sound test failed: output unavailable')).toBeInTheDocument()
})
