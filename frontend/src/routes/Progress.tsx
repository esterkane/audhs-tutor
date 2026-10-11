import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Disclosure } from '../components/ui/disclosure'
import { useSkills } from '../features/skills/api'
import { boundedRead } from '../lib/boundedRead'
import type { Schemas } from '../lib/api'

const labels: Record<string, string> = {
  explanation: 'Understanding', application: 'Practice', transfer: 'Transfer', recall: 'Recall',
}
function dateLabel(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleString()
}

export function Progress() {
  const skills = useSkills()
  const [params, setParams] = useSearchParams()
  const selected = params.get('skill') ?? skills.data?.skills[0]?.id ?? ''
  const concept = skills.data?.skills.find(skill => skill.id === selected)
  return <div className="grid gap-5">
    <div>
      <h1 className="text-page-title font-semibold">Progress</h1>
      <p className="mt-2 text-muted">See what has been checked and when. Reading, bookmarks and opening activities are not evidence of understanding.</p>
    </div>
    {skills.isError && <Card><p role="alert">Could not refresh your concepts.</p><Button onClick={() => void skills.refetch()} disabled={skills.isFetching}>Retry concepts</Button></Card>}
    {skills.isPending && <p role="status">Loading concepts…</p>}
    {skills.data && <>
      <div className="grid gap-2"><label htmlFor="progress-concept">Concept</label>
        <select id="progress-concept" className="min-h-11 min-w-0 max-w-full rounded border border-line bg-card p-2" value={selected}
          onChange={event => setParams({ skill: event.target.value })}>
          {!skills.data.skills.length && <option value="">No concepts available</option>}
          {selected && !concept && <option value={selected}>Unavailable concept</option>}
          {skills.data.skills.map(skill => <option key={skill.id} value={skill.id}>{skill.title}</option>)}
        </select>
      </div>
      {concept ? <ConceptEvidence key={concept.id} skillId={concept.id} title={concept.title} />
        : <p role="status">{selected ? 'This concept is unavailable. Choose another concept.' : 'No concepts are available yet. Explore your learning areas to get started.'}</p>}
    </>}
    <div className="flex flex-wrap gap-4">
      <Link className="underline" to="/map">View skill map</Link>
      <Link className="underline" to="/explore">Explore learning areas</Link>
    </div>
  </div>
}

function ConceptEvidence({ skillId, title }: { skillId: string; title: string }) {
  const [offset, setOffset] = useState(0)
  const evidence = useQuery({
    queryKey: ['progress-evidence', skillId, offset],
    queryFn: ({ signal }) => boundedRead<Schemas['ProgressEvidencePage']>(
      `/api/skills/${encodeURIComponent(skillId)}/evidence?offset=${offset}&limit=20`, signal, 'Progress evidence'),
    retry: false,
    placeholderData: keepPreviousData,
  })
  const [lastPage, setLastPage] = useState<Schemas['ProgressEvidencePage']>()
  if (evidence.data && !evidence.isPlaceholderData && evidence.data !== lastPage) setLastPage(evidence.data)
  const data = evidence.data ?? lastPage
  function changePage(next: number) {
    if (next === offset) void evidence.refetch()
    else setOffset(next)
  }
  if (!data) return <Card>
    {evidence.isError ? <><p role="alert">Could not load evidence for {title}.</p><Button onClick={() => void evidence.refetch()} disabled={evidence.isFetching}>Retry evidence</Button></>
      : <p role="status">Loading evidence for {title}…</p>}
  </Card>
  return <>
    {evidence.isError && <p role="alert">Could not load the requested evidence. Showing the last loaded records. <Button onClick={() => void evidence.refetch()}>Retry evidence</Button></p>}
    <Card>
      <CardTitle>{title}</CardTitle>
      <dl className="grid gap-4">
        {['explanation', 'application', 'transfer', 'recall'].map(dimension => {
          const summary = data.dimensions.find(row => row.dimension === dimension)
          return <div key={dimension} className="border-b border-line pb-3">
            <dt className="font-semibold">{dimension === 'transfer' ? 'Independent application' : labels[dimension]}</dt>
            <dd className="mt-1">
              {dimension === 'transfer' ? 'Not verified as independent work.' : summary ? 'Evidence recorded.' : 'Not yet checked.'}
              {summary && <span className="block text-sm text-muted">{summary.count} {dimension === 'transfer' ? 'transfer ' : ''}{summary.count === 1 ? 'record' : 'records'} · Latest: <time dateTime={summary.last_recorded_at}>{dateLabel(summary.last_recorded_at)}</time></span>}
            </dd>
          </div>
        })}
      </dl>
      <p className="mt-3 text-sm text-muted">A recorded check is not a mastery level. Hint counts do not capture all help or solution exposure, so independent work is not confirmed.</p>
    </Card>
    <Disclosure label="Why does the tutor think this?">
      {evidence.isFetching && <p role="status">Updating records…</p>}
      <p className="mb-3">These are the recorded checks behind this summary. They may include model judgements. Open a saved assessment to inspect its recorded question, answer and feedback when available.</p>
      {!data.total ? <p>No assessment evidence recorded yet.</p> : <>
        <p className="text-sm text-muted">Records {data.items.length ? data.offset + 1 : 0}–{data.offset + data.items.length} of {data.total}, newest first.</p>
        <ol className="grid gap-3 mt-3">
          {data.items.map(item => <li key={item.id} className="border-b border-line pb-3">
            <p className="font-medium">{labels[item.dimension] ?? item.dimension} · <time dateTime={item.recorded_at}>{dateLabel(item.recorded_at)}</time></p>
            <p>Recorded result: {item.score === 1 ? 'full credit' : item.score === 0 ? 'no credit' : 'partial credit'}.</p>
            <p className="text-sm text-muted">Checked by: {item.grader_level === 'local' ? 'local model' : item.grader_level === 'hosted' ? 'hosted model' : item.grader_level}.</p>
            <p className="text-sm text-muted">{item.reported_hint_count === null ? 'Hint history unavailable.' : `Reported hints: ${item.reported_hint_count}.`} {item.attempt_id ? 'Linked assessment attempt.' : 'Original attempt unavailable.'}</p>
            {item.answer_id ? <Link className="inline-flex min-h-11 items-center underline" to={`/answers/${encodeURIComponent(item.answer_id)}`}>Open saved assessment</Link> : <p className="text-sm text-muted">Saved question and feedback unavailable.</p>}
          </li>)}
        </ol>
        <div className="flex flex-wrap gap-2 mt-3">
          <Button disabled={evidence.isFetching || data.offset === 0} onClick={() => changePage(Math.max(0, data.offset - 20))}>Newer records</Button>
          <Button disabled={evidence.isFetching || data.offset + data.items.length >= data.total} onClick={() => changePage(data.offset + 20)}>Older records</Button>
        </div>
      </>}
    </Disclosure>
    <Card>
      <CardTitle>Next useful evidence</CardTitle>
      <p className="mb-3">Work through this concept and check an answer in a learning session. The lesson will guide the next activity; this page does not change your learning plan.</p>
      <Button asChild><Link to={`/?lesson=${encodeURIComponent(skillId)}`}>Choose this lesson</Link></Button>
    </Card>
  </>
}
