import { useMemo } from 'react'
import { readingMinutes } from './readingTime'

export function ReadingTime({ text }: { text: string }) {
  const minutes = useMemo(() => readingMinutes(text), [text])
  return <details className="text-sm text-muted" aria-label="Estimated reading time">
    <summary>{minutes === null ? 'Reading time varies — no prose estimate' : `Reading time: about ${minutes} min (estimate)`}</summary>
    <p>This is a rough text-only estimate using 200 words per minute, rounded up to whole minutes. It is not your measured pace or time remaining.
      Code, formulas, examples, listening, notes and practice may take longer. There is no countdown or deadline.</p>
  </details>
}
