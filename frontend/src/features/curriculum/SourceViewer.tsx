import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { Textarea } from '../../components/ui/textarea'
import { useChunk, useReport } from './api'

function mmss(t: number | null | undefined): string | null {
  if (t == null) return null
  const m = Math.floor(t / 60)
  const s = Math.floor(t % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

/**
 * The passage behind a citation (P4 `source-viewer`): the cited text with its neighbours, the
 * course › section › lecture path, a timestamp for media, and an open link only when the server
 * allows it (http(s), or the app's guarded file endpoint for a file under the ingest roots; media
 * links carry `#t=` so the browser seeks). A missing chunk shows the citation as a fallback excerpt. "Report" keeps a note next to the evidence; it never rewrites anything.
 */
export function SourceViewer({
  chunkId,
  citation,
  turnId,
  onClose,
}: {
  chunkId: string
  citation: string
  turnId?: string | null
  onClose: () => void
}) {
  const chunk = useChunk(chunkId)
  const report = useReport()
  const [note, setNote] = useState('')
  const [reporting, setReporting] = useState(false)
  const c = chunk.data
  return (
    <Card role="region" aria-label={`Source ${citation}`} className="border-accent">
      <div className="flex justify-between gap-2 items-start">
        <p className="font-medium text-sm">{c ? c.citation : citation}</p>
        <Button size="sm" variant="ghost" onClick={onClose}>
          Close
        </Button>
      </div>
      {chunk.isLoading && <p className="text-sm text-muted">Loading passage…</p>}
      {chunk.isError && (
        <p className="text-sm text-muted" role="status">
          This passage is no longer in the corpus (it may have been re-ingested or removed). The citation
          above is what the tutor saw.
        </p>
      )}
      {c && (
        <>
          <p className="text-xs text-muted mt-1">
            {c.document_title} · {c.source_type} · trust {c.trust_tier}
            {mmss(c.t_start) ? ` · at ${mmss(c.t_start)}${mmss(c.t_end) ? `–${mmss(c.t_end)}` : ''}` : ''}
          </p>
          {c.prev_text && (
            <p className="text-sm text-muted mt-2 whitespace-pre-wrap">…{c.prev_text.slice(-300)}</p>
          )}
          <blockquote className="text-sm mt-2 border-l-2 border-accent pl-3 whitespace-pre-wrap">
            {c.text}
          </blockquote>
          {c.next_text && (
            <p className="text-sm text-muted mt-2 whitespace-pre-wrap">{c.next_text.slice(0, 300)}…</p>
          )}
          <p className="text-xs text-muted mt-2 break-all">
            {c.open_url ? (
              <a href={c.open_url} target="_blank" rel="noreferrer">
                Open the original ({c.uri.split('!/')[0].split('/').slice(-1)[0]})
              </a>
            ) : (
              <>Path: {c.uri} (not under the configured ingest roots — open it yourself)</>
            )}
          </p>
        </>
      )}
      <div className="mt-3">
        {!reporting ? (
          <Button size="sm" variant="ghost" onClick={() => setReporting(true)}>
            Report this source as wrong
          </Button>
        ) : report.isSuccess ? (
          <p className="text-sm" role="status">
            Reported. It stays on record next to this turn; nothing was rewritten.
          </p>
        ) : (
          <div className="grid gap-2">
            <label htmlFor="report-note" className="text-sm">
              What is wrong? (one line is enough)
            </label>
            <Textarea
              id="report-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className="min-h-16"
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="primary"
                disabled={report.isPending}
                onClick={() =>
                  report.mutate({ kind: 'wrong_source', chunk_id: chunkId, turn_id: turnId ?? null, note })
                }
              >
                Send report
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setReporting(false)}>
                Cancel
              </Button>
            </div>
            {report.isError && (
              <p role="alert" className="text-sm text-warn">
                {(report.error as Error).message}
              </p>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
