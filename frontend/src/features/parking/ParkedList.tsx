import { Link } from 'react-router-dom'
import { thoughtContextPath } from './context'
import { useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { useParked, useParkingActions } from './api'

export function ParkedList({ onOpenContext }: { onOpenContext?: () => void } = {}) { return <ThoughtList status="parked" onOpenContext={onOpenContext} /> }
export function PromotedReminders() { return <ThoughtList status="promoted" /> }

/** These are optional reminders, never evidence of learning or completed work. */
function ThoughtList({ status, onOpenContext }: { status: 'parked' | 'promoted'; onOpenContext?: () => void }) {
  const query = useParked(status)
  const { promote, drop } = useParkingActions()
  const lock = useRef(false)
  const removeButtons = useRef<Record<string, HTMLButtonElement | null>>({})
  const feedback = useRef<HTMLParagraphElement>(null)
  const [pending, setPending] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<string | null>(null)
  const [result, setResult] = useState<{ error: boolean; text: string } | null>(null)
  async function act(id: string, action: 'promote' | 'drop', text: string) {
    if (lock.current) return
    lock.current = true
    setPending(id)
    setResult(null)
    const origin = document.activeElement
    try {
      if (action === 'promote') await promote.mutateAsync({ id, to: 'next_session' })
      else await drop.mutateAsync(id)
      setConfirm(null)
      setResult({ error: false, text: action === 'promote' ? `Shown on Home: ${text}` : `Removed from reminders: ${text}` })
    } catch {
      setResult({ error: true, text: `Could not confirm the change to “${text}”. Check the refreshed list before trying again; the server may have applied it.` })
    } finally {
      lock.current = false
      setPending(null)
      // Keep focus if the learner has moved elsewhere while waiting.
      if (document.activeElement === origin || (origin instanceof HTMLButtonElement && (!origin.isConnected || origin.disabled) && document.activeElement === document.body)) {
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
      {query.isPending ? <p role="status">Loading saved thoughts…</p> : query.isError ? (
        <p role="alert">Could not load saved thoughts. <Button onClick={() => void query.refetch()}>Retry saved thoughts</Button></p>
      ) : !items.length ? <p className="text-sm text-muted">{status === 'parked' ? 'No saved thoughts.' : 'No thoughts to revisit.'}</p> : (
        <ul className="grid gap-3 text-sm" aria-label={status === 'parked' ? 'Saved thoughts' : 'Thoughts to revisit'}>
          {items.map(p => (
            <li key={p.id} className="flex flex-wrap items-center gap-2">
              <span className="grow">{p.text}</span>
              {p.original_context && thoughtContextPath(p.original_context) && <Link className="underline" to={thoughtContextPath(p.original_context)!} onClick={onOpenContext}>Open original material: {p.original_context.label}</Link>}
              {status === 'parked' && <Button size="sm" disabled={pending !== null} onClick={() => void act(p.id, 'promote', p.text)}>Show on Home</Button>}
              {confirm === p.id ? <div className="w-full">
                <p>Remove this thought from your reminders? There is currently no undo.</p>
                <div className="flex flex-wrap gap-2 mt-1">
                  <Button size="sm" disabled={pending !== null} onClick={() => void act(p.id, 'drop', p.text)}>Remove thought</Button>
                  <Button size="sm" variant="ghost" autoFocus disabled={pending !== null} onClick={() => { setConfirm(null); requestAnimationFrame(() => removeButtons.current[p.id]?.focus()) }}>Keep thought</Button>
                </div>
              </div> : <Button size="sm" variant="ghost" asChild><button ref={node => { removeButtons.current[p.id] = node }} disabled={pending !== null} onClick={() => setConfirm(p.id)}>Remove…</button></Button>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
