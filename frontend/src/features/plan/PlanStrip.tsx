import { BLOCK_LABELS, type Block } from './api'

/**
 * The session plan as a strip: which block is current, what is planned, what is optional.
 * Blocks before `firstStarted` were passed over by the learner's "which first?" choice: they are
 * shown as "not started", never struck through like a finished block (honest strip).
 */
export function PlanStrip({
  blocks,
  current,
  firstStarted = null,
}: {
  blocks: Block[]
  current: number
  firstStarted?: number | null
}) {
  if (!blocks.length) return null
  return (
    <ol className="flex flex-wrap gap-2 text-sm" aria-label="Session plan">
      {blocks.map((b, i) => {
        const passedOver = firstStarted != null && i < firstStarted
        const done = !passedOver && i < current
        return (
          <li
            key={i}
            aria-current={i === current ? 'step' : undefined}
            className={
              'rounded-md border px-2 py-1 ' +
              (i === current
                ? 'border-accent bg-accent text-accent-fg'
                : done
                  ? 'border-line text-muted line-through'
                  : passedOver
                    ? 'border-dashed border-line text-muted'
                    : 'border-line')
            }
          >
            {BLOCK_LABELS[b.type] ?? b.type} · {b.planned_min} min{b.optional ? ' · optional' : ''}
            {passedOver ? ' · not started' : ''}
          </li>
        )
      })}
    </ol>
  )
}
