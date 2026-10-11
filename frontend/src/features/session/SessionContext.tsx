import type { SessionOut } from '../../lib/api'
import { BLOCK_LABELS, type Block } from '../plan/api'

/** Display persisted session context, never today's goal preference or next recommendation. */
export function SessionContext({ data, compact = false }: { data: SessionOut; compact?: boolean }) {
  const state = data.state
  const index = state.block_index
  const plan = data.plan as Block[]
  if (state.block_status !== 'running' || index == null || !plan[index]) return null
  const block = plan[index]
  const skill = data.active_skill?.id === state.skill_id ? data.active_skill : null
  const conceptActivity = ['teach', 'assess', 'challenge'].includes(state.phase ?? '')
  return <div className="grid gap-2 mb-3" role="region" aria-label={compact ? 'Current activity summary' : 'Current learning context'}>
    {conceptActivity && <>
      {!compact && <div>
        <h3 className="text-xs text-muted">Learning goal</h3>
        <p className="text-sm">{skill?.description || 'No learning objective is recorded for this concept.'}</p>
      </div>}
      {compact ? <h1 className="text-page-title font-semibold">Learn: {skill?.title || 'Concept unavailable'}</h1>
        : <p className="text-sm"><span className="text-muted">Concept: </span><strong>{skill?.title || 'Concept unavailable'}</strong></p>}
    </>}
    <p className="text-sm text-muted">Activity {index + 1} of {plan.length} · {BLOCK_LABELS[block.type] ?? block.type}
      {block.planned_min != null && <> · about {block.planned_min} min</>}
    </p>
  </div>
}
