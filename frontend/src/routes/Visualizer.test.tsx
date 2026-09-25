import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { renderApp, jsonResponse } from '../test/utils'
import { Visualizer } from './Visualizer'
import { openAudio } from '../features/visualizer/audio'
import { initial } from '../features/visualizer/engine'
vi.mock('../features/visualizer/AudioWaveform', () => ({ AudioWaveform: () => <div>Waveform preview</div> }))
vi.mock('../features/visualizer/audio', () => ({ openAudio: vi.fn() }))
beforeEach(() => {
  localStorage.clear()
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse({ values: { 'ui.reduced_motion': true, 'ui.sound': false } })),
  )
})
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  vi.mocked(openAudio).mockReset()
})
it('starts still, preserves valid presets after invalid edits, and exposes hints accessibly', async () => {
  const { container } = renderApp(<Visualizer />)
  expect(openAudio).not.toHaveBeenCalled()
  expect(screen.getByRole('button', { name: 'Start demo' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Next sample' }))
  fireEvent.change(screen.getByLabelText('Preset JSON'), { target: { value: '{broken' } })
  fireEvent.click(screen.getByRole('button', { name: 'Apply preset' }))
  expect(screen.getByRole('alert')).toHaveTextContent('last working preset')
  expect(screen.getByText(/Active preset: Bass rings/)).toBeVisible()
  fireEvent.click(screen.getByText('Guided Bass rings lesson'))
  fireEvent.click(screen.getByRole('button', { name: 'One hint' }))
  expect(screen.getByText(/Start with the feature node/)).toBeVisible()
  fireEvent.change(screen.getByLabelText('Preset JSON'), {
    target: { value: JSON.stringify({ ...initial, name: 'Saved experiment' }) },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Apply preset' }))
  fireEvent.click(screen.getByRole('button', { name: 'Save applied preset' }))
  expect(localStorage.getItem('audhs:visualizer:preset:v1')).toContain('Saved experiment')
  expect(await axe(container)).toHaveNoViolations()
})
it('cancels a pending audio open and disposes late completion', async () => {
  let resolve!: (value: Awaited<ReturnType<typeof openAudio>>) => void
  vi.mocked(openAudio).mockImplementation(
    () =>
      new Promise((r) => {
        resolve = r
      }),
  )
  const { unmount } = renderApp(<Visualizer />)
  fireEvent.change(screen.getByLabelText('Input'), { target: { value: 'file' } })
  fireEvent.change(screen.getByLabelText('Audio file'), {
    target: { files: [new File(['x'], 'demo.wav', { type: 'audio/wav' })] },
  })
  expect(openAudio).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Play file silently' }))
  fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
  const disposed = vi.fn()
  resolve({ read: () => ({ bass: 0, mid: 0, treble: 0, rms: 0 }), stop: disposed, setAudible: vi.fn() })
  await waitFor(() => expect(disposed).toHaveBeenCalled())
  expect(vi.mocked(openAudio).mock.calls[0][2].aborted).toBe(true)
  unmount()
})

it('replays identical demo samples and restores the guided graph explicitly', () => {
  renderApp(<Visualizer />)
  fireEvent.click(screen.getByRole('button', { name: 'Next sample' }))
  const before = screen.getByText(/Manual sample: 1/).textContent
  fireEvent.click(screen.getByRole('button', { name: 'Reset demo' }))
  fireEvent.click(screen.getByRole('button', { name: 'Next sample' }))
  expect(screen.getByText(/Manual sample: 1/).textContent).toBe(before)
  fireEvent.change(screen.getByLabelText('Preset JSON'), {
    target: { value: JSON.stringify({ ...initial, name: 'Custom' }) },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Apply preset' }))
  fireEvent.click(screen.getByRole('button', { name: 'Save applied preset' }))
  fireEvent.click(screen.getByText('Guided Bass rings lesson'))
  fireEvent.click(screen.getByRole('button', { name: 'Start guided example' }))
  expect(screen.getByText(/Active preset: Bass rings/)).toBeVisible()
  expect(localStorage.getItem('audhs:visualizer:preset:v1')).toContain('Custom')
})

it('uses current sound permission after async opening and handles natural completion', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse({ values: { 'ui.reduced_motion': true, 'ui.sound': true } })),
  )
  let resolve!: (value: Awaited<ReturnType<typeof openAudio>>) => void
  vi.mocked(openAudio).mockImplementation(
    () =>
      new Promise((r) => {
        resolve = r
      }),
  )
  renderApp(<Visualizer />)
  fireEvent.change(screen.getByLabelText('Input'), { target: { value: 'file' } })
  const hear = screen.getByRole('checkbox', { name: 'Hear audio at half volume' })
  await waitFor(() => expect(hear).toBeEnabled())
  fireEvent.click(hear)
  fireEvent.change(screen.getByLabelText('Audio file'), {
    target: { files: [new File(['x'], 'demo.wav', { type: 'audio/wav' })] },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Play file with sound' }))
  expect(vi.mocked(openAudio).mock.calls[0][1]).toBe(false)
  fireEvent.click(hear)
  const setAudible = vi.fn()
  const stop = vi.fn()
  resolve({ read: () => ({ bass: 0, mid: 0, treble: 0, rms: 0 }), stop, setAudible })
  await waitFor(() => expect(setAudible).toHaveBeenCalledWith(false))
  const end = vi.mocked(openAudio).mock.calls[0][3]
  await import('@testing-library/react').then(({ act }) =>
    act(() => {
      end?.()
    }),
  )
  expect(screen.getByRole('button', { name: 'Play file silently' })).toBeEnabled()
  expect(stop).toHaveBeenCalled()
  expect(screen.getByText(/File finished/)).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Switch to silent demo' }))
  expect(screen.queryByText(/File finished/)).toBeNull()
  expect(screen.getByText(/Demo stopped/)).toBeVisible()
})

it('keeps advanced code and example-specific teaching optional and prevents saving an older preview', () => {
  renderApp(<Visualizer />)
  expect(screen.getByLabelText('Preset JSON')).not.toBeVisible()
  expect(screen.getByText('Start guided example')).not.toBeVisible()
  expect(screen.getByRole('button', { name: 'Apply preset' })).toBeVisible()
  fireEvent.change(screen.getByLabelText('Visual style'), { target: { value: 'orbit' } })
  expect(screen.getByText('You have changes to preview. Apply them when ready.')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Save applied preset' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Export applied preset' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Apply preset' }))
  expect(screen.getByText('The preview matches your settings.')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Save applied preset' })).toBeEnabled()
  fireEvent.click(screen.getByText('Advanced: edit preset JSON'))
  expect(screen.getByLabelText('Preset JSON')).toBeVisible()
})

it('does not revive playback when Stop interrupts a pending Resume', async () => {
  let complete!: () => void
  const resume = vi.fn(
    () =>
      new Promise<void>((resolve) => {
        complete = resolve
      }),
  )
  const pause = vi.fn()
  const stopAudio = vi.fn()
  vi.mocked(openAudio).mockResolvedValue({
    read: () => ({ bass: 0, mid: 0, treble: 0, rms: 0 }),
    stop: stopAudio,
    setAudible: vi.fn(),
    pause,
    resume,
    position: () => ({ seconds: 2, duration: 10 }),
    seek: vi.fn(),
  })
  renderApp(<Visualizer />)
  fireEvent.change(screen.getByLabelText('Input'), { target: { value: 'file' } })
  fireEvent.change(screen.getByLabelText('Audio file'), { target: { files: [new File(['x'], 'test.wav')] } })
  fireEvent.click(screen.getByRole('button', { name: 'Play file silently' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Pause file' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Pause file' }))
  expect(pause).toHaveBeenCalledOnce()
  fireEvent.click(screen.getByRole('button', { name: 'Resume file' }))
  fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
  await import('@testing-library/react').then(({ act }) => act(async () => complete()))
  expect(screen.getByRole('button', { name: 'Pause file' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Play file silently' })).toBeEnabled()
  expect(stopAudio).toHaveBeenCalled()
})

it('explains storage failure without changing applied settings', () => {
  renderApp(<Visualizer />)
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('quota')
  })
  fireEvent.click(screen.getByRole('button', { name: 'Save applied preset' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Browser storage is unavailable')
  expect(screen.getByText(/Active preset: Bass rings/)).toBeVisible()
  expect(screen.getByRole('button', { name: 'Export applied preset' })).toBeEnabled()
})
