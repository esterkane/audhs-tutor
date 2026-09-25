import { useId, useMemo, useState } from 'react'
import { Button } from '../../components/ui/button'
import { parsePreset, type Preset } from './engine'

export function PresetControls({
  text,
  onChange,
  onInspect,
}: {
  text: string
  onChange: (text: string) => void
  onInspect: (id: string) => void
}) {
  const uid = useId()
  const [note, setNote] = useState('')
  const parsed = useMemo(() => {
    try {
      return parsePreset(text)
    } catch {
      return null
    }
  }, [text])
  function write(p: Preset) {
    onChange(JSON.stringify(p, null, 2))
    setNote('Draft updated. Apply preset to see the change.')
  }
  if (!parsed)
    return (
      <p className="text-sm">
        Controls need a valid preset. Fix the JSON below or load an example into the editor. The working
        visual is unchanged.
      </p>
    )
  const p = parsed
  function nodeChange(id: string, field: string, value: unknown) {
    write({ ...p, nodes: p.nodes.map((n) => (n.id === id ? { ...n, [field]: value } : n)) } as Preset)
  }
  function numberControl(
    node: string,
    field: string,
    label: string,
    value: number,
    min: number,
    max: number,
    step: number,
    writeValue?: (v: number) => void,
  ) {
    const key = `${uid}-${node}-${field}`
    return (
      <label className="grid gap-1 text-sm" htmlFor={key}>
        {label}
        <input
          id={key}
          type="number"
          min={min}
          max={max}
          step={step}
          key={`${key}-${value}`}
          defaultValue={value}
          className="border border-line bg-card rounded p-2 w-full"
          onKeyDown={(e) => {
            if (e.key === 'Enter') e.currentTarget.blur()
          }}
          onBlur={(e) => {
            const v = Number(e.target.value)
            if (e.target.value.trim() && Number.isFinite(v) && v >= min && v <= max) {
              if (writeValue) writeValue(v)
              else nodeChange(node, field, v)
            } else {
              e.target.value = String(value)
              setNote(`${label}: enter a number between ${min} and ${max}. The previous value was kept.`)
            }
          }}
        />
      </label>
    )
  }
  return (
    <div className="grid gap-3">
      <p className="text-sm text-muted">
        Choose a shape and color. Apply preset updates the picture; your saved settings stay unchanged until
        you save.
      </p>
      <div className="grid sm:grid-cols-2 gap-3">
        <label className="grid gap-1 text-sm">
          Visual style
          <select
            className="border border-line bg-card rounded p-2"
            value={p.visual.kind}
            onChange={(e) =>
              write({ ...p, visual: { ...p.visual, kind: e.target.value as Preset['visual']['kind'] } })
            }
          >
            <option value="rings">Rings</option>
            <option value="bars">Bars</option>
            <option value="orbit">Orbit</option>
          </select>
        </label>
        <label className="grid gap-1 text-sm">
          Visual color
          <input
            type="color"
            value={p.visual.color}
            onChange={(e) => write({ ...p, visual: { ...p.visual, color: e.target.value } })}
          />
        </label>
      </div>
      <details>
        <summary className="cursor-pointer">Block controls ({p.nodes.length})</summary>
        <div className="grid gap-3 mt-3">
          {p.nodes.map((n) => (
            <fieldset key={n.id} className="border border-line rounded p-3 grid gap-2">
              <legend className="px-1 font-medium">
                {n.id} · {n.type}
              </legend>
              {'input' in n && <p className="text-xs text-muted">Input: {n.input}</p>}
              {n.type === 'feature' && (
                <label className="grid gap-1 text-sm">
                  Feature for {n.id}
                  <select
                    className="border border-line bg-card rounded p-2"
                    value={n.feature}
                    onChange={(e) => nodeChange(n.id, 'feature', e.target.value)}
                  >
                    {['bass', 'mid', 'treble', 'rms'].map((f) => (
                      <option key={f}>{f}</option>
                    ))}
                  </select>
                </label>
              )}
              {n.type === 'smooth' && (
                <div className="grid sm:grid-cols-2 gap-2">
                  {numberControl(n.id, 'attackMs', `Attack for ${n.id} (ms)`, n.attackMs, 1, 10000, 1)}
                  {numberControl(n.id, 'releaseMs', `Release for ${n.id} (ms)`, n.releaseMs, 1, 10000, 1)}
                  <p className="text-xs text-muted sm:col-span-2">
                    Attack follows rising values; release follows falling values. Larger times change more
                    slowly.
                  </p>
                </div>
              )}
              {n.type === 'map' && (
                <>
                  <p className="text-sm">
                    Input range: {n.inputRange[0]} to {n.inputRange[1]}
                  </p>
                  <div className="grid sm:grid-cols-2 gap-2">
                    {numberControl(
                      n.id,
                      'low',
                      `Output start for ${n.id}`,
                      n.outputRange[0],
                      -100,
                      100,
                      0.1,
                      (v) => nodeChange(n.id, 'outputRange', [v, n.outputRange[1]]),
                    )}
                    {numberControl(
                      n.id,
                      'high',
                      `Output end for ${n.id}`,
                      n.outputRange[1],
                      -100,
                      100,
                      0.1,
                      (v) => nodeChange(n.id, 'outputRange', [n.outputRange[0], v]),
                    )}
                  </div>
                  <p className="text-xs text-muted">
                    Visual size is limited to 0.1–2; energy to 0–1. Values outside those limits are clipped at
                    the visual output.
                  </p>
                </>
              )}
              {n.type === 'constant' &&
                numberControl(n.id, 'value', `Value for ${n.id}`, n.value, -100, 100, 0.1)}
              {n.type === 'lfo' && (
                <div className="grid sm:grid-cols-2 gap-2">
                  {numberControl(
                    n.id,
                    'frequencyHz',
                    `Frequency for ${n.id} (Hz)`,
                    n.frequencyHz,
                    0,
                    2,
                    0.05,
                  )}
                  {numberControl(n.id, 'amplitude', `Amplitude for ${n.id}`, n.amplitude, 0, 2, 0.1)}
                </div>
              )}
              <Button variant="outline" onClick={() => onInspect(n.id)}>
                Explain {n.id}
              </Button>
            </fieldset>
          ))}
        </div>
      </details>
      {note && (
        <p className="text-sm" role="status">
          {note}
        </p>
      )}
    </div>
  )
}
