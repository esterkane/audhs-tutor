import { BLOCK_LABELS, type Block } from './api'

/** Literal labels for "which first?": say what starts and what is passed over. */
export function startLabel(plan: Block[], index: number, skillTitle?: string | null): string {
  const b = plan[index]
  const label = BLOCK_LABELS[b.type] ?? b.type
  const head =
    b.type === 'movement_primer'
      ? `Move (${b.planned_min} min), then new material${skillTitle ? `: ${skillTitle}` : ''}`
      : b.type === 'new_material'
        ? `New material${skillTitle ? `: ${skillTitle}` : ''}`
        : `Start with ${label}`
  return head + skipNote(plan, index)
}

export function skipNote(plan: Block[], index: number): string {
  const skipped = plan.slice(0, index).map((b) => BLOCK_LABELS[b.type] ?? b.type)
  return skipped.length ? ` — skips ${skipped.join(' and ')}` : ''
}
