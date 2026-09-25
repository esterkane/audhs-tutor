import { evaluate, parsePreset, type Frame, type Preset } from './engine'

export const experiments = [
  {
    id: 'feature',
    title: 'Choose a frequency region',
    context:
      'A sound feature reads one region of the signal. This made-up sample has bass 0.8 and treble 0.2. A direct size connection gives size 0.8 when reading bass.',
    change: 'Try treble instead of bass. The input sample and all other settings stay the same.',
    hint: 'Compare the two feature levels: 0.8 and 0.2. Which one now feeds size?',
    explanation:
      'Size changes from 0.8 to 0.2 because the graph now reads treble. These synthetic levels are not instrument or beat detection.',
  },
  {
    id: 'smooth',
    title: 'Follow changes gradually',
    context:
      'Smoothing follows a rising input over time. At input 0.8, starting from zero, a 100 ms attack reaches about 0.506 after one 100 ms step.',
    change: 'Try a slower 500 ms attack. Both versions start with empty smoothing memory.',
    hint: 'A slower attack moves less toward the same target during one step.',
    explanation:
      'Size changes from about 0.506 to 0.145. The calculation is 0.8 × (1 − exp(−0.1 / attackSeconds)). This is one step, not the eventual steady level.',
  },
  {
    id: 'map',
    title: 'Map a range and see clipping',
    context:
      'Mapping changes a number’s range. Input 0.8 mapped from [0, 1] into [0.4, 1.4] gives 1.2. The renderer limits size to 0.1–2.',
    change: 'Try output range [0.4, 3.4]. The input remains 0.8.',
    hint: 'First calculate 0.4 + 0.8 × (3.4 − 0.4), then apply the size limit of 2.',
    explanation:
      'The map produces 2.8, but rendered size is clipped to 2. A bigger mapped number does not always make a bigger picture.',
  },
] as const
export type ExperimentId = (typeof experiments)[number]['id']
export const experimentFrame: Frame = { bass: 0.8, mid: 0.5, treble: 0.2, rms: 0.6 }
export function experimentPreset(id: ExperimentId, changed: boolean): Preset {
  const nodes: Preset['nodes'] = [
    { id: 'signal', type: 'feature', feature: id === 'feature' && changed ? 'treble' : 'bass' },
  ]
  if (id === 'smooth')
    nodes.push({
      id: 'result',
      type: 'smooth',
      input: 'signal',
      attackMs: changed ? 500 : 100,
      releaseMs: 350,
    })
  if (id === 'map')
    nodes.push({
      id: 'result',
      type: 'map',
      input: 'signal',
      inputRange: [0, 1],
      outputRange: changed ? [0.4, 3.4] : [0.4, 1.4],
    })
  return parsePreset(
    JSON.stringify({
      schemaVersion: 1,
      name: `${id}: ${changed ? 'after' : 'before'}`,
      nodes,
      visual: {
        kind: 'rings',
        color: '#a78bfa',
        scale: id === 'feature' ? 'signal' : 'result',
        energy: 'signal',
      },
    }),
  )
}
export function experimentSnapshot(id: ExperimentId, changed: boolean) {
  const preset = experimentPreset(id, changed)
  const result = evaluate(preset, experimentFrame, 0.1, 0.1, new Map())
  return {
    preset,
    frame: { ...experimentFrame },
    seconds: 0.1,
    dt: 0.1,
    rawSize: result.values.get(preset.visual.scale)!,
    scale: result.scale,
    energy: result.energy,
  }
}
