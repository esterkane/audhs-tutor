import { useSearchParams } from 'react-router-dom'
import { SavedContextAnswers } from '../features/programs/SavedContextAnswers'
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { LocalNotebookLab } from '../features/programs/LocalNotebookLab'
import { NotebookWorkspace } from '../features/programs/NotebookWorkspace'
import { GuidedSection } from '../features/programs/GuidedSection'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { parseNotebook, parseProgram, type NotebookCell, type Program } from '../features/programs/manifest'

function NotebookReader({
  notebook,
  courseId,
  explanations,
  paused,
}: {
  paused: boolean
  courseId: string
  notebook?: string
  explanations?: Record<string, string>
}) {
  const [cells, setCells] = useState<NotebookCell[]>([])
  const [isSavedNotebook, setIsSavedNotebook] = useState(false)
  const [error, setError] = useState('')
  const generation = useRef(0)
  useEffect(
    () => () => {
      generation.current++
    },
    [],
  )
  return (
    <Card className="min-w-0 grid gap-3">
      <div id="complete-notebook-guide">{!paused && <LocalNotebookLab courseId={courseId} />}</div>
      <details className="border-t border-line pt-3">
        <summary className="cursor-pointer font-medium">Read or edit a notebook in this page</summary>
        <p className="my-3">
          Open a notebook to read instructions, edit its starter code and try a local experiment. Nothing runs
          until you press Run.
        </p>
        {notebook?.startsWith('/local-learning/') && (
          <Button
            onClick={async () => {
              const request = ++generation.current
              try {
                const res = await fetch(notebook)
                if (!res.ok) throw new Error('The saved notebook is unavailable.')
                const next = parseNotebook(await res.json())
                if (request !== generation.current) return
                setIsSavedNotebook(true)
                setCells(next)
                setError('')
              } catch (err) {
                if (request === generation.current) setError((err as Error).message)
              }
            }}
          >
            Open saved project notebook
          </Button>
        )}

        <label>
          Local notebook
          <input
            className="block w-full min-w-0 max-w-full"
            type="file"
            accept=".ipynb"
            onChange={async (e) => {
              const file = e.target.files?.[0]
              if (!file) return
              const request = ++generation.current
              try {
                if (file.size > 10 * 1024 * 1024) throw new Error('Choose a notebook smaller than 10 MiB.')
                const next = parseNotebook(JSON.parse(await file.text()))
                if (request !== generation.current) return
                setIsSavedNotebook(false)
                setCells(next)
                setError('')
              } catch (err) {
                if (request === generation.current) setError((err as Error).message)
              }
            }}
          />
        </label>
        {error && <p role="alert">{error} The previous notebook remains open.</p>}
        {cells.length > 0 && (
          <NotebookWorkspace
            paused={paused}
            courseId={isSavedNotebook ? courseId : undefined}
            key={JSON.stringify(cells)}
            cells={cells}
            identity={notebook ?? 'uploaded'}
            explanations={isSavedNotebook ? explanations : undefined}
          />
        )}
      </details>
    </Card>
  )
}

const locationKey = 'project-study-location:v1'
type StudyLocation = { version: 1; courseId: string; sectionId: string; notebook: boolean }
function restoreLocation(): { location: StudyLocation | null; error: string } {
  try {
    const raw = localStorage.getItem(locationKey)
    if (!raw) return { location: null, error: '' }
    const value = JSON.parse(raw) as StudyLocation
    if (
      value.version !== 1 ||
      typeof value.courseId !== 'string' ||
      typeof value.sectionId !== 'string' ||
      typeof value.notebook !== 'boolean'
    )
      throw new Error('Invalid location')
    return { location: value, error: '' }
  } catch {
    return {
      location: null,
      error:
        'Your saved place could not be read. Choose a course and step; existing notes have not been removed.',
    }
  }
}

function rememberLocation(next: StudyLocation): string {
  try {
    localStorage.setItem(locationKey, JSON.stringify(next))
    return 'Your place is saved in this browser.'
  } catch {
    return 'Your place could not be saved in this browser. Keep the page address to return here. Existing notes have not been removed.'
  }
}

export function Programs() {
  const [program, setProgram] = useState<Program | null>(null)
  const [error, setError] = useState('')
  const [restored] = useState(restoreLocation)
  const [params, setParams] = useSearchParams()
  const linked = params.has('course') || params.has('step') || params.has('view')
  const location = useMemo(() => linked ? {
    version: 1 as const,
    courseId: params.get('course') ?? '',
    sectionId: params.get('step') ?? '',
    notebook: params.get('view') === 'notebook',
  } : restored.location, [linked, params, restored.location])
  const [placeStatus, setPlaceStatus] = useState(restored.error)
  const [paused, setPaused] = useState(false)
  const notebookView = location?.notebook ?? false
  const [chooserOpen, setChooserOpen] = useState(false)
  const heading = useRef<HTMLHeadingElement>(null)
  const focusRequested = useRef(false)
  useLayoutEffect(() => {
    if (focusRequested.current) {
      focusRequested.current = false
      heading.current?.focus()
    }
  }, [location, notebookView])
  useEffect(() => {
    const ctl = new AbortController()
    void fetch('/local-learning/program.json', { signal: ctl.signal })
      .then(async (res) => {
        if (!res.ok) throw new Error('No local programme is configured yet.')
        const value = parseProgram(await res.json())
        if (!ctl.signal.aborted) setProgram(value)
      })
      .catch((err) => {
        if (!ctl.signal.aborted) setError(err.message)
      })
    return () => ctl.abort()
  }, [])
  const course = program?.courses.find((c) => c.id === location?.courseId) ?? program?.courses[0]
  const section = course?.sections.find((s) => s.id === location?.sectionId) ?? course?.sections[0]
  const sectionIndex = course?.sections.findIndex((s) => s.id === section?.id) ?? -1
  const staleLocation =
    !!program &&
    !!location &&
    (course?.id !== location.courseId || (section?.id ?? '') !== location.sectionId)
  useEffect(() => {
    if (linked || !course || staleLocation) return
    setParams(
      (previous) => {
        const query = new URLSearchParams(previous)
        query.set('course', course.id)
        query.set('step', section?.id ?? '')
        if (notebookView) query.set('view', 'notebook')
        return query
      },
      { replace: true },
    )
  }, [linked, course, section, staleLocation, notebookView, setParams])
  function savePlace(courseId: string, sectionId: string, notebook = false) {
    setParams((previous) => {
      const query = new URLSearchParams(previous)
      query.set('course', courseId)
      query.set('step', sectionId)
      if (notebook) query.set('view', 'notebook')
      else query.delete('view')
      return query
    })
    setPlaceStatus(rememberLocation({ version: 1, courseId, sectionId, notebook }))
  }
  const resolvedCourseId = course?.id
  const resolvedSectionId = section?.id ?? ''
  useEffect(() => {
    if (!resolvedCourseId || staleLocation) return
    const next: StudyLocation = {
      version: 1,
      courseId: resolvedCourseId,
      sectionId: resolvedSectionId,
      notebook: notebookView,
    }
    // Report the result of synchronizing browser history with external saved-place storage.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPlaceStatus(rememberLocation(next))
  }, [resolvedCourseId, resolvedSectionId, notebookView, staleLocation])

  function focusStep() {
    focusRequested.current = true
  }
  function chooseStep(id: string) {
    if (!course) return
    savePlace(course.id, id)
    setPaused(false)
    setChooserOpen(false)
    focusStep()
  }
  function showNotebook(value: boolean) {
    if (!course) return
    savePlace(course.id, section?.id ?? '', value)
    setPaused(false)
    focusStep()
  }
  return (
    <div className="grid grid-cols-1 gap-4 max-w-4xl mx-auto min-w-0">
      <header>
        <h1 className="text-2xl font-semibold">Project study</h1>
        <p className="text-sm text-muted mt-1">Learn the ideas, try the task, then discuss your reasoning.</p>
      </header>
      {error && <p role="alert">{error} Local course content is separate from the application.</p>}
      {!program && !error && <p role="status">Loading local programme…</p>}
      {program && !course && <p>No courses are configured yet. Add local learning material to begin.</p>}
      {program && course && (
        <>
          <section aria-label="Current project" className="grid gap-3 border-b border-line pb-4 min-w-0">
            <p className="text-sm text-muted break-words">{course.title}</p>
            <div className="flex flex-wrap gap-3 items-center justify-between">
              <div className="min-w-0">
                <p className="text-sm text-muted">
                  {section ? `Project step ${sectionIndex + 1} of ${course.sections.length}` : 'No guide yet'}
                </p>
                <h2 ref={heading} tabIndex={-1} className="text-xl font-semibold break-words">
                  {notebookView ? 'Full course notebook' : (section?.title ?? 'Choose how to study')}
                </h2>
              </div>
              <Button variant="outline" onClick={() => setPaused(!paused)}>
                {paused ? 'Resume this step' : 'Pause study'}
              </Button>
            </div>
            <details open={chooserOpen} onToggle={(e) => setChooserOpen(e.currentTarget.open)}>
              <summary className="cursor-pointer text-sm">Change course or project step</summary>
              <div className="grid sm:grid-cols-2 gap-3 mt-3">
                <label className="text-sm font-medium min-w-0">
                  Course
                  <select
                    className="block w-full min-w-0 border border-line rounded p-2 bg-card mt-2"
                    value={course.id}
                    onChange={(e) => {
                      const next = program.courses.find((c) => c.id === e.target.value)!
                      savePlace(next.id, next.sections[0]?.id ?? '')
                      setPaused(false)
                    }}
                  >
                    {program.courses.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.title}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-medium min-w-0">
                  Project step
                  <select
                    className="block w-full min-w-0 border border-line rounded p-2 bg-card mt-2"
                    value={section?.id ?? ''}
                    disabled={!section}
                    onChange={(e) => chooseStep(e.target.value)}
                  >
                    {!section && <option value="">No guide available</option>}
                    {course.sections.map((s, i) => (
                      <option key={s.id} value={s.id}>
                        {i + 1}. {s.title}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <p className="text-xs text-muted mt-2">
                Changing your place does not mark a step complete. Notes remain with their original step.
              </p>
            </details>
            {staleLocation && (
              <p role="status">
                {linked
                  ? 'The linked course or step could not be found.'
                  : 'Your saved course or step is no longer available.'}{' '}
                Showing the first available step; choose where to continue. Existing notes have not been
                removed.
              </p>
            )}
            {placeStatus && !staleLocation && (
              <p role="status" className="text-xs text-muted">
                {placeStatus}
              </p>
            )}
          </section>
          {paused && (
            <p role="status">
              Project study is paused. Your notes stay available. This does not end a separate learning
              session.
            </p>
          )}
          {notebookView && !paused && (
            <div className="grid gap-2">
              <Button onClick={() => showNotebook(false)}>Back to guided lesson</Button>
              <p className="text-sm">
                This is the whole course notebook and its datasets. For a smaller practice task, return to the
                guided lesson and choose Try.
              </p>
            </div>
          )}
          <div role="region" aria-label="Guided lesson" hidden={paused || notebookView}>
            {section ? (
              <GuidedSection
                key={course.id + ':' + section.id}
                section={section}
                course={course.id}
                paused={paused || notebookView}
                onOpenNotebook={() => showNotebook(true)}
              />
            ) : (
              <p>
                No verified project guide is available for this course yet. You can still open its full
                notebook tools below.
              </p>
            )}
          </div>
          <div hidden={!notebookView || paused}>
            <NotebookReader
              key={course.id}
              courseId={course.id}
              paused={paused || !notebookView}
              notebook={course.notebook}
              explanations={course.explanations}
            />
          </div>
          {!notebookView && !paused && (
            <>
              <details>
                <summary className="cursor-pointer">Full course notebook and files</summary>
                <p className="text-sm my-2">
                  Use the complete project notebook with its datasets and scientific libraries in local
                  Jupyter, or read a notebook in this page. Nothing runs automatically.
                </p>
                <Button onClick={() => showNotebook(true)}>Open full course notebook tools</Button>
              </details>
              <details>
                <summary className="cursor-pointer">Project goal and sources</summary>
                <p className="mt-2 text-sm">{course.project}</p>
                <p className="mt-2 text-xs text-muted">
                  {program.title} · Material coverage: {course.status}
                </p>
              </details>
              <SavedContextAnswers key={`course:${course.id}`} courseId={course.id} />
              {section && (
                <nav
                  aria-label="Adjacent project steps"
                  className="flex flex-wrap justify-between gap-3 border-t border-line pt-4"
                >
                  <Button
                    disabled={sectionIndex <= 0}
                    onClick={() => chooseStep(course.sections[sectionIndex - 1].id)}
                  >
                    Previous step
                  </Button>
                  {sectionIndex < course.sections.length - 1 ? (
                    <Button onClick={() => chooseStep(course.sections[sectionIndex + 1].id)}>
                      Next project step
                    </Button>
                  ) : (
                    <p className="text-sm">End of guide. Review your project against its checklist.</p>
                  )}
                </nav>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
