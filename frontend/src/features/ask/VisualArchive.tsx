import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import type { Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'
import { RequestRecoveryControls } from '../playground/RequestRecoveryControls'
import { useVisualArchiveRecovery, type PendingTutorRequest, type VisualArchiveBody } from '../playground/useRequestRecovery'

type Document = Schemas['VisualDocumentSummary']
export function VisualArchive({ answerId, learnerId, document, refresh, showArchived, lock }: {
  answerId: string; learnerId: string; document?: Document;
  refresh: () => Promise<void>; showArchived: (archived: boolean) => void; lock: (locked: boolean) => void
}) {
  // Answer scope keeps a lost-response retry reachable even if the document leaves the active list.
  const recovery = useVisualArchiveRecovery(`visual-archive:${learnerId}:${answerId}`)
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [confirmed, setConfirmed] = useState<{ archived: boolean; label: string } | null>(null)
  const locked = busy || !!recovery.pending || recovery.needsDiscard
  useEffect(() => { lock(locked) }, [lock, locked])
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; active.current?.abort() } }, [])

  async function save(previous?: PendingTutorRequest<VisualArchiveBody>) {
    if (active.current || (!previous && (!document || locked))) return
    const controller = new AbortController(); active.current = controller; setBusy(true); setError(''); setConfirmed(null)
    try {
      let intent = previous
      if (!intent) {
        const current = await boundedRead<Document>(`/api/authored-visuals/${encodeURIComponent(document!.id)}`, controller.signal, 'Current diagram state')
        if (!mounted.current || controller.signal.aborted) return
        // Do not invert a newer state the learner has not seen.
        if (current.archived !== document!.archived) throw new Error('Archive state changed. Refresh the diagram library before choosing an action.')
        intent = recovery.prepare({ action: 'archive', document_id: current.id, expected_revision: current.revision, archived: !current.archived },
          { display: `${current.archived ? 'Restore' : 'Archive'}: ${current.title}`, submitted: '', snapshot: '', mode: 'explicit' })
      }
      await boundedRead<Schemas['VisualReceipt']>('/api/authored-visuals/commands', controller.signal, 'Archive change', {
        method: 'POST', headers: { 'Idempotency-Key': intent.key }, body: JSON.stringify(intent.body),
      })
      if (!mounted.current || controller.signal.aborted) return
      recovery.accept(intent.key); setConfirmed({ archived: intent.body.archived, label: intent.view.display })
      // A replay receipt confirms an operation, not the document's current state.
      await refresh()
    } catch (reason) {
      if (mounted.current) setError(reason instanceof Error ? reason.message : 'Archive change could not be confirmed.')
    } finally { if (mounted.current) { active.current = null; setBusy(false) } }
  }

  return <div className="space-y-2">
    {document && <><p className="text-sm text-muted">Archiving hides this diagram from active diagrams. Its versions and reviews are retained; you can restore it.</p>
      <Button disabled={locked} onClick={() => void save()}>{document.archived ? 'Restore diagram' : 'Archive diagram'}</Button></>}
    <RequestRecoveryControls saveOnly savedAction="change archive state again" recovery={recovery} busy={busy} originalContext="diagram, revision and archive action" retry={() => { if (recovery.pending) void save(recovery.pending) }} />
    {busy && <><p role="status">Saving archive change… Stopping this wait does not undo a saved action.</p><Button onClick={() => active.current?.abort()}>Stop waiting for archive change</Button></>}
    {error && <p role="alert">{error}</p>}
    {confirmed !== null && <div role="status"><p>{confirmed.archived ? 'Archive' : 'Restore'} request confirmed: {confirmed.label}. The library shows the latest available state; a previous receipt may predate later changes.</p><Button onClick={() => showArchived(confirmed.archived)}>{confirmed.archived ? 'View archived diagrams' : 'View active diagrams'}</Button></div>}
  </div>
}
