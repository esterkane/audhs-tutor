import { useEffect, useRef } from 'react'
import { Button } from '../../components/ui/button'
import { ApiError } from '../../lib/api'
import { useAdaptationLog, useRefreshPlan, type ProposalOut } from './api'

export function PlanPreview({ proposal }: { proposal: ProposalOut }) {
  const remaining = (proposal.plan_blocks ?? []).slice(proposal.protected_blocks ?? 0)
  return <div className="my-3 text-sm">
    <p>Completed and current activities stay unchanged, including the current timer.</p>
    <p className="font-semibold mt-2">Proposed remaining activities · {remaining.reduce((sum, b) => sum + b.planned_min, 0)} min</p>
    {remaining.length ? <ol className="list-decimal pl-5">{remaining.map((b, i) => <li key={i}>{b.type.replaceAll('_', ' ')} · {b.planned_min} min</li>)}</ol> : <p>No future activities to change.</p>}
  </div>
}

export function PlanRecovery({ id, fromUndo = false }: { id: string; fromUndo?: boolean }) {
  const refresh = useRefreshPlan()
  const { decide } = useAdaptationLog()
  const heading = useRef<HTMLHeadingElement>(null)
  const proposal = refresh.data
  useEffect(() => { if (proposal) heading.current?.focus() }, [proposal])
  const stale = decide.error instanceof ApiError && decide.error.code === 'stale_plan'
  return <div className="my-3 rounded border border-border p-3">
    <p className="text-sm">The session has changed. Keep your current activity and review a new proposal before changing future activities.</p>
    <Button className="mt-2 whitespace-normal" disabled={refresh.isPending || decide.isPending} onClick={() => { decide.reset(); refresh.mutate(id) }}>
      {refresh.isPending ? 'Preparing preview…' : 'Review an updated plan'}
    </Button>
    {(proposal || !fromUndo) && <div className="mt-2 flex flex-wrap gap-2">
      <Button variant="ghost" disabled={refresh.isPending || decide.isPending} onClick={() => decide.mutate({ id: proposal?.id ?? id, decision: 'no', sessionId: proposal?.session_id ?? null })}>Not now</Button>
      <Button variant="ghost" disabled={refresh.isPending || decide.isPending} onClick={() => decide.mutate({ id: proposal?.id ?? id, decision: 'never', sessionId: proposal?.session_id ?? null })}>Don't suggest this again</Button>
    </div>}
    {refresh.isError && <p role="alert">Could not prepare the preview. {refresh.error.message}</p>}
    {proposal && <section aria-label="Updated plan preview">
      <h4 ref={heading} tabIndex={-1} className="mt-3 font-semibold">Updated plan — not applied</h4>
      <p className="text-sm">{proposal.why}</p>
      <PlanPreview proposal={proposal} />
      <Button disabled={decide.isPending || refresh.isPending || decide.isSuccess || stale} onClick={() => decide.mutate({ id: proposal.id, decision: 'try', sessionId: proposal.session_id ?? null })}>Apply reviewed plan</Button>
      {decide.isSuccess && decide.variables?.decision === 'try' && <p role="status">Updated plan applied.</p>}
    </section>}
    {decide.isError && <p role="alert">{decide.error.message}</p>}
  </div>
}
