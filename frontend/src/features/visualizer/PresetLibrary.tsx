import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { type Library, readLibrary, writeLibrary } from './library'
import type { Preset } from './engine'
export function PresetLibrary({
  preset,
  onLoad,
  onSaved,
}: {
  onSaved: (id: string) => void
  preset: Preset
  onLoad: (p: Preset, id: string) => void
}) {
  const [state, setState] = useState(() => {
    try {
      return { library: readLibrary(localStorage), error: '' }
    } catch (e) {
      return { library: null, error: (e as Error).message }
    }
  })
  const [name, setName] = useState(preset.name)
  const [notice, setNotice] = useState('')
  function update(next: Library) {
    try {
      writeLibrary(localStorage, next)
      setState({ library: next, error: '' })
      setNotice('Collection saved in this browser. Audio files are not saved.')
      return true
    } catch {
      setNotice(
        'Could not save: browser storage is unavailable or full. Your current picture and draft are kept; use Export applied preset in Create.',
      )
    }
  }
  const library = state.library
  return (
    <section aria-label="Your visual collection" className="grid gap-3">
      <h2 className="font-semibold">Your visual collection</h2>
      <p className="text-sm">
        Save the applied graph visual under a name. Loading a saved visual replaces the editor draft; Undo
        draft recovers it.
      </p>
      {state.error && <p role="alert">{state.error}</p>}
      <label>
        Preset name
        <input
          className="block border border-line rounded bg-card p-2"
          maxLength={80}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <Button
        variant="outline"
        disabled={!library || !name.trim()}
        onClick={() => {
          if (!library) return
          const id = crypto.randomUUID()
          const saved = update({
            ...library,
            active: id,
            items: [
              ...library.items,
              { id, name: name.trim(), favorite: false, preset: { ...preset, name: name.trim() } },
            ],
          })
          if (saved) onSaved(id)
        }}
      >
        Save as new visual
      </Button>
      <div className="grid sm:grid-cols-3 gap-2">
        {library?.items.map((item) => (
          <div key={item.id} className="border border-line rounded p-2 grid gap-2">
            <svg
              viewBox="0 0 120 60"
              role="img"
              aria-label={`${item.name}: ${item.preset.visual.kind} thumbnail, illustrative`}
              className="w-full h-16 bg-slate-900 rounded"
            >
              {item.preset.visual.kind === 'rings'
                ? [12, 20, 27].map((r) => (
                    <circle key={r} cx="60" cy="30" r={r} fill="none" stroke={item.preset.visual.color} />
                  ))
                : item.preset.visual.kind === 'bars'
                  ? [15, 30, 45, 60, 75, 90].map((x, i) => (
                      <rect
                        key={x}
                        x={x}
                        y={12 + (i % 3) * 5}
                        width="9"
                        height={36 - (i % 3) * 10}
                        fill={item.preset.visual.color}
                      />
                    ))
                  : [0, 1, 2, 3, 4, 5].map((i) => (
                      <circle
                        key={i}
                        cx={60 + 24 * Math.cos((i * Math.PI) / 3)}
                        cy={30 + 24 * Math.sin((i * Math.PI) / 3)}
                        r="4"
                        fill={item.preset.visual.color}
                      />
                    ))}
            </svg>
            <Button variant="outline" onClick={() => onLoad(item.preset, item.id)}>
              Load {item.name}
            </Button>
            <Button
              variant="outline"
              aria-pressed={item.favorite}
              onClick={() =>
                update({
                  ...library,
                  items: library.items.map((x) => (x.id === item.id ? { ...x, favorite: !x.favorite } : x)),
                })
              }
            >
              {item.favorite ? 'Unfavorite' : 'Favorite'} {item.name}
            </Button>
            <Button
              variant="outline"
              onClick={() =>
                update({
                  ...library,
                  items: [
                    ...library.items,
                    {
                      ...item,
                      id: crypto.randomUUID(),
                      name: `${item.name.slice(0, 73)} (copy)`,
                      preset: { ...item.preset, name: `${item.name.slice(0, 73)} (copy)` },
                    },
                  ],
                })
              }
            >
              Duplicate {item.name}
            </Button>
          </div>
        ))}
      </div>
      {notice && <p role="status">{notice}</p>}
    </section>
  )
}
