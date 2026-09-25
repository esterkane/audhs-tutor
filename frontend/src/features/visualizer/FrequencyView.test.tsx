import { render, screen, waitFor, act } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type WaveSurfer from 'wavesurfer.js'
import { FrequencyView } from './FrequencyView'
const { create, destroy, handlers } = vi.hoisted(() => ({
  create: vi.fn(),
  destroy: vi.fn(),
  handlers: {} as Record<string, () => void>,
}))
vi.mock('wavesurfer.js/dist/plugins/spectrogram.js', () => ({ default: { create } }))
afterEach(() => {
  vi.resetAllMocks()
  for (const key of Object.keys(handlers)) delete handlers[key]
})
it('labels bounded frequency and time axes, handles plugin failure and cleans up', async () => {
  create.mockReturnValue({
    on: (name: string, fn: () => void) => {
      handlers[name] = fn
    },
    destroy,
  })
  const registerPlugin = vi.fn()
  const { unmount } = render(
    <FrequencyView player={{ registerPlugin } as unknown as WaveSurfer} duration={10} />,
  )
  await waitFor(() => expect(registerPlugin).toHaveBeenCalledOnce())
  expect(create).toHaveBeenCalledWith(
    expect.objectContaining({
      frequencyMax: 2000,
      colorMap: 'igray',
      useWebWorker: true,
      fallbackToMainThread: false,
    }),
  )
  expect(screen.getByText(/only 0–2,000 Hz/)).toBeVisible()
  expect(screen.getByText('10.0 s')).toBeVisible()
  act(() => handlers.ready())
  expect(screen.getByRole('status')).toHaveTextContent('Frequency view ready')
  act(() => handlers.error())
  expect(screen.getByRole('status')).toHaveTextContent('Waveform and playback still work')
  unmount()
  expect(destroy).toHaveBeenCalledOnce()
})
