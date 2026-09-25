import { initial, type Preset } from './engine'
export const examples: Array<{ title: string; description: string; preset: Preset }> = [
  { title: 'Bass rings', description: 'Bass → smoothing → size. Start here.', preset: initial },
  {
    title: 'Treble bars',
    description:
      'Treble drives the bars. Change only the feature to bass within this preset, then compare the same demo sample.',
    preset: {
      ...initial,
      name: 'Treble bars',
      nodes: [{ id: 'signal', type: 'feature', feature: 'treble' }, ...initial.nodes.slice(1)],
      visual: { ...initial.visual, kind: 'bars', color: '#38bdf8' },
    },
  },
  {
    title: 'Slow oscillator',
    description: 'A slow oscillator drives orbiting dots independently of audio.',
    preset: {
      schemaVersion: 1,
      name: 'Slow oscillator',
      nodes: [
        { id: 'wave', type: 'lfo', frequencyHz: 0.2, amplitude: 1 },
        { id: 'size', type: 'map', input: 'wave', inputRange: [0, 1], outputRange: [0.4, 1.2] },
      ],
      visual: { kind: 'orbit', color: '#fbbf24', scale: 'size', energy: 'wave' },
    },
  },
]
