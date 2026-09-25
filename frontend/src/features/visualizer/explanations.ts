import type { Preset } from './engine'
export function describeBlock(preset: Preset, id: string): { mechanism: string; hint: string } | null {
  const node = preset.nodes.find((n) => n.id === id)
  if (!node) return null
  switch (node.type) {
    case 'feature':
      return {
        mechanism: `${id} reads ${node.feature} from the current input. Demo values are synthetic; file values come from local analysis. This is not instrument or beat detection.`,
        hint: 'Keep the rest of the graph fixed and compare a different feature at the same demo sample.',
      }
    case 'constant':
      return {
        mechanism: `${id} always outputs ${node.value}. It does not depend on the audio or time.`,
        hint: 'Use a constant to hold one visual property steady while testing another.',
      }
    case 'map':
      return {
        mechanism: `${id} reads ${node.input}, clips it to ${node.inputRange[0]}–${node.inputRange[1]}, then maps those endpoints to ${node.outputRange[0]} and ${node.outputRange[1]}. The visual may clip the result again: size uses 0.1–2, energy uses 0–1.`,
        hint: 'Predict the output at the two input endpoints before trying a value between them.',
      }
    case 'smooth':
      return {
        mechanism: `${id} follows ${node.input} gradually. Rising values use ${node.attackMs} ms and falling values use ${node.releaseMs} ms as time constants, not fixed completion deadlines. After one time constant about 63% of the gap is closed for a held input.`,
        hint: 'Increase only release, then compare the same demo samples after resetting. Look at how slowly the output falls.',
      }
    case 'lfo':
      return {
        mechanism: `${id} oscillates from 0 to ${node.amplitude} at ${node.frequencyHz} Hz independently of the audio.${node.frequencyHz === 0 ? ' At 0 Hz it stays at half the amplitude.' : ` One cycle takes ${(1 / node.frequencyHz).toFixed(2)} seconds.`}`,
        hint: 'Change frequency while keeping amplitude fixed. Predict whether the movement gets faster or wider.',
      }
  }
}
