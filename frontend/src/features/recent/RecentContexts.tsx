import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { OriginalLesson } from '../parking/OriginalLesson'
import { thoughtContextPath, type ThoughtContext } from '../parking/context'
import { contextIdentity, useRecentContexts } from './history'

const labels: Record<ThoughtContext['kind'], string> = { source: 'Source passage', workspace: 'Coding workspace', area: 'Learning area', answer: 'Saved explanation', project: 'Project step', audio_lesson: 'Audio lesson', lesson: 'Lesson checkpoint' }
export function RecentContexts() {
  const { items, storageError, clear } = useRecentContexts()
  if (!items.length && !storageError) return null
  return <details className="rounded-md border border-line p-3">
    <summary className="cursor-pointer font-medium">Recently opened material</summary>
    <p className="my-2 text-sm text-muted">Navigation history in this tab, not learning progress. Opening material does not restore temporary output or playback.</p>
    {storageError && <p role="status" className="text-sm">History could not be saved, restored or cleared in this tab. Current entries remain available here; older history may reappear after reloading.</p>}
    <ul className="grid gap-3 my-2">
      {items.map(context => <li key={contextIdentity(context)} className="min-w-0 break-words">
        <span className="block text-sm text-muted">{labels[context.kind]}</span>
        {context.kind === 'lesson' ? <OriginalLesson context={context} /> : <Link className="underline" to={thoughtContextPath(context)!}>{context.label}</Link>}
      </li>)}
    </ul>
    <Button size="sm" variant="secondary" onClick={clear}>Clear material history</Button>
  </details>
}
