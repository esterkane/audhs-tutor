import type { CSSProperties } from 'react'
import { Button } from './button'

export type ChoiceOption<T extends string | number> = {
  value: T
  label: string
  hint?: string
}

/** 2–5 concrete options as an accessible toggle group ("Which next?", never an open prompt). */
export function Choice<T extends string | number>({
  label,
  options,
  value,
  onChange,
  columns = 3,
  stackOnNarrow = false,
  describedBy,
  segmented = false,
  selectionTone = 'strong',
}: {
  label: string
  options: ChoiceOption<T>[]
  value: T | null
  onChange: (v: T) => void
  columns?: number
  stackOnNarrow?: boolean
  describedBy?: string
  segmented?: boolean
  selectionTone?: 'strong' | 'quiet'
}) {
  return (
    <fieldset aria-describedby={describedBy} className="border-0 p-0 m-0 min-w-0 @container">
      <legend className="text-sm font-medium mb-2">{label}</legend>
      <div
        className={`grid ${segmented ? 'gap-1 rounded-panel border border-control bg-sunken p-1' : 'gap-2'} ${stackOnNarrow ? 'grid-cols-1 @sm:grid-cols-[repeat(var(--choice-columns),minmax(0,1fr))]' : ''}`}
        style={
          stackOnNarrow
            ? ({ '--choice-columns': columns } as CSSProperties)
            : { gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }
        }
      >
        {options.map((o) => (
          <Button
            key={String(o.value)}
            variant={segmented ? 'ghost' : value === o.value && selectionTone === 'strong' ? 'primary' : 'secondary'}
            pressed={value === o.value}
            onClick={() => onChange(o.value)}
            className={`${!segmented && selectionTone === 'quiet' && value === o.value ? 'before:bg-accent-tint hover:before:bg-accent-tint text-fg' : ''} flex-col h-auto py-2 items-start text-left min-w-0 max-w-full ${segmented ? `text-fg ${value === o.value ? 'before:bg-card hover:before:bg-card' : 'hover:before:bg-card'}` : ''}`}
          >
            <span className="max-w-full [overflow-wrap:anywhere]">{o.label}</span>
            {o.hint && (
              <span className="text-xs font-normal opacity-80 max-w-full [overflow-wrap:anywhere]">
                {o.hint}
              </span>
            )}
          </Button>
        ))}
      </div>
    </fieldset>
  )
}
