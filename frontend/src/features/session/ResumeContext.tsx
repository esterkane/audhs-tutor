import type { SessionOut } from '../../lib/api'
import { BLOCK_LABELS } from '../plan/api'

/** A checkpoint says where to return, not which work was completed or how much time remains. */
export function ResumeContext({ session }: { session: SessionOut }) {
  const state = session.state
  const index = state?.block_index
  const block = !state?.plan_complete && state?.block_status === 'running' && index != null ? session.plan?.[index] : null
  const phase = state?.phase
  const step = phase === 'teach' ? 'Explanation'
    : phase === 'assess' ? 'Understanding check'
    : phase === 'review' ? 'Review'
    : phase === 'challenge' ? 'Challenge'
    : phase === 'practice' ? 'Practice'
    : phase === 'recap' ? 'Recap' : null
  const minutes = block?.planned_min
  return <>
    {block && typeof block.type === 'string' && <p className="text-sm mt-2">
      Saved activity: {BLOCK_LABELS[block.type] ?? 'Learning activity'}{step ? ` · ${step}` : ''}.
    </p>}
    {typeof minutes === 'number' && Number.isFinite(minutes) && minutes > 0 && <p className="text-sm text-muted">
      Planned activity: about {minutes} min. This is the original plan, not time remaining.
    </p>}
  </>
}
