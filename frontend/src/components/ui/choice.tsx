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
}: {
  label: string
  options: ChoiceOption<T>[]
  value: T | null
  onChange: (v: T) => void
  columns?: number
}) {
  return (
    <fieldset className="border-0 p-0 m-0">
      <legend className="text-sm font-medium mb-2">{label}</legend>
      <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
        {options.map((o) => (
          <Button
            key={String(o.value)}
            variant={value === o.value ? 'primary' : 'secondary'}
            pressed={value === o.value}
            onClick={() => onChange(o.value)}
            className="flex-col h-auto py-2 items-start text-left"
          >
            <span>{o.label}</span>
            {o.hint && <span className="text-xs font-normal opacity-80">{o.hint}</span>}
          </Button>
        ))}
      </div>
    </fieldset>
  )
}
