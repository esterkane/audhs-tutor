import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import WaveSurfer from 'wavesurfer.js'
import { AudioWaveform } from './AudioWaveform'
vi.mock('wavesurfer.js', () => ({ default: { create: vi.fn() } }))
afterEach(() => vi.resetAllMocks())
function player(loadBlob = vi.fn(async () => {})) {
  const p = {
    loadBlob,
    setMuted: vi.fn(),
    setTime: vi.fn(),
    destroy: vi.fn(),
    on: vi.fn(() => vi.fn()),
    getDuration: () => 2,
  }
  vi.mocked(WaveSurfer.create).mockReturnValue(p as unknown as WaveSurfer)
  return p
}
it('prepares a muted noninteractive overview without playback and cleans up', async () => {
  const p = player()
  const file = new File(['x'], 'local.wav')
  const { rerender, unmount } = render(<AudioWaveform file={file} seconds={0} reduced />)
  await screen.findByText(/Waveform ready/)
  expect(WaveSurfer.create).toHaveBeenCalledWith(
    expect.objectContaining({ autoplay: false, interact: false }),
  )
  expect(p.setMuted).toHaveBeenCalledWith(true)
  expect(p.loadBlob).toHaveBeenCalledWith(file)
  rerender(<AudioWaveform file={file} seconds={1} reduced />)
  expect(p.setTime).not.toHaveBeenCalled()
  rerender(<AudioWaveform file={file} seconds={1} reduced={false} />)
  expect(p.setTime).toHaveBeenCalledWith(1)
  unmount()
  expect(p.destroy).toHaveBeenCalledOnce()
})
it('offers playback fallback after decode failure and skips large previews', async () => {
  player(
    vi.fn(async () => {
      throw new Error('decode')
    }),
  )
  const { unmount } = render(<AudioWaveform file={new File(['x'], 'broken.wav')} seconds={0} reduced />)
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('You can still try playing'))
  unmount()
  vi.mocked(WaveSurfer.create).mockClear()
  const file = new File([], 'large.wav')
  Object.defineProperty(file, 'size', { value: 21 * 1024 * 1024 })
  render(<AudioWaveform file={file} seconds={0} reduced />)
  expect(screen.getByText(/up to 20 MiB/)).toBeVisible()
  expect(WaveSurfer.create).not.toHaveBeenCalled()
})

it('drops previous ready state when a different file has identical metadata', async () => {
  const first = player()
  const fileA = new File(['a'], 'same.wav', { lastModified: 10 })
  const fileB = new File(['b'], 'same.wav', { lastModified: 10 })
  const { rerender } = render(<AudioWaveform file={fileA} seconds={0} reduced />)
  await screen.findByText(/Waveform ready/)
  player(vi.fn(() => new Promise<void>(() => {})))
  rerender(<AudioWaveform file={fileB} seconds={0} reduced />)
  expect(screen.getByRole('status')).toHaveTextContent('Preparing waveform')
  expect(screen.getByRole('button', { name: 'Show frequency view (optional)' })).toBeDisabled()
  expect(first.destroy).toHaveBeenCalledOnce()
})
