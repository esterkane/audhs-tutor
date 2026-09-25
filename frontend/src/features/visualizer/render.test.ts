import { expect, it, vi } from 'vitest'
import { draw } from './render'
import { initial } from './engine'
it('makes the bars respond to their size binding as well as energy', () => {
  const fillRect = vi.fn()
  const canvas = { width: 720, height: 320, getContext: () => ({ fillRect }) } as unknown as HTMLCanvasElement
  const preset = { ...initial, visual: { ...initial.visual, kind: 'bars' as const } }
  draw(canvas, preset, 0.4, 0.5)
  const short = fillRect.mock.calls[1][3]
  fillRect.mockClear()
  draw(canvas, preset, 1.4, 0.5)
  expect(fillRect.mock.calls[1][3]).toBeGreaterThan(short)
})
