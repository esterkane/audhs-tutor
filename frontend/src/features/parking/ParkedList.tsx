import { Button } from '../../components/ui/button'
import { useParked, useParkingActions } from './api'

/** Parked tangents with the two concrete next steps: promote (to the next session) or drop. */
export function ParkedList() {
  const parked = useParked('parked')
  const { promote, drop } = useParkingActions()
  const items = parked.data?.items ?? []
  if (items.length === 0) return <p className="text-sm text-muted">Nothing parked.</p>
  return (
    <ul className="grid gap-1 text-sm" aria-label="Parked tangents">
      {items.map((p) => (
        <li key={p.id} className="flex flex-wrap items-center gap-2">
          <span className="grow">{p.text}</span>
          <Button size="sm" onClick={() => promote.mutate({ id: p.id, to: 'next_session' })}>
            Promote to next session
          </Button>
          <Button size="sm" variant="ghost" onClick={() => drop.mutate(p.id)}>
            Drop
          </Button>
        </li>
      ))}
    </ul>
  )
}

/** Promoted items: a reminder on Home until the learner marks them done. */
export function PromotedReminders() {
  const promoted = useParked('promoted')
  const { drop } = useParkingActions()
  const items = promoted.data?.items ?? []
  if (items.length === 0) return null
  return (
    <div className="rounded-lg border border-line bg-card p-4 shadow-sm">
      <p className="font-medium mb-1">You promoted these for this session</p>
      <ul className="grid gap-1 text-sm">
        {items.map((p) => (
          <li key={p.id} className="flex flex-wrap items-center gap-2">
            <span className="grow">{p.text}</span>
            <Button size="sm" variant="ghost" onClick={() => drop.mutate(p.id)}>
              Done
            </Button>
          </li>
        ))}
      </ul>
    </div>
  )
}
