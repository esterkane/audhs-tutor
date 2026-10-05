import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { boundedRead } from '../../lib/boundedRead'
import { ApiError } from '../../lib/api'
import { parseProgram } from './manifest'

export function ProjectSearch({ phrase }: { phrase: string }) {
  const guide = useQuery({
    queryKey: ['material-search', 'project-guide'],
    queryFn: async ({ signal }) => {
      try {
        return parseProgram(await boundedRead<unknown>('/local-learning/program.json', signal, 'Project guide'))
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
    retry: false,
  })
  const term = phrase.toLocaleLowerCase()
  const matches = (guide.data?.courses ?? []).flatMap(course => course.sections
    .filter(section => [course.title, section.title, section.explanation].some(text => text.toLocaleLowerCase().includes(term)))
    .map(section => ({ course, section })))
  return <section aria-labelledby="search-projects" className="rounded-md border border-line p-3 min-w-0 break-words">
    <h2 id="search-projects" className="text-panel-heading font-semibold">Project guides</h2>
    <p className="text-sm text-muted">Guide titles and section explanations matching your phrase. Notebook cells and your notes are not searched.</p>
    {guide.isPending ? <p role="status">Searching project guides…</p> : guide.isError ? <div role="alert">Project guides could not be loaded. Other search results remain available. <Button disabled={guide.isFetching} onClick={() => void guide.refetch()}>Retry project search</Button></div> : !guide.data ? <p>No local project guide is configured.</p> : <>
      <p role="status">{matches.length ? `${Math.min(8, matches.length)} of ${matches.length} matching sections shown.` : 'No project guide sections matched.'}</p>
      <ul className="grid gap-3 my-2">{matches.slice(0, 8).map(({ course, section }) => <li key={JSON.stringify([course.id, section.id])}>
        <Link className="underline" to={`/programs?${new URLSearchParams({ course: course.id, step: section.id })}`}>{course.title} · {section.title}</Link>
        <p className="text-sm whitespace-pre-wrap">{section.explanation.slice(0, 240)}{section.explanation.length > 240 ? '…' : ''}</p>
      </li>)}</ul>
      {matches.length > 8 && <Link className="underline" to="/programs">Browse all project guides</Link>}
    </>}
  </section>
}
