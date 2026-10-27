import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../lib/api'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { useDraftRecovery } from '../features/curriculum/useDraftRecovery'

type Project = Schemas['LearningProjectOut']
const encode = (project: Project) =>
  JSON.stringify({
    notes: project.notes,
    evidence: project.evidence,
    reflection: project.reflection,
    status: project.status,
  })
const input = 'block w-full rounded border border-line bg-card p-2'

export function Projects() {
  const query = useQuery({
    queryKey: ['learning-projects'],
    retry: false,
    queryFn: () => apiFetch<Project[]>('/api/projects'),
  })
  const [params, setParams] = useSearchParams()
  const selected = query.data?.find((project) => project.id === params.get('project'))
  return (
    <div className="grid gap-4">
      <h1 className="text-page-title font-semibold">Knowledge projects</h1>
      <p>
        Build, test and explain a small working system. Create your own learning material as you go. Existing
        reference material is for checking accuracy; submitting a project does not automatically change
        mastery.
      </p>
      <p>
        <Link to="/curriculum">Create knowledge material from notes or uploads</Link> ·{' '}
        <Link to="/map">Open the new knowledge map</Link>
      </p>
      {query.isPending && <p role="status">Loading your projects…</p>}
      {query.isError && (
        <div>
          <p role="alert">Projects could not load. Your saved work is kept.</p>
          <Button onClick={() => void query.refetch()}>Retry projects</Button>
        </div>
      )}
      {selected ? (
        <>
          <Button variant="secondary" onClick={() => setParams({})}>
            Back to all projects
          </Button>
          <ProjectEditor key={selected.id} project={selected} />
        </>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {query.data?.map((project) => (
            <Card key={project.id}>
              <CardTitle as="h2">{project.title}</CardTitle>
              <p className="text-sm text-muted">
                {project.topic} · {project.status}
              </p>
              <p>{project.objective}</p>
              <Button onClick={() => setParams({ project: project.id })}>
                Open project: {project.topic}
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

function ProjectEditor({ project }: { project: Project }) {
  const recovery = useDraftRecovery('learning-project:' + project.id, project.version, encode(project))
  const cache = useQueryClient()
  const [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(''),
    [error, setError] = useState('')
  const active = useRef<AbortController | null>(null)
  useEffect(() => () => active.current?.abort(), [])
  let form = { notes: '', evidence: '', reflection: '', status: 'planned' }
  let valid = false
  try {
    const parsed = JSON.parse(recovery.text)
    if (['notes', 'evidence', 'reflection', 'status'].every((key) => typeof parsed[key] === 'string')) {
      form = parsed
      valid = true
    }
  } catch {
    /* Keep damaged recovery text visible below. */
  }
  const conflict = recovery.baseVersion !== project.version
  async function save(status: 'working' | 'submitted') {
    if (active.current || !valid || conflict) return
    const controller = new AbortController()
    active.current = controller
    setBusy(true)
    setError('')
    setNotice('')
    const sent = { ...form, status }
    recovery.edit(JSON.stringify(sent))
    try {
      const result = await apiFetch<Project>('/api/projects/' + encodeURIComponent(project.id), {
        method: 'PUT',
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]),
        body: JSON.stringify({ ...sent, expected_version: recovery.baseVersion }),
      })
      if (controller.signal.aborted) return
      recovery.reset(JSON.stringify(sent), result.version)
      cache.setQueryData<Project[]>(['learning-projects'], (old) =>
        old?.map((row) => (row.id === result.id && row.version <= result.version ? result : row)),
      )
      setNotice(
        status === 'submitted'
          ? 'Project evidence submitted for review. This does not certify mastery.'
          : 'Project writing saved. You can resume it later.',
      )
    } catch (reason) {
      if (!controller.signal.aborted)
        setError(
          reason instanceof Error
            ? reason.message
            : 'Could not confirm saving. Your writing is kept; check the saved version before retrying.',
        )
    } finally {
      if (active.current === controller) active.current = null
      if (!controller.signal.aborted) setBusy(false)
    }
  }
  function edit(key: 'notes' | 'evidence' | 'reflection', value: string) {
    recovery.edit(JSON.stringify({ ...form, [key]: value }))
    setNotice('')
  }
  return (
    <Card>
      <CardTitle as="h2">{project.title}</CardTitle>
      <p>{project.objective}</p>
      {(['build', 'test'] as const).map((key) => (
        <section key={key}>
          <h3 className="font-semibold">{key === 'build' ? 'Build' : 'Test your understanding'}</h3>
          <ol className="list-decimal pl-5">
            {(Array.isArray(project.brief[key]) ? (project.brief[key] as string[]) : []).map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </section>
      ))}
      <p>
        <strong>Reflect:</strong> {String(project.brief.reflect ?? '')}
      </p>

      {typeof project.brief.workspace === 'string' && project.brief.workspace === '/projects/supabase' && (
        <p>
          <Link to={project.brief.workspace}>Open the imported Supabase/PostgreSQL lab</Link>
        </p>
      )}

      {typeof project.brief.source === 'string' && (
        <p>
          <a href={project.brief.source} target="_blank" rel="noreferrer">
            Open project source and setup instructions
          </a>
        </p>
      )}
      <p className="text-sm text-muted">
        Use only disposable local resources for these experiments. Record commands and results you actually
        ran.
      </p>
      {!valid && (
        <div>
          <p role="alert">
            Saved browser recovery could not be interpreted. Copy it before replacing anything.
          </p>
          <textarea className={input} aria-label="Project recovery text" readOnly value={recovery.text} />
        </div>
      )}
      {(['notes', 'evidence', 'reflection'] as const).map((key) => (
        <label key={key} className="block">
          {
            {
              notes: 'My project notes',
              evidence: 'Test evidence and observed results',
              reflection: 'What I can explain and what remains uncertain',
            }[key]
          }
          <textarea
            className={input}
            rows={5}
            maxLength={key === 'evidence' ? 24000 : 16000}
            disabled={busy || !valid}
            value={form[key]}
            onChange={(event) => edit(key, event.target.value)}
          />
        </label>
      ))}
      {conflict && (
        <div>
          <p role="alert">The saved project changed. Your writing is retained; compare it before saving.</p>
          <Button
            variant="secondary"
            onClick={() => {
              const kept = recovery.text
              recovery.reset(encode(project), project.version)
              recovery.edit(kept)
            }}
          >
            Keep my writing against the latest version
          </Button>
        </div>
      )}
      <div className="flex gap-2 flex-wrap">
        <Button disabled={busy || !valid || conflict} onClick={() => void save('working')}>
          Save project notes
        </Button>
        <Button
          variant="secondary"
          disabled={busy || !valid || conflict || !form.evidence.trim() || !form.reflection.trim()}
          onClick={() => void save('submitted')}
        >
          Submit evidence for review
        </Button>
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() => void cache.invalidateQueries({ queryKey: ['learning-projects'] })}
        >
          Check saved project
        </Button>
      </div>
      <p className="text-sm text-muted">
        {recovery.dirty ? 'Unsaved writing is kept in this browser tab.' : 'Your current writing is saved.'}
      </p>
      {recovery.error && <p role="alert">{recovery.error}</p>}
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
    </Card>
  )
}
