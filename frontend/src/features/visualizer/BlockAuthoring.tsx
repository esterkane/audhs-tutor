import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { type Preset } from './engine'
import { addBlock, removeBlock, type BlockType } from './authoring'

export function BlockAuthoring({ preset, onChange }: { preset: Preset; onChange: (p: Preset) => void }) {
  const [type, setType] = useState<BlockType>('feature')
  const [input, setInput] = useState('')
  const [remove, setRemove] = useState('')
  const [note, setNote] = useState('')
  const inputId = preset.nodes.some((n) => n.id === input) ? input : preset.nodes[0].id
  const removeId = preset.nodes.some((n) => n.id === remove) ? remove : preset.nodes[0].id
  function edit(action: () => Preset, success: string) {
    try {
      onChange(action())
      setNote(success)
    } catch (e) {
      setNote((e as Error).message)
    }
  }
  return (
    <details>
      <summary className="cursor-pointer">Add or remove blocks (optional)</summary>
      <div className="grid gap-3 mt-3">
        <p className="text-sm">
          New blocks start disconnected from the picture. Connect them in Signal flow diagram, then Apply
          preset. Change their values in Block controls.
        </p>
        <label className="grid gap-1 text-sm">
          New block type
          <select
            className="bg-card border border-line rounded p-2"
            value={type}
            onChange={(e) => setType(e.target.value as BlockType)}
          >
            <option value="feature">Sound feature — read a frequency region or amplitude</option>
            <option value="constant">Fixed value — keep one number</option>
            <option value="map">Map range — turn an input into a different range</option>
            <option value="smooth">Smooth — follow changes gradually</option>
            <option value="lfo">Slow oscillator — vary a number with time</option>
          </select>
        </label>
        {(type === 'map' || type === 'smooth') && (
          <label className="grid gap-1 text-sm">
            Input for new block
            <select
              className="bg-card border border-line rounded p-2"
              value={inputId}
              onChange={(e) => setInput(e.target.value)}
            >
              {preset.nodes.map((n) => (
                <option key={n.id}>{n.id}</option>
              ))}
            </select>
          </label>
        )}
        <Button
          variant="outline"
          onClick={() =>
            edit(() => addBlock(preset, type, inputId), 'Block added to draft. Connect it when ready.')
          }
          disabled={preset.nodes.length >= 32}
        >
          Add block
        </Button>
        <p className="text-xs text-muted">
          {preset.nodes.length} of 32 blocks. Removal is refused while another block or visual binding uses
          it.
        </p>
        <label className="grid gap-1 text-sm">
          Block to remove
          <select
            className="bg-card border border-line rounded p-2"
            value={removeId}
            onChange={(e) => setRemove(e.target.value)}
          >
            {preset.nodes.map((n) => (
              <option key={n.id}>{n.id}</option>
            ))}
          </select>
        </label>
        <Button
          variant="outline"
          onClick={() =>
            edit(() => removeBlock(preset, removeId), 'Block removed from draft. Undo draft restores it.')
          }
        >
          Remove block
        </Button>
        {note && (
          <p role="status" className="text-sm">
            {note}
          </p>
        )}
      </div>
    </details>
  )
}
