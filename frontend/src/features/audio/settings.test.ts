import { afterEach, expect, it, vi } from 'vitest'
import { bindMedia, bindOutput, useAudioSettings } from './settings'
import { Player } from '../voice/audio'
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  useAudioSettings.setState({ volume: 0.5, rate: 1, muted: false, saved: true })
})
it('updates output volume and media speed, keeps analysis input untouched, and unsubscribes', () => {
  const gain = { gain: { value: 0 } } as GainNode
  const audio = document.createElement('audio')
  const release = bindOutput(gain)
  const releaseMedia = bindMedia(audio)
  useAudioSettings.getState().update({ volume: 0.3, rate: 1.5 })
  expect(gain.gain.value).toBe(0.3)
  expect(audio.playbackRate).toBe(1.5)
  useAudioSettings.getState().update({ muted: true })
  expect(gain.gain.value).toBe(0)
  expect(audio.muted).toBe(true)
  release()
  releaseMedia()
  useAudioSettings.getState().update({ muted: false })
  expect(gain.gain.value).toBe(0)
  expect(audio.muted).toBe(true)
})
it('keeps in-memory preferences usable when storage fails', () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('quota')
  })
  useAudioSettings.getState().update({ volume: 0.25 })
  expect(useAudioSettings.getState().volume).toBe(0.25)
  expect(useAudioSettings.getState().saved).toBe(false)
})
it('schedules PCM without gaps at the chosen speed and keeps one speed while audio is queued', () => {
  const nodes: { playbackRate: { value: number }; start: ReturnType<typeof vi.fn>; onended?: () => void }[] =
    []
  const gain = { gain: { value: 0 }, connect: vi.fn() }
  vi.stubGlobal(
    'AudioContext',
    class {
      currentTime = 0
      state = 'running'
      destination = {}
      createBuffer() {
        return { duration: 2, getChannelData: () => new Float32Array(4) }
      }
      createGain() {
        return gain
      }
      createBufferSource() {
        const n = { playbackRate: { value: 1 }, connect: vi.fn(), start: vi.fn(), stop: vi.fn() }
        nodes.push(n)
        return n
      }
      close() {
        return Promise.resolve()
      }
    },
  )
  useAudioSettings.getState().update({ rate: 2 })
  const player = new Player()
  player.enqueue(new Int16Array(4), 2)
  useAudioSettings.getState().update({ rate: 0.5, volume: 0.2 })
  player.enqueue(new Int16Array(4), 2)
  expect(nodes[0].playbackRate.value).toBe(2)
  expect(nodes[1].playbackRate.value).toBe(2)
  expect(nodes[1].start).toHaveBeenCalledWith(1)
  expect(gain.gain.value).toBe(0.2)
  nodes[0].onended?.()
  nodes[1].onended?.()
  player.enqueue(new Int16Array(4), 2)
  expect(nodes[2].playbackRate.value).toBe(2)
  player.stop()
  player.enqueue(new Int16Array(4), 2)
  expect(nodes[3].playbackRate.value).toBe(0.5)
  player.close()
  useAudioSettings.getState().update({ volume: 1 })
  expect(gain.gain.value).toBe(0.2)
})
