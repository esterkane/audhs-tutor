import { useEffect, useRef, useState } from 'react'
import { NotebookWorkspace } from '../features/programs/NotebookWorkspace'
import { GuidedSection } from '../features/programs/GuidedSection'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { parseNotebook, parseProgram, type NotebookCell, type Program } from '../features/programs/manifest'

function NotebookReader({
  notebook,
  explanations,
  paused,
}: {
  paused: boolean
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
    <Card className="grid gap-3">
      <h2 className="text-lg font-semibold">Understand a notebook</h2>
      <p>
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
          className="block"
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
      {!paused && cells.length > 0 && (
        <NotebookWorkspace
          key={JSON.stringify(cells)}
          cells={cells}
          identity={notebook ?? 'uploaded'}
          explanations={isSavedNotebook ? explanations : undefined}
        />
      )}
      <details id="complete-notebook-guide" open>
        <summary>Run the complete notebook with datasets and scientific libraries</summary>
        <p>
          For full notebooks, use the local Jupyter lab. It opens data/notebooks; upload your notebook and
          datasets there using its Upload button. Keep the notebook and dataset files in the same folder. Read
          the first markdown cells, then run cells in order with Shift+Enter. Check outputs and errors before
          continuing.
        </p>
        <pre className="whitespace-pre-wrap">python3 scripts/notebook_lab.py --install</pre>
        <p>
          Run once from the project folder in a terminal; on later starts omit --install. The authenticated
          local lab does not execute cells automatically. Review course-specific dependencies before
          installing them.
        </p>
        <a href="http://127.0.0.1:8890/lab" target="_blank" rel="noreferrer">
          Open local notebook lab (after starting it)
        </a>
      </details>
    </Card>
  )
}

export function Programs() {
  const [program, setProgram] = useState<Program | null>(null)
  const [error, setError] = useState('')
  const [courseId, setCourseId] = useState('')
  const [sectionId, setSectionId] = useState('')
  const [paused, setPaused] = useState(false)
  const [notebookView, setNotebookView] = useState(false)
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
  const course = program?.courses.find((c) => c.id === courseId) ?? program?.courses[0]
  const section = course?.sections.find((s) => s.id === sectionId) ?? course?.sections[0]
  const sectionIndex = course?.sections.findIndex((s) => s.id === section?.id) ?? -1
  function chooseStep(id: string) {
    setSectionId(id)
    setPaused(false)
    setNotebookView(false)
  }
  return (
    <div className="grid gap-5">
      <header className="border-b border-line pb-4">
        <p className="text-sm text-muted">Project study · one idea at a time</p>
        <h1 className="text-2xl font-semibold">{program?.title ?? 'Degree projects'}</h1>
        <p className="mt-2">Understand an idea, try it, then explore where it holds—and where it breaks.</p>
      </header>
      {error && <p role="alert">{error} Local course content is separate from the application.</p>}
      {!program && !error && <p role="status">Loading local programme…</p>}
      {program && course && (
        <div className="grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)] items-start">
          <aside
            className="lg:sticky lg:top-4 border border-line bg-card rounded-xl p-4 grid gap-4"
            aria-label="Lesson outline"
          >
            <label className="text-sm font-medium">
              Course
              <select
                className="block w-full min-w-0 border border-line rounded p-2 bg-card mt-2"
                value={course.id}
                onChange={(e) => {
                  setCourseId(e.target.value)
                  setSectionId('')
                  setPaused(false)
                  setNotebookView(false)
                }}
              >
                {program.courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            </label>
            <details open className="hidden lg:block">
              <summary className="font-semibold cursor-pointer">Project steps</summary>
              <nav aria-label="Project steps" className="grid gap-1 mt-3">
                {course.sections.map((s, i) => (
                  <button
                    key={s.id}
                    aria-current={s.id === section?.id ? 'step' : undefined}
                    className={`text-left rounded-lg p-3 text-sm border ${s.id === section?.id ? 'border-accent bg-bg font-semibold' : 'border-transparent'}`}
                    onClick={() => chooseStep(s.id)}
                  >
                    <span className="text-muted mr-2">{i + 1}.</span>
                    {s.title}
                  </button>
                ))}
              </nav>
            </details>
            <label className="lg:hidden text-sm">
              Project step
              <select
                className="block w-full border border-line rounded p-2 bg-card mt-2"
                value={section?.id ?? ''}
                onChange={(e) => chooseStep(e.target.value)}
              >
                {course.sections.map((s, i) => (
                  <option key={s.id} value={s.id}>
                    {i + 1}. {s.title}
                  </option>
                ))}
              </select>
            </label>
            <p className="text-xs text-muted">
              Your place in the guide, not a completion score. You can revisit any step.
            </p>
            <details>
              <summary className="cursor-pointer">Project goal and sources</summary>
              <p className="mt-2 text-sm">{course.project}</p>
              <p className="mt-2 text-xs text-muted">Material coverage: {course.status}</p>
            </details>
          </aside>
          <div className="min-w-0 grid gap-4">
            <div className="flex flex-wrap gap-2 items-center justify-between">
              <p className="text-sm text-muted">
                {section
                  ? `Step ${sectionIndex + 1} of ${course.sections.length} · ${section.title}`
                  : 'No guide yet'}
              </p>
              <Button variant="outline" onClick={() => setPaused(!paused)}>
                {paused ? 'Resume this step' : 'Pause study'}
              </Button>
            </div>
            <div className="flex gap-2" aria-label="Study view">
              <Button
                variant={notebookView ? 'outline' : 'primary'}
                aria-pressed={!notebookView}
                onClick={() => setNotebookView(false)}
              >
                Guided lesson
              </Button>
              <Button
                variant={notebookView ? 'primary' : 'outline'}
                aria-pressed={notebookView}
                onClick={() => setNotebookView(true)}
              >
                Notebook workspace
              </Button>
            </div>
            {paused && <p role="status">Paused. Your notes stay available; resume or choose another step.</p>}
            <div hidden={paused || notebookView}>
              {section ? (
                <GuidedSection
                  key={course.id + ':' + section.id}
                  section={section}
                  course={course.id}
                  paused={paused || notebookView}
                />
              ) : (
                <p>No verified project guide is available for this course yet.</p>
              )}
            </div>
            <div hidden={!notebookView || paused}>
              <NotebookReader
                key={course.id}
                paused={paused || !notebookView}
                notebook={course.notebook}
                explanations={course.explanations}
              />
            </div>
            {!notebookView && section && (
              <nav
                aria-label="Adjacent project steps"
                className="flex justify-between gap-3 border-t border-line pt-4"
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
          </div>
        </div>
      )}
      {!program && !error && <p>You can pause at any time.</p>}
    </div>
  )
}
