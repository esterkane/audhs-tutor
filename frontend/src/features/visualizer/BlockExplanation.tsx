import type { Preset } from './engine'
import { describeBlock } from './explanations'
export function BlockExplanation({
  preset,
  id,
  values,
  draft,
}: {
  preset: Preset
  id: string
  values: Map<string, number>
  draft: boolean
}) {
  const explanation = describeBlock(preset, id)
  if (!explanation) return <p className="text-sm">Choose a block with its Explain button.</p>
  return (
    <section className="border border-line rounded p-3 grid gap-2" aria-label="Block explanation">
      <h3 className="font-medium">About {id}</h3>
      <p className="text-xs text-muted">
        Calculated locally from {draft ? 'the editor draft' : 'the applied preset'} · no AI request
      </p>
      <p className="text-sm" role="status">
        {explanation.mechanism}
      </p>
      {!draft && <p className="text-sm">Last displayed block value: {(values.get(id) ?? 0).toFixed(3)}</p>}
      {draft && (
        <p className="text-sm">
          Apply the draft to inspect its output; current visual values belong to the previous preset.
        </p>
      )}
      <details>
        <summary className="cursor-pointer">Try one change</summary>
        <p className="text-sm mt-2">{explanation.hint}</p>
      </details>
    </section>
  )
}
