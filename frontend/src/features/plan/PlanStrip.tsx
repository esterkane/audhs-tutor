import { BLOCK_LABELS, type Block } from './api'

/** The session plan as a strip: which block is current, what is planned, what is optional. */
export function PlanStrip({ blocks, current }: { blocks: Block[]; current: number }) {
  if (!blocks.length) return null
  return (
    <ol className="flex flex-wrap gap-2 text-sm" aria-label="Session plan">
      {blocks.map((b, i) => (
        <li
          key={i}
          aria-current={i === current ? 'step' : undefined}
          className={
            'rounded-md border px-2 py-1 ' +
            (i === current
              ? 'border-accent bg-accent text-accent-fg'
              : i < current
                ? 'border-line text-muted line-through'
                : 'border-line')
          }
        >
          {BLOCK_LABELS[b.type] ?? b.type} · {b.planned_min} min{b.optional ? ' · optional' : ''}
        </li>
      ))}
    </ol>
  )
}
