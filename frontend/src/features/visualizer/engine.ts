/** Portable preset subset: no executable source, network, file access or dynamic shaders. */
export type Feature = 'rms' | 'bass' | 'mid' | 'treble'
export type Frame = Record<Feature, number>
type Node =
  | { id: string; type: 'feature'; feature: Feature }
  | { id: string; type: 'constant'; value: number }
  | { id: string; type: 'map'; input: string; inputRange: [number, number]; outputRange: [number, number] }
  | { id: string; type: 'smooth'; input: string; attackMs: number; releaseMs: number }
  | { id: string; type: 'lfo'; frequencyHz: number; amplitude: number }
export type Preset = {
  schemaVersion: 1
  name: string
  nodes: Node[]
  visual: { kind: 'rings' | 'bars' | 'orbit'; color: string; scale: string; energy: string }
}
export const initial: Preset = {
  schemaVersion: 1,
  name: 'Bass rings',
  nodes: [
    { id: 'signal', type: 'feature', feature: 'bass' },
    { id: 'soft', type: 'smooth', input: 'signal', attackMs: 40, releaseMs: 350 },
    { id: 'size', type: 'map', input: 'soft', inputRange: [0, 1], outputRange: [0.4, 1.4] },
  ],
  visual: { kind: 'rings', color: '#a78bfa', scale: 'size', energy: 'soft' },
}
export const clamp = (x: number, min = 0, max = 1) =>
  Math.min(max, Math.max(min, Number.isFinite(x) ? x : min))
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Expected a JSON object.')
  return value as Record<string, unknown>
}
function finite(value: unknown, min = -100, max = 100): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max)
    throw new Error(`Number must be between ${min} and ${max}.`)
  return value
}
function id(value: unknown): string {
  if (typeof value !== 'string' || !/^[a-zA-Z][a-zA-Z0-9_-]{0,39}$/.test(value))
    throw new Error('Node IDs must be short names starting with a letter.')
  return value
}
function pair(value: unknown): [number, number] {
  if (!Array.isArray(value) || value.length !== 2) throw new Error('Ranges need two finite numbers.')
  return [finite(value[0]), finite(value[1])]
}
export function parsePreset(text: string): Preset {
  if (text.length > 16000) throw new Error('Preset exceeds 16,000 characters.')
  const p = object(JSON.parse(text))
  if (p.schemaVersion !== 1) throw new Error('Only schemaVersion 1 is supported.')
  if (typeof p.name !== 'string' || !p.name.trim() || p.name.length > 80)
    throw new Error('Give the preset a name of 1–80 characters.')
  if (!Array.isArray(p.nodes) || p.nodes.length < 1 || p.nodes.length > 32) throw new Error('Use 1–32 nodes.')
  const nodes: Node[] = p.nodes.map((raw: unknown): Node => {
    const n = object(raw)
    const key = id(n.id)
    switch (n.type) {
      case 'feature':
        if (typeof n.feature !== 'string' || !['rms', 'bass', 'mid', 'treble'].includes(n.feature))
          throw new Error('Unknown audio feature.')
        return { id: key, type: 'feature', feature: n.feature as Feature }
      case 'constant':
        return { id: key, type: 'constant', value: finite(n.value) }
      case 'lfo':
        return {
          id: key,
          type: 'lfo',
          frequencyHz: finite(n.frequencyHz, 0, 2),
          amplitude: finite(n.amplitude, 0, 2),
        }
      case 'smooth':
        return {
          id: key,
          type: 'smooth',
          input: id(n.input),
          attackMs: finite(n.attackMs, 1, 10000),
          releaseMs: finite(n.releaseMs, 1, 10000),
        }
      case 'map': {
        const inputRange = pair(n.inputRange)
        if (inputRange[0] >= inputRange[1])
          throw new Error('Input range must increase; zero-width ranges cannot be mapped.')
        return { id: key, type: 'map', input: id(n.input), inputRange, outputRange: pair(n.outputRange) }
      }
      default:
        throw new Error('Unknown node type. Use feature, constant, map, smooth or lfo.')
    }
  })
  const byId = new Map(nodes.map((n) => [n.id, n]))
  if (byId.size !== nodes.length) throw new Error('Node IDs must be unique.')
  const order: Node[] = []
  const active = new Set<string>()
  const done = new Set<string>()
  function visit(key: string) {
    if (active.has(key)) throw new Error('The graph contains a cycle.')
    if (done.has(key)) return
    const n = byId.get(key)
    if (!n) throw new Error(`Missing node: ${key}`)
    active.add(key)
    if ('input' in n) visit(n.input)
    active.delete(key)
    done.add(key)
    order.push(n)
  }
  nodes.forEach((n) => visit(n.id))
  const visual = object(p.visual)
  if (typeof visual.kind !== 'string' || !['rings', 'bars', 'orbit'].includes(visual.kind))
    throw new Error('Choose rings, bars or orbit.')
  if (typeof visual.color !== 'string' || !/^#[\da-fA-F]{6}$/.test(visual.color))
    throw new Error('Color must be a six-digit hex color.')
  const scale = id(visual.scale)
  const energy = id(visual.energy)
  if (!byId.has(scale) || !byId.has(energy)) throw new Error('Visual bindings must name existing nodes.')
  return {
    schemaVersion: 1,
    name: p.name.trim(),
    nodes: order,
    visual: { kind: visual.kind as Preset['visual']['kind'], color: visual.color, scale, energy },
  }
}
export function evaluate(
  preset: Preset,
  frame: Frame,
  seconds: number,
  dt: number,
  memory: Map<string, number>,
) {
  const values = new Map<string, number>()
  for (const n of preset.nodes) {
    let value = 0
    if (n.type === 'feature') value = clamp(frame[n.feature])
    if (n.type === 'constant') value = n.value
    if (n.type === 'lfo') value = (Math.sin(seconds * 2 * Math.PI * n.frequencyHz) + 1) * 0.5 * n.amplitude
    if (n.type === 'map') {
      const ratio = clamp(
        ((values.get(n.input) ?? 0) - n.inputRange[0]) / (n.inputRange[1] - n.inputRange[0]),
      )
      value = n.outputRange[0] + ratio * (n.outputRange[1] - n.outputRange[0])
    }
    if (n.type === 'smooth') {
      const target = values.get(n.input) ?? 0
      const old = memory.get(n.id) ?? 0
      const tau = (target > old ? n.attackMs : n.releaseMs) / 1000
      value = old + (target - old) * (1 - Math.exp(-clamp(dt, 0, 0.25) / tau))
      memory.set(n.id, value)
    }
    values.set(n.id, clamp(value, -100, 100))
  }
  return {
    scale: clamp(values.get(preset.visual.scale) ?? 1, 0.1, 2),
    energy: clamp(values.get(preset.visual.energy) ?? 0),
    values,
  }
}
export function features(time: Float32Array, db: Float32Array, sampleRate: number, fftSize: number): Frame {
  const rms = Math.sqrt(time.reduce((sum, x) => sum + x * x, 0) / Math.max(1, time.length))
  function band(low: number, high: number) {
    let sum = 0
    let count = 0
    for (let i = 0; i < db.length; i++) {
      const hz = (i * sampleRate) / fftSize
      if (hz >= low && hz < high) {
        sum += clamp((db[i] + 80) / 60)
        count++
      }
    }
    return count ? sum / count : 0
  }
  return {
    rms: clamp(rms),
    bass: band(20, 250),
    mid: band(250, 4000),
    treble: band(4000, Math.min(16000, sampleRate / 2)),
  }
}
export function demoFrame(t: number): Frame {
  return {
    bass: (Math.sin(t * 3) + 1) / 2,
    mid: (Math.sin(t * 1.7 + 1) + 1) / 2,
    treble: (Math.sin(t * 4.1 + 2) + 1) / 2,
    rms: 0.4,
  }
}
