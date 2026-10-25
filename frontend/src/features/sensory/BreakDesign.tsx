import { useState } from 'react'
import { Button } from '../../components/ui/button'
import type { BreakDesign as Design } from './comfortStore'

/** Input-driven SVG only: no timers, animation loops, canvas or graphics dependencies. */
export default function BreakDesign({ design }: { design: Exclude<Design, 'off'> }) {
  const [pattern, setPattern] = useState(0)
  return <div className="mt-3 grid gap-3">
    <svg aria-hidden="true" viewBox="0 0 400 160" className="w-full max-w-xl rounded-xl border text-muted"
      style={{ height: '10rem' }} data-break-design={design}>
      <g transform={`translate(200 80) rotate(${pattern * 29 % 360})`} fill="currentColor" fillOpacity="0.16" stroke="currentColor" strokeWidth="1.5">
        {design === 'frost'
          ? Array.from({ length: 6 }, (_, i) => <path key={i} transform={`rotate(${i * 60})`} d="M0 0 L30 -57 L65 -15 Z M0 0 L65 -15 L48 32 Z" />)
          : <><path d="M-100 0 C-110 -65 -20 -70 10 -45 C80 -85 125 -10 80 35 C35 80 -75 70 -100 0Z" /><path d="M-60 0 C-70 -35 -5 -42 20 -20 C65 -35 75 15 40 33 C0 52 -45 40 -60 0Z" /></>}
      </g>
    </svg>
    <Button onClick={() => setPattern(value => (value + 1) % 360)}>Change pattern</Button>
  </div>
}
