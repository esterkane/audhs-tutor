import { parsePreset, type Preset } from './engine'

// Output IDs contain a colon, which validated preset node IDs cannot contain.
export function connectPreset(preset: Preset, source: string, target: string): Preset {
  if (!preset.nodes.some((n) => n.id === source)) throw new Error('Choose an existing source block.')
  const next = structuredClone(preset)
  if (target === 'output:scale' || target === 'output:energy') {
    next.visual[target === 'output:scale' ? 'scale' : 'energy'] = source
  } else {
    const node = next.nodes.find((n) => n.id === target)
    if (!node || !('input' in node)) throw new Error('Only map and smooth blocks accept an input.')
    node.input = source
  }
  // One validator for JSON, dropdowns and canvas gestures; cycles never reach the draft.
  return parsePreset(JSON.stringify(next))
}
