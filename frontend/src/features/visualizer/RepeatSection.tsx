import { useState } from 'react'
import { Button } from '../../components/ui/button'
export function RepeatSection({
  duration,
  enabled,
  active,
  onChange,
}: {
  duration: number
  enabled: boolean
  active: { start: number; end: number } | null
  onChange: (range: { start: number; end: number } | null) => void
}) {
  const [start, setStart] = useState('0')
  const [end, setEnd] = useState('5')
  const [error, setError] = useState('')
  function apply() {
    const a = Number(start),
      b = Number(end)
    if (
      !start.trim() ||
      !end.trim() ||
      !Number.isFinite(a) ||
      !Number.isFinite(b) ||
      a < 0 ||
      b > duration ||
      b - a < 0.5
    ) {
      setError(`Choose a section at least 0.5 seconds long, between 0 and ${duration.toFixed(1)} seconds.`)
      return
    }
    setError('')
    onChange({ start: a, end: b })
  }
  return (
    <details>
      <summary className="cursor-pointer">Repeat a short section (optional)</summary>
      <div className="grid gap-2 mt-2">
        <p className="text-sm">
          After Play, choose a passage to repeat while comparing visual settings. Enable repeat jumps to its
          start; if paused, Resume starts it. Boundaries are approximate, not sample-accurate audio editing.
        </p>
        <div className="grid grid-cols-2 gap-2">
          <label className="grid gap-1 text-sm">
            Section start (seconds)
            <input
              className="border border-line rounded bg-card p-2 w-full"
              type="number"
              min={0}
              step={0.1}
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </label>
          <label className="grid gap-1 text-sm">
            Section end (seconds)
            <input
              className="border border-line rounded bg-card p-2 w-full"
              type="number"
              min={0}
              step={0.1}
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </label>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button onClick={apply} disabled={!enabled || !duration}>
            {active ? 'Update repeat section' : 'Enable repeat'}
          </Button>
          <Button
            onClick={() => {
              onChange(null)
              setError('')
            }}
            disabled={!active}
          >
            Turn repeat off
          </Button>
        </div>
        <p className="text-sm" role="status">
          {active
            ? `Repeat on: ${active.start.toFixed(1)}–${active.end.toFixed(1)} seconds. Stop turns repeat off.`
            : enabled
              ? 'Repeat off. Choose a section and enable repeat.'
              : 'Repeat off. Start playback first to enable it.'}
        </p>
        {error && <p role="alert">{error}</p>}
      </div>
    </details>
  )
}
