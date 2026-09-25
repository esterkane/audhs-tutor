import { Button } from '../../components/ui/button'
import type { Preset } from './engine'

/** Explicit edge rows avoid implying that adjacent, independent nodes are connected. */
export function SignalFlow({
  preset,
  draft,
  selected,
  onInspect,
}: {
  preset: Preset
  draft: boolean
  selected: string
  onInspect: (id: string) => void
}) {
  const block = (id: string) => (
    <Button variant="outline" aria-pressed={selected === id} onClick={() => onInspect(id)}>
      Inspect {id}
    </Button>
  )
  return (
    <section aria-label="Signal flow" className="grid gap-3">
      <p className="text-sm">
        {draft ? 'Draft connections — Apply to use them.' : 'Applied connections.'} Each row shows one
        connection. Select a block for its explanation in the Learning guide.
      </p>
      <ul className="grid gap-2" aria-label="Block connections">
        {preset.nodes.map((node) => (
          <li
            key={node.id}
            className="flex flex-wrap items-center gap-2 border border-line rounded p-2 text-sm"
          >
            {'input' in node ? (
              block(node.input)
            ) : (
              <span>
                {node.type === 'feature'
                  ? `Audio or demo: ${node.feature}`
                  : node.type === 'constant'
                    ? 'Fixed number'
                    : 'Elapsed time (independent of audio)'}
              </span>
            )}
            <span aria-hidden="true">→</span>
            <span className="sr-only">feeds</span>
            {block(node.id)}
            <span>({node.type})</span>
          </li>
        ))}
      </ul>
      <div className="border border-line rounded p-3 grid gap-2 text-sm" aria-label="Visual connections">
        <p className="font-medium">Visual output: {preset.visual.kind}</p>
        <div className="flex flex-wrap gap-2 items-center">
          {block(preset.visual.scale)}
          <span>→ size (clipped to 0.1–2)</span>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          {block(preset.visual.energy)}
          <span>
            {preset.visual.kind === 'rings' ? '→ energy (not used by rings)' : '→ energy (clipped to 0–1)'}
          </span>
        </div>
      </div>
      <p className="text-xs text-muted">
        Connections describe this lab’s implementation. Blocks with no path to an output used by this visual
        style do not affect the visual.
      </p>
    </section>
  )
}
