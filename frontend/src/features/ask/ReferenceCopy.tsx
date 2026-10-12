import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import { apiFetch, type Schemas } from '../../lib/api'

export function ReferenceCopy({ referenceId }: { referenceId: string }) {
  const [copy, setCopy] = useState<Schemas['ReferenceSnapshot'] | null>(null)
  const [busy, setBusy] = useState<'load' | 'import' | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const active = useRef<AbortController | null>(null)
  const status = useQuery({
    queryKey: ['reference-copy', referenceId],
    retry: false,
    queryFn: ({ signal }) =>
      apiFetch<Schemas['ReferenceStatus']>(`/api/references/${referenceId}`, { signal }),
  })
  const snapshot = copy ?? status.data?.snapshot
  useEffect(() => () => active.current?.abort(), [])
  async function run(action: 'load' | 'import', refresh = false) {
    if (active.current || (action === 'import' && !snapshot)) return
    const controller = new AbortController()
    active.current = controller
    setBusy(action)
    setError('')
    setMessage('')
    try {
      if (action === 'load') {
        const next = await apiFetch<Schemas['ReferenceSnapshot']>(`/api/references/${referenceId}/load`, {
          method: 'POST',
          body: JSON.stringify({ refresh }),
          signal: controller.signal,
        })
        if (controller.signal.aborted) return
        setCopy(next)
        setMessage('Local reading copy saved. Review the preview before adding it to your library.')
      } else {
        const result = await apiFetch<Schemas['ReferenceImported']>(`/api/references/${referenceId}/import`, {
          method: 'POST',
          body: JSON.stringify({ snapshot_id: snapshot!.snapshot_id }),
          signal: controller.signal,
        })
        if (controller.signal.aborted) return
        setMessage(`${result.note} ${result.chunks} passages stored.`)
      }
    } catch (e) {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Reference action failed.')
    } finally {
      if (active.current === controller) {
        active.current = null
        setBusy(null)
      }
    }
  }
  return (
    <section aria-label="Local reading copy" className="border-t border-line pt-3 space-y-2">
      <p className="text-sm text-muted">
        Save downloads this page only, without your question or course content. Add to local library is a
        separate action. Third-party text stays local.
      </p>
      {status.isPending && <p role="status">Checking local copy…</p>}
      {status.isError && (
        <p role="alert">
          Could not read local-copy status.{' '}
          <Button onClick={() => void status.refetch()}>Retry local status</Button>
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button
          disabled={!!busy || status.isPending}
          onClick={() => void run('load', !!snapshot || status.isError)}
        >
          {busy === 'load'
            ? 'Downloading page…'
            : snapshot
              ? 'Refresh reading copy'
              : 'Save a local reading copy'}
        </Button>
        {snapshot && (
          <Button disabled={!!busy} onClick={() => void run('import')}>
            {busy === 'import' ? 'Adding to local library…' : 'Add to local library'}
          </Button>
        )}
        {busy && (
          <Button
            onClick={() => {
              active.current?.abort()
              active.current = null
              setBusy(null)
              setMessage(
                'Stopped waiting. The operation may still finish locally; read local-copy status or retry import to recover.',
              )
            }}
          >
            Stop waiting
          </Button>
        )}
      </div>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
      {snapshot && (
        <details>
          <summary>Read saved preview · {new Date(snapshot.fetched_at).toLocaleDateString()}</summary>
          <div className="space-y-2 mt-2 text-sm">
            <p>{snapshot.note}</p>
            <p className="break-words">Source: {snapshot.url}</p>
            <p>
              {snapshot.extracted_characters.toLocaleString()} extracted characters. Preview shows up to 6,000
              characters.
            </p>
            <p className="whitespace-pre-wrap break-words">{snapshot.text_preview}</p>
            <p className="break-all text-muted">Content fingerprint: {snapshot.snapshot_id}</p>
          </div>
        </details>
      )}
    </section>
  )
}
