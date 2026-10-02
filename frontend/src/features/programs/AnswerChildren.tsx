import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch, type Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'

/** History includes reported/hidden replies: this is lineage, not a recommendation list. */
export function AnswerChildren({ answerId }: { answerId: string }) {
  const [open, setOpen] = useState(false)
  const params = new URLSearchParams({ parent_answer_id: answerId })
  const query = useQuery({
    queryKey: ['answers', 'children', answerId],
    queryFn: ({ signal }) => apiFetch<Schemas['AnswerPage']>(`/api/answers?${params}&limit=5`, { signal }),
    enabled: open,
  })
  return (
    <details onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>Later replies to this answer</summary>
      <p className="text-sm text-muted my-2">
        Direct follow-ups, newest first. A later reply is not automatically a correction or a verified
        replacement. Reported and hidden replies remain in this history; open one to review its feedback.
      </p>
      {open && (query.isPending ? <p role="status">Loading follow-up history…</p>
        : query.isError ? <p role="alert">Could not load follow-up history. <Button onClick={() => void query.refetch()}>Retry follow-up history</Button></p>
        : <>
          {query.data.items.length === 0 ? <p>No saved direct follow-ups yet.</p> : (
            <ul className="grid gap-2">
              {query.data.items.map((answer) => <li key={answer.id}>
                <Link className="underline" to={`/answers/${encodeURIComponent(answer.id)}`}>
                  {(answer.learner_question || answer.request_text || 'Open saved follow-up').slice(0, 180)}
                </Link>
                <p className="text-sm">Saved {new Date(answer.created_at).toLocaleString()}</p>
              </li>)}
            </ul>
          )}
          {query.data.next_cursor && <Link className="underline" to={`/answers?${params}`}>Browse all direct follow-ups</Link>}
        </>)}
    </details>
  )
}
