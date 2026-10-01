import { fireEvent, screen, waitFor, act } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp, jsonResponse } from '../../test/utils'
import { DictationButton } from './DictationButton'
import { startMic } from './audio'
vi.mock('./audio', () => ({ startMic: vi.fn(), wavFromPcm16: vi.fn(() => new Blob(['wav'])) }))
afterEach(() => {
  vi.resetAllMocks()
  vi.unstubAllGlobals()
})
it('closes a microphone whose permission resolves after unmount', async () => {
  let resolve!: (m: { stop: () => void }) => void
  vi.mocked(startMic).mockImplementation(
    () =>
      new Promise((r) => {
        resolve = r
      }),
  )
  const stop = vi.fn()
  const view = renderApp(<DictationButton onTranscript={vi.fn()} />)
  fireEvent.click(screen.getByText('Dictate question'))
  view.unmount()
  await act(async () => resolve({ stop }))
  expect(stop).toHaveBeenCalledOnce()
})
it('stops recording before transcription and returns editable text only', async () => {
  const stop = vi.fn()
  const receive = vi.fn()
  vi.mocked(startMic).mockResolvedValue({ stop })
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => {
      expect(stop).toHaveBeenCalled()
      return jsonResponse({ text: 'Explain this step' })
    }),
  )
  renderApp(<DictationButton onTranscript={receive} />)
  fireEvent.click(screen.getByText('Dictate question'))
  fireEvent.click(await screen.findByText('Done — transcribe'))
  await waitFor(() => expect(receive).toHaveBeenCalledWith('Explain this step'))
})
