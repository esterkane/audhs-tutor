import { ApiError, type Schemas } from '../../lib/api'
import { OriginalLesson } from './OriginalLesson'
import { Link } from 'react-router-dom'
import { thoughtContextPath } from './context'
import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { useParked, useParkingActions, type ParkOut } from './api'

export function ParkedList({ onOpenContext }: { onOpenContext?: () => void } = {}) { return <ThoughtList status="parked" onOpenContext={onOpenContext} /> }
export function PromotedReminders() { return <ThoughtList status="promoted" /> }

type ActionIntent = { id: string; text: string; body: Schemas['ThoughtActionIn'] }

/** These are optional reminders, never evidence of learning or completed work. */
function ThoughtList({ status, onOpenContext }: { status: 'parked' | 'promoted'; onOpenContext?: () => void }) {
  const query = useParked(status)
  const { change } = useParkingActions()
  const lock = useRef(false)
  const removeButtons = useRef<Record<string, HTMLButtonElement | null>>({})
  const feedback = useRef<HTMLParagraphElement>(null)
  const [pending, setPending] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<string | null>(null)
  const [result, setResult] = useState<{ error: boolean; text: string } | null>(null)
  const [retry, setRetry] = useState<ActionIntent | null>(null)
  const [undo, setUndo] = useState<{ id: string; text: string; revision: number; receipt: string } | null>(null)
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  function act(item: ParkOut, action: 'promote' | 'drop') {
    void perform({ id: item.id, text: item.text, body: { promoted_to: 'next_session', request_key: crypto.randomUUID(), expected_revision: item.revision ?? 0, action } })
  }
  async function perform(intent: ActionIntent) {
    if (lock.current) return
    lock.current = true
    setPending(intent.id)
    setResult(null)
    setUndo(null)
    const origin = document.activeElement
    try {
      const response = await change.mutateAsync({ id: intent.id, body: intent.body })
      if (!mounted.current) return
      setRetry(null)
      setConfirm(null)
      const current = response.item
      const description = current.status === 'parked' ? 'In Saved thoughts' : current.status === 'promoted' ? (current.promoted_to === 'next_session' ? 'Shown on Home' : 'Linked to a skill') : 'Removed from reminders'
      setResult({ error: false, text: `${description}: ${intent.text}${current.revision !== response.action_revision ? '. A newer change is already applied; the original action was not repeated.' : ''}` })
      if (response.can_undo) setUndo({ id: intent.id, text: intent.text, revision: response.action_revision, receipt: response.action_id })
    } catch (error) {
      if (!mounted.current) return
      const conflict = error instanceof ApiError && [404, 409, 422].includes(error.status)
      setRetry(conflict ? null : intent)
      setResult({ error: true, text: conflict ? `This thought changed or is no longer available. The requested change was not applied. Check the refreshed list.` : `Could not confirm the change to “${intent.text}”. Retry this same action to check its result without applying it twice. Keep this view open to retain that retry.` })
    } finally {
      lock.current = false
      if (mounted.current) setPending(null)
      // Keep focus if the learner has moved elsewhere while waiting.
      if (mounted.current && (document.activeElement === origin || (origin instanceof HTMLButtonElement && (!origin.isConnected || origin.disabled) && document.activeElement === document.body))) {
        requestAnimationFrame(() => {
          if (document.activeElement === origin || (origin instanceof HTMLButtonElement && (!origin.isConnected || origin.disabled) && document.activeElement === document.body)) feedback.current?.focus()
        })
      }
    }
  }
  const items = query.data?.items ?? []
  if (status === 'promoted' && !query.isPending && !query.isError && !items.length && !result) return null
  return (
    <div className={status === 'promoted' ? 'rounded-lg border border-line bg-card p-4 shadow-sm' : ''}>
      {status === 'promoted' && <p className="font-medium mb-1">Thoughts to revisit</p>}
      <p ref={feedback} tabIndex={-1} role={result?.error ? 'alert' : 'status'} className="text-sm">
        {result?.text ?? (pending ? 'Updating thought…' : '')}
      </p>
      {retry && <Button size="sm" disabled={pending !== null} onClick={() => void perform(retry)}>Retry same action</Button>}
      {undo && <div className="my-2 grid gap-1">
        <Button size="sm" disabled={pending !== null || retry !== null} onClick={() => void perform({ id: undo.id, text: undo.text, body: { promoted_to: 'next_session', action: 'undo', request_key: crypto.randomUUID(), expected_revision: undo.revision, undo_of: undo.receipt } })}>Undo last change</Button>
        <p className="text-sm text-muted">Restores the previous reminder state for “{undo.text}”. Available here until another change or you leave this view.</p>
      </div>}
      {query.isPending ? <p role="status">Loading saved thoughts…</p> : query.isError ? (
        <p role="alert">Could not load saved thoughts. <Button onClick={() => void query.refetch()}>Retry saved thoughts</Button></p>
      ) : !items.length ? <p className="text-sm text-muted">{status === 'parked' ? 'No saved thoughts.' : 'No thoughts to revisit.'}</p> : (
        <ul className="grid gap-3 text-sm" aria-label={status === 'parked' ? 'Saved thoughts' : 'Thoughts to revisit'}>
          {items.map(p => (
            <li key={p.id} className="flex flex-wrap items-center gap-2">
              <span className="grow">{p.text}</span>
              {p.original_context?.kind === 'lesson' && <OriginalLesson context={p.original_context} onOpen={onOpenContext} />}
              {p.original_context && thoughtContextPath(p.original_context) && <Link className="underline" to={thoughtContextPath(p.original_context)!} onClick={onOpenContext}>Open original material: {p.original_context.label}</Link>}
              {status === 'parked' && <Button size="sm" disabled={pending !== null || retry !== null} onClick={() => act(p, 'promote')}>Show on Home</Button>}
              {confirm === p.id ? <div className="w-full">
                <p>Remove this thought from your reminders? After removal, Undo is available here until another change or you leave this view.</p>
                <div className="flex flex-wrap gap-2 mt-1">
                  <Button size="sm" disabled={pending !== null || retry !== null} onClick={() => act(p, 'drop')}>Remove thought</Button>
                  <Button size="sm" variant="ghost" autoFocus disabled={pending !== null || retry !== null} onClick={() => { setConfirm(null); requestAnimationFrame(() => removeButtons.current[p.id]?.focus()) }}>Keep thought</Button>
                </div>
              </div> : <Button size="sm" variant="ghost" asChild><button ref={node => { removeButtons.current[p.id] = node }} disabled={pending !== null || retry !== null} onClick={() => setConfirm(p.id)}>Remove…</button></Button>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
