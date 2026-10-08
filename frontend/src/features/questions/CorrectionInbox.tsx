import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { type Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'

export function CorrectionInbox() {
  const [open, setOpen] = useState(false)
  const [offset, setOffset] = useState(0)
  const heading = useRef<HTMLHeadingElement>(null)
  const moved = useRef(false)
  const query = useQuery({
    queryKey: ['question-corrections', offset], enabled: open, retry: false,
    queryFn: ({ signal }) => boundedRead<Schemas['CorrectionInbox']>(
      `/api/questions/corrections?offset=${offset}&limit=20`, signal, 'Question reports',
    ),
  })
  useEffect(() => {
    if (open && !query.isFetching && query.data && moved.current) {
      moved.current = false
      heading.current?.focus()
    }
  }, [open, query.isFetching, query.data])
  function page(next: number) {
    moved.current = true
    setOffset(next)
  }
  return <section id="question-reports" className="border border-line rounded p-4">
    <h2 ref={heading} tabIndex={-1} className="text-lg font-semibold">Reported questions</h2>
    <p className="text-sm text-muted">Review questions you marked as needing improvement. This list does not change questions or grades. You can prepare a correction draft; replacement is not available yet.</p>
    <Button className="mt-2" aria-expanded={open} onClick={() => setOpen(!open)}>
      {open ? 'Hide question reports' : 'Show question reports'}
    </Button>
    {open && <div className="mt-3 grid gap-3">
      <p className="text-sm">Latest non-withdrawn negative rating per question version. A newer positive rating removes that version from this list.</p>
      <Button disabled={query.isFetching} onClick={() => void query.refetch()}>Refresh question reports</Button>
      {query.isFetching && <p role="status">Loading question reports…</p>}
      {query.error && <p role="alert">Could not load reports. {query.data ? 'Previously loaded reports remain below. ' : ''}Use Refresh question reports to try again.</p>}
      {query.data && <>
        <p role="status">{query.data.total === 0 ? 'No question reports need review.' : `${query.data.total} reported question version(s).`}</p>
        {query.data.items.map(item => <article key={item.id} className="border border-line rounded p-3 min-w-0 break-words">
          <h3 className="font-medium">{item.target === 'draft' ? 'Draft question' : 'Practice question'}</h3>
          <p className="text-sm text-muted">Reported {new Date(item.created_at).toLocaleString()}</p>
          <p className="mt-2 font-medium">Wording when reported</p><p>{item.reported_question}</p>
          <p className="mt-2">Reported reasons: {item.labels.map(label => label.replaceAll('_', ' ')).join(', ')}</p>
          {item.note && <p className="whitespace-pre-wrap">Your note: {item.note}</p>}
          <p className="mt-2 text-sm">{item.content_status === 'unchanged'
            ? 'Content unchanged since this report.'
            : item.content_status === 'changed' ? 'Content changed since this report; the reported version is preserved above.'
              : 'Current content unavailable; your report is preserved.'}</p>
          {item.content_status === 'changed' && item.current_question && <>
            <p className="mt-2 font-medium">Current wording</p><p>{item.current_question}</p>
          </>}
          {item.assessment_id && item.content_status === 'unchanged' && <Link to={`/corrections?assessment=${encodeURIComponent(item.assessment_id)}&report=${encodeURIComponent(item.id)}`}>Prepare a correction draft</Link>}
          {item.content_status === 'changed' && !item.current_question && <p className="text-sm">The original question cannot be safely matched in the current draft.</p>}
        </article>)}
        {query.data.total > 0 && query.data.items.length === 0 && <p>This page is now empty. Return to the previous page or refresh.</p>}
        <div className="flex flex-wrap gap-2">
          {offset > 0 && <Button disabled={query.isFetching} onClick={() => page(Math.max(0, offset - 20))}>Previous reports</Button>}
          {offset + query.data.items.length < query.data.total && <Button disabled={query.isFetching} onClick={() => page(offset + 20)}>More reports</Button>}
        </div>
      </>}
      <Link to="/corrections">Open saved correction drafts</Link>
      <Link to="/preferences#excluded-questions">Manage question exclusions separately</Link>
    </div>}
  </section>
}
