import { parsePreset, type Preset } from './engine'

export type BlockType = Preset['nodes'][number]['type']
export function addBlock(preset: Preset, type: BlockType, input: string): Preset {
  if (preset.nodes.length >= 32) throw new Error('The limit is 32 blocks. Remove an unused block first.')
  let index = 1
  while (preset.nodes.some((n) => n.id === `${type}_${index}`)) index++
  const id = `${type}_${index}`
  const node =
    type === 'feature'
      ? { id, type, feature: 'bass' as const }
      : type === 'constant'
        ? { id, type, value: 0.5 }
        : type === 'lfo'
          ? { id, type, frequencyHz: 0.2, amplitude: 1 }
          : type === 'map'
            ? { id, type, input, inputRange: [0, 1], outputRange: [0.4, 1.4] }
            : { id, type, input, attackMs: 40, releaseMs: 350 }
  return parsePreset(JSON.stringify({ ...preset, nodes: [...preset.nodes, node] }))
}
export function removeBlock(preset: Preset, id: string): Preset {
  if (!preset.nodes.some((n) => n.id === id)) throw new Error('Choose an existing block.')
  const uses = preset.nodes.filter((n) => 'input' in n && n.input === id).map((n) => n.id)
  if (preset.visual.scale === id) uses.push('visual size')
  if (preset.visual.energy === id) uses.push('visual energy (including unused bindings)')
  if (uses.length)
    throw new Error(
      `Cannot remove ${id}: used by ${uses.join(', ')}. Reconnect these in Signal flow diagram first.`,
    )
  return parsePreset(JSON.stringify({ ...preset, nodes: preset.nodes.filter((n) => n.id !== id) }))
}
export async function readPresetFile(file: File): Promise<Preset> {
  if (file.size > 16000) throw new Error('Preset file exceeds 16,000 bytes.')
  return parsePreset(await file.text())
}
