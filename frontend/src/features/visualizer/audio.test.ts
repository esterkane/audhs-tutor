import { afterEach, expect, it, vi } from 'vitest'
import { openAudio } from './audio'
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})
it('releases the audio context and blob on natural completion without uploading', async () => {
  const audio = new EventTarget() as EventTarget & {
    currentTime: number
    duration: number
    src: string
    pause: () => void
    load: () => void
    removeAttribute: () => void
    play: () => Promise<void>
  }
  Object.assign(audio, {
    src: '',
    currentTime: 1,
    duration: 2,
    pause: vi.fn(),
    load: vi.fn(),
    removeAttribute: vi.fn(),
    play: vi.fn(async () => {}),
  })
  const gain = { gain: { value: 0 }, connect: vi.fn() }
  const context = {
    createMediaElementSource: () => ({ connect: vi.fn() }),
    createAnalyser: () => ({ connect: vi.fn(), frequencyBinCount: 1024 }),
    createGain: () => gain,
    resume: async () => {},
    close: vi.fn(async () => {}),
    destination: {},
    sampleRate: 48000,
  }
  vi.stubGlobal(
    'Audio',
    vi.fn(function () {
      return audio
    }),
  )
  vi.stubGlobal(
    'AudioContext',
    vi.fn(function () {
      return context
    }),
  )
  const revoke = vi.fn()
  vi.stubGlobal('URL', { createObjectURL: () => 'blob:local-test', revokeObjectURL: revoke })
  const ended = vi.fn()
  const abort = new AbortController()
  const input = await openAudio(new File(['x'], 'sample.wav'), false, abort.signal, ended)
  expect(gain.gain.value).toBe(0)
  expect(input.position?.()).toEqual({ seconds: 1, duration: 2 })
  input.pause?.()
  expect(audio.pause).toHaveBeenCalledOnce()
  await input.resume?.()
  expect(audio.play).toHaveBeenCalledTimes(2)
  input.seek?.(99)
  expect(input.position?.()?.seconds).toBe(2)
  input.seek?.(-1)
  expect(input.position?.()?.seconds).toBe(0)
  input.seek?.(1)
  input.seek?.(Number.NaN)
  const wrap = vi.fn()
  expect(() => input.setRepeat?.({ start: 1.9, end: 2 }, wrap)).toThrow()
  expect(() => input.setRepeat?.({ start: 0, end: 3 }, wrap)).toThrow()
  input.setRepeat?.({ start: 0.5, end: 1.5 }, wrap)
  expect(audio.currentTime).toBe(0.5)
  audio.currentTime = 1.6
  audio.dispatchEvent(new Event('timeupdate'))
  expect(audio.currentTime).toBe(0.5)
  input.pause?.()
  audio.currentTime = 1.7
  audio.dispatchEvent(new Event('timeupdate'))
  expect(audio.currentTime).toBe(1.7)
  await input.resume?.()
  let rejectLoop!: (reason: Error) => void
  vi.mocked(audio.play).mockImplementationOnce(
    () =>
      new Promise<void>((_, reject) => {
        rejectLoop = reject
      }),
  )
  audio.dispatchEvent(new Event('ended'))
  input.pause?.()
  rejectLoop(new Error('AbortError'))
  await Promise.resolve()
  await Promise.resolve()
  expect(ended).not.toHaveBeenCalled()
  expect(context.close).not.toHaveBeenCalled()
  input.setRepeat?.(null)
  await input.resume?.()
  input.seek?.(1)
  audio.dispatchEvent(new Event('ended'))
  expect(ended).toHaveBeenCalledOnce()
  expect(input.position?.()).toEqual({ seconds: 1, duration: 2 })
  expect(context.close).toHaveBeenCalledOnce()
  expect(revoke).toHaveBeenCalledWith('blob:local-test')
  input.stop()
  abort.abort()
  expect(context.close).toHaveBeenCalledOnce()
  await expect(input.resume?.()).rejects.toThrow(/stopped/)
})
