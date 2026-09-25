import { useMemo, useState } from 'react'
import { Button } from '../../components/ui/button'
import { demoFrame, evaluate, type Preset } from './engine'
import { describeBlock } from './explanations'

/** Isolated worked example: never reads or mutates the live audio loop's memory. */
export function SampleTrace({ preset }: { preset: Preset }) {
  const [step, setStep] = useState(-1)
  const sample = useMemo(() => {
    const frame = demoFrame(1)
    return { frame, ...evaluate(preset, frame, 1, 0.1, new Map()) }
  }, [preset])
  const node = preset.nodes[step]
  const complete = step === preset.nodes.length
  return (
    <section aria-label="Sample walkthrough" className="grid gap-3">
      <p className="text-sm">
        Walk through the editor draft with one fixed synthetic sample at time 1 second. Smoothing starts at
        zero with a 0.1-second step. This is a separate worked example; it does not change the preview, saved
        preset or audio playback.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => setStep(0)}>
          {step < 0 ? 'Start sample walkthrough' : 'Restart walkthrough'}
        </Button>
        {step >= 0 && (
          <Button
            variant="outline"
            disabled={complete}
            onClick={() => setStep((s) => Math.min(s + 1, preset.nodes.length))}
          >
            Next block
          </Button>
        )}
        {step >= 0 && (
          <Button variant="outline" onClick={() => setStep(-1)}>
            End walkthrough
          </Button>
        )}
      </div>
      {step >= 0 && (
        <div role="status" className="border border-line rounded p-3 grid gap-2 text-sm">
          {node ? (
            <>
              <h3 className="font-medium">
                Block {step + 1} of {preset.nodes.length}: {node.id}
              </h3>
              <p>{describeBlock(preset, node.id)?.mechanism}</p>
              <p>
                {'input' in node
                  ? `Input from ${node.input}: ${sample.values.get(node.input)?.toFixed(3)}`
                  : node.type === 'feature'
                    ? `Synthetic ${node.feature}: ${sample.frame[node.feature].toFixed(3)}`
                    : node.type === 'constant'
                      ? `Fixed value: ${node.value}`
                      : 'Elapsed time: 1 second'}
              </p>
              {node.type === 'smooth' && <p>Previous value: 0.000 · elapsed step: 0.100 s</p>}
              <p>Block output: {sample.values.get(node.id)?.toFixed(3)}</p>
            </>
          ) : (
            <>
              <h3 className="font-medium">Sample reached the visual bindings</h3>
              <p>
                Size from {preset.visual.scale}: {sample.scale.toFixed(3)} (clipped to 0.1–2)
              </p>
              <p>
                Energy from {preset.visual.energy}: {sample.energy.toFixed(3)}{' '}
                {preset.visual.kind === 'rings' ? '(not used by rings)' : '(clipped to 0–1)'}
              </p>
              <p>
                Try changing one input or mapping, then restart and compare this same sample. Blocks with no
                path to a used visual output have no visible effect.
              </p>
            </>
          )}
        </div>
      )}
    </section>
  )
}
