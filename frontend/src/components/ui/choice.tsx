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
}: {
  label: string
  options: ChoiceOption<T>[]
  value: T | null
  onChange: (v: T) => void
  columns?: number
  stackOnNarrow?: boolean
}) {
  return (
    <fieldset className="border-0 p-0 m-0 min-w-0 @container">
      <legend className="text-sm font-medium mb-2">{label}</legend>
      <div
        className={`grid gap-2 ${stackOnNarrow ? 'grid-cols-1 @sm:grid-cols-[repeat(var(--choice-columns),minmax(0,1fr))]' : ''}`}
        style={
          stackOnNarrow
            ? ({ '--choice-columns': columns } as CSSProperties)
            : { gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }
        }
      >
        {options.map((o) => (
          <Button
            key={String(o.value)}
            variant={value === o.value ? 'primary' : 'secondary'}
            pressed={value === o.value}
            onClick={() => onChange(o.value)}
            className="flex-col h-auto py-2 items-start text-left min-w-0 max-w-full"
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
