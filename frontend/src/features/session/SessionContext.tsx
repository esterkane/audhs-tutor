import { LearningBreadcrumbs } from '../../components/LearningBreadcrumbs'
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
  const subject = conceptActivity ? skill?.domain : block.domain
  return <div className="grid gap-2 mb-3" role="region" aria-label={compact ? 'Current activity summary' : 'Current learning context'}>
    {compact && <LearningBreadcrumbs items={[
      subject ? (({ ai_ml: 'AI and machine learning', programming: 'Programming', language: 'Language', guitar: 'Guitar', movement: 'Movement' } as Record<string, string>)[subject] ?? subject.replaceAll('_', ' ')) : 'Learning session',
      conceptActivity ? (skill?.title || 'Concept unavailable') : (BLOCK_LABELS[block.type] ?? block.type),
      ({ teach: 'Explanation', assess: 'Understanding check', challenge: 'Challenge', practice: 'Practice', review: 'Review', recap: 'Recap' } as Record<string, string>)[state.phase ?? ''] ?? 'Current activity',
    ]} />}
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
    {state.first_started_index != null && state.first_started_index > 0 && plan[state.first_started_index] &&
      <p className="text-sm text-muted">Started with {BLOCK_LABELS[plan[state.first_started_index].type] ?? plan[state.first_started_index].type}; earlier planned activities were skipped at the start.</p>}
  </div>
}
