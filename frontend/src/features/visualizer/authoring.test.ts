import { expect, it } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { addBlock, removeBlock, readPresetFile } from './authoring'
import { initial, parsePreset } from './engine'
import { connectPreset } from './connections'
import { useDraftHistory } from './useDraftHistory'
it('creates every type, bounds count and refuses referenced deletion', () => {
  let p = initial
  for (const type of ['feature', 'constant', 'map', 'smooth', 'lfo'] as const) p = addBlock(p, type, 'signal')
  expect(parsePreset(JSON.stringify(p))).toEqual(p)
  expect(removeBlock(p, 'constant_1').nodes).toHaveLength(7)
  expect(() => removeBlock(p, 'signal')).toThrow('Reconnect')
  expect(() => removeBlock(p, 'size')).toThrow('visual size')
  while (p.nodes.length < 32) p = addBlock(p, 'constant', 'signal')
  expect(() => addBlock(p, 'constant', 'signal')).toThrow('32 blocks')
})
it('preserves prototype-like IDs and rejects cycles and unknown import versions', async () => {
  const p = parsePreset(
    JSON.stringify({
      ...initial,
      nodes: [...initial.nodes, { id: 'constructor', type: 'constant', value: 0.8 }],
    }),
  )
  expect(connectPreset(p, 'constructor', 'output:scale').visual.scale).toBe('constructor')
  expect(() => connectPreset(p, 'size', 'soft')).toThrow('cycle')
  await expect(
    readPresetFile({ size: 20, text: async () => JSON.stringify({ ...initial, schemaVersion: 2 }) } as File),
  ).rejects.toThrow('schemaVersion')
  await expect(readPresetFile({ size: 16001 } as File)).rejects.toThrow('16,000 bytes')
})
it('undoes reconnect, skips invalid JSON and bounds history', () => {
  const original = JSON.stringify(initial)
  const next = JSON.stringify(connectPreset(initial, 'signal', 'output:scale'))
  const { result } = renderHook(() => useDraftHistory(original))
  act(() => result.current.change(next))
  act(() => result.current.undo())
  expect(result.current.text).toBe(original)
  act(() => result.current.redo())
  expect(result.current.text).toBe(next)
  act(() => result.current.change('{'))
  act(() => result.current.change('{invalid'))
  act(() => result.current.undo())
  expect(result.current.text).toBe(next)
  expect(result.current.canRedo).toBe(false)
  for (let i = 0; i < 60; i++)
    act(() => result.current.change(JSON.stringify({ ...initial, name: `Test ${i}` })))
  for (let i = 0; i < 50; i++) act(() => result.current.undo())
  expect(result.current.canUndo).toBe(false)
})
