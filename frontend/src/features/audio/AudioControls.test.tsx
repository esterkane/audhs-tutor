import { act, fireEvent, render, screen, cleanup } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
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
