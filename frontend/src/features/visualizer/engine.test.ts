import { describe, expect, it } from 'vitest'
import { evaluate, features, initial, parsePreset } from './engine'
const encode = (value: unknown) => JSON.stringify(value)
describe('bounded visualizer presets', () => {
  it('rejects cycles, missing references, duplicate IDs and invalid ranges', () => {
    for (const nodes of [
      [{ id: 'size', type: 'smooth', input: 'size', attackMs: 10, releaseMs: 10 }],
      [{ id: 'size', type: 'smooth', input: 'missing', attackMs: 10, releaseMs: 10 }],
      [initial.nodes[0], initial.nodes[0]],
      [
        initial.nodes[0],
        { id: 'size', type: 'map', input: 'signal', inputRange: [1, 1], outputRange: [0, 1] },
      ],
    ])
      expect(() => parsePreset(encode({ ...initial, nodes }))).toThrow()
    expect(() => parsePreset(encode({ ...initial, schemaVersion: 2 }))).toThrow()
    expect(() => parsePreset(' '.repeat(16001))).toThrow()
    expect(() =>
      parsePreset(encode({ ...initial, nodes: [{ id: 'x', type: 'javascript', source: 'while(true){}' }] })),
    ).toThrow()
  })
  it('sorts dependencies and produces finite bounded output even for hostile feature values', () => {
    const p = parsePreset(encode({ ...initial, nodes: [...initial.nodes].reverse() }))
    expect(p.nodes[0].id).toBe('signal')
    const memory = new Map<string, number>()
    const out = evaluate(p, { bass: Infinity, rms: NaN, mid: -1, treble: 9 }, 1, 1, memory)
    expect(Number.isFinite(out.scale)).toBe(true)
    expect(out.energy).toBeGreaterThanOrEqual(0)
    expect(out.energy).toBeLessThanOrEqual(1)
  })
  it('computes RMS and respects frequency boundaries including silence', () => {
    const wave = new Float32Array([0.5, -0.5])
    const bins = new Float32Array(1024).fill(-Infinity)
    expect(features(wave, bins, 48000, 2048)).toEqual({ rms: 0.5, bass: 0, mid: 0, treble: 0 })
    bins[4] = -20 // 93.75 Hz, inside bass
    const frame = features(wave, bins, 48000, 2048)
    expect(frame.bass).toBeGreaterThan(0)
    expect(frame.mid).toBe(0)
    expect(frame.treble).toBe(0)
  })
})

it('rejects coerced enums instead of silently changing renderer or feature', () => {
  expect(() =>
    parsePreset(JSON.stringify({ ...initial, visual: { ...initial.visual, kind: ['rings'] } })),
  ).toThrow()
  expect(() =>
    parsePreset(
      JSON.stringify({
        ...initial,
        nodes: [{ id: 'signal', type: 'feature', feature: ['bass'] }, ...initial.nodes.slice(1)],
      }),
    ),
  ).toThrow()
})
