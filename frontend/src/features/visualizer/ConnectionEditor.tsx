import { lazy, Suspense, useState } from 'react'
import { Button } from '../../components/ui/button'
import { connectPreset } from './connections'
import type { Preset } from './engine'
const BlockCanvas = lazy(() => import('./BlockCanvas'))
export function ConnectionEditor({
  preset,
  onChange,
  onInspect,
}: {
  preset: Preset
  onChange: (preset: Preset) => void
  onInspect: (id: string) => void
}) {
  const [canvas, setCanvas] = useState(false)
  const [message, setMessage] = useState('')
  function change(source: string, target: string) {
    try {
      onChange(connectPreset(preset, source, target))
      setMessage('Connection updated in the draft. Apply preset to use it.')
    } catch (e) {
      setMessage(`Connection rejected; previous draft kept. ${e instanceof Error ? e.message : ''}`)
    }
  }
  const targets = [
    ...preset.nodes.flatMap((n) =>
      'input' in n ? [{ id: n.id, name: `Input for ${n.id}`, value: n.input }] : [],
    ),
    { id: 'output:scale', name: 'Source for visual size', value: preset.visual.scale },
    {
      id: 'output:energy',
      name:
        preset.visual.kind === 'rings' ? 'Source for energy (unused by rings)' : 'Source for visual energy',
      value: preset.visual.energy,
    },
  ]
  return (
    <section aria-label="Edit block connections" className="grid gap-3">
      <Button variant="outline" onClick={() => setCanvas(!canvas)} aria-expanded={canvas}>
        {canvas ? 'Hide block canvas' : 'Open block canvas'}
      </Button>
      {canvas && (
        <Suspense fallback={<p>Loading local block editor…</p>}>
          <BlockCanvas preset={preset} onChange={onChange} onInspect={onInspect} />
        </Suspense>
      )}
      <p className="text-sm">
        Choose which block feeds each input. A new connection replaces the existing one. Cycles are rejected.
        Apply remains explicit.
      </p>
      <div className="grid sm:grid-cols-2 gap-2">
        {targets.map((t) => (
          <label key={t.id} className="grid gap-1 text-sm">
            {t.name}
            <select
              className="border border-line rounded bg-card p-2"
              value={t.value}
              onChange={(e) => change(e.target.value, t.id)}
            >
              {preset.nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.id} · {n.type}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
      {message && (
        <p role="status" className="text-sm">
          {message}
        </p>
      )}
    </section>
  )
}
