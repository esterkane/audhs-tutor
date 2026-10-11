import { useId } from 'react'

/** Native keyboard/touch behavior with an explicit state label; saves stay caller-owned. */
export function SwitchField({ label, checked, disabled, describedBy, onChange }: {
  label: string
  checked: boolean
  disabled?: boolean
  describedBy?: string
  onChange: (checked: boolean) => void
}) {
  const id = useId()
  return <label htmlFor={id} className="relative isolate flex min-h-control-target items-center justify-between gap-3 rounded-panel border border-line px-3 py-2 text-sm">
    <span className="min-w-0 break-words font-medium">{label}</span>
    <span className="flex shrink-0 items-center gap-2">
      <input id={id} type="checkbox" role="switch" className="peer absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0 disabled:cursor-wait" aria-label={label} aria-describedby={describedBy} checked={checked} disabled={disabled} onChange={event => onChange(event.target.checked)} />
      <span aria-hidden="true" className="relative block h-6 w-10 rounded-full border border-control bg-bg peer-checked:bg-accent peer-focus-visible:outline-2 peer-focus-visible:outline-accent peer-focus-visible:outline-offset-2 peer-disabled:opacity-60">
        <span className={`absolute top-0.5 h-4 w-4 rounded-full ${checked ? 'right-0.5 bg-card' : 'left-0.5 bg-muted'}`} />
      </span>
      <span aria-hidden="true" className="w-6">{checked ? 'On' : 'Off'}</span>
    </span>
  </label>
}
