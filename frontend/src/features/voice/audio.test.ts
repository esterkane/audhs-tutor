import { afterEach, expect, it, vi } from 'vitest'
import { Player } from './audio'

afterEach(() => vi.unstubAllGlobals())
it('queues chunks in a suspended context without resuming or changing their schedule', async () => {
  const starts: number[] = []
  const ctx = {
    state: 'running',
    currentTime: 2,
    destination: {},
    resume: vi.fn(async () => {
      ctx.state = 'running'
    }),
    suspend: vi.fn(async () => {
      ctx.state = 'suspended'
    }),
    close: vi.fn(async () => {}),
    createBuffer: () => ({ duration: 1, getChannelData: () => new Float32Array(2) }),
    createGain: () => ({ gain: { value: 1 }, connect: vi.fn() }),
    createBufferSource: () => ({
      playbackRate: { value: 1 },
      connect: vi.fn(),
      start: (at: number) => starts.push(at),
      stop: vi.fn(),
    }),
  }
  vi.stubGlobal(
    'AudioContext',
    class {
      constructor() {
        return ctx
      }
    },
  )
  const player = new Player()
  await player.unlock()
  player.enqueue(new Int16Array(2), 24000)
  await player.pause()
  player.enqueue(new Int16Array(2), 24000)
  expect(ctx.resume).not.toHaveBeenCalled()
  expect(starts).toEqual([2, 3])
  expect(player.pending()).toBe(2)
  await player.resume()
  expect(ctx.resume).toHaveBeenCalledOnce()
  expect(starts).toEqual([2, 3])
  player.close()
  expect(ctx.close).toHaveBeenCalledOnce()
})
