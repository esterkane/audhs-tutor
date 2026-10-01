import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import {
  parseNotebook,
  parseProgram,
  type NotebookCell,
  type Program,
  type Section,
} from '../features/programs/manifest'

type Work = { answer: string; note: string; label: string }
function SectionStudy({ section, course }: { section: Section; course: string }) {
  const key = `project-study:v1:${course}:${section.id}`
  const [work, setWork] = useState<Work>(() => {
    try {
      const value = JSON.parse(localStorage.getItem(key) ?? 'null')
      if (value && ['answer', 'note', 'label'].every((k) => typeof value[k] === 'string')) return value
    } catch {
      /* editable in-memory fallback */
    }
    return { answer: '', note: '', label: 'Learning' }
  })
  const [saved, setSaved] = useState('')
  const [hint, setHint] = useState(false)
  const [check, setCheck] = useState(false)
  function update(next: Work) {
    setWork(next)
    try {
      localStorage.setItem(key, JSON.stringify(next))
      setSaved('Saved on this browser.')
    } catch {
      setSaved('Could not save. Keep this page open and copy your notes before leaving.')
    }
  }
  return (
    <Card className="grid gap-4">
      <h2 className="text-lg font-semibold">{section.title}</h2>
      <p className="whitespace-pre-wrap">{section.explanation}</p>
      <p className="text-sm text-muted">Tutor-authored learning guide. Source: {section.source}</p>
      <h3 className="font-semibold">Build this part of the project</h3>
      <p>{section.task}</p>
      <h3 className="font-semibold">Think it through</h3>
      <p>{section.question}</p>
      <label>
        Your explanation
        <textarea
          className="block border rounded p-2 w-full bg-card"
          value={work.answer}
          onChange={(e) => update({ ...work, answer: e.target.value })}
        />
      </label>
      <div className="flex gap-2 flex-wrap">
        <Button variant="outline" onClick={() => setHint(!hint)}>
          {hint ? 'Hide hint' : 'One hint'}
        </Button>
        <Button variant="outline" onClick={() => setCheck(!check)}>
          {check ? 'Hide checklist' : 'Show self-check checklist'}
        </Button>
      </div>
      {hint && <p>{section.hint}</p>}
      {check && <p>Self-check, not automated grading: {section.criteria}</p>}
      <label>
        Project notes
        <textarea
          className="block border rounded p-2 w-full bg-card"
          value={work.note}
          onChange={(e) => update({ ...work, note: e.target.value })}
        />
      </label>
      <label>
        My bookmark
        <select
          className="block border rounded p-2 bg-card"
          value={work.label}
          onChange={(e) => update({ ...work, label: e.target.value })}
        >
          <option>Learning</option>
          <option>Clear</option>
          <option>Ask later again</option>
        </select>
      </label>
      <p className="text-sm">Bookmarks do not mark the official project complete or award mastery.</p>
      <p role="status">{saved}</p>
    </Card>
  )
}

function NotebookReader({
  notebook,
  explanations,
}: {
  notebook?: string
  explanations?: Record<string, string>
}) {
  const [cells, setCells] = useState<NotebookCell[]>([])
  const [index, setIndex] = useState(0)
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
      <p>Open a local .ipynb file. Read one cell at a time; nothing is executed or uploaded.</p>
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
              setIndex(0)
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
              setIndex(0)
              setError('')
            } catch (err) {
              if (request === generation.current) setError((err as Error).message)
            }
          }}
        />
      </label>
      {error && <p role="alert">{error} The previous notebook remains open.</p>}
      {cells.length > 0 && (
        <>
          <p>
            Cell {index + 1} of {cells.length} · {cells[index].cell_type}
          </p>
          <pre className="whitespace-pre-wrap break-words overflow-auto border rounded p-3">
            {cells[index].source}
          </pre>
          {isSavedNotebook && explanations?.[String(index + 1)] && (
            <p className="border-l-4 pl-3">
              <strong>Why this step: </strong>
              {explanations[String(index + 1)]}
            </p>
          )}
          <p>
            Before moving on: What goes in? What changes? What comes out? Why does the next step need this
            result?
          </p>
          <div className="flex gap-2">
            <Button disabled={index === 0} onClick={() => setIndex(index - 1)}>
              Previous cell
            </Button>
            <Button disabled={index === cells.length - 1} onClick={() => setIndex(index + 1)}>
              Next cell
            </Button>
          </div>
          <Link to="/playground">Open the coding playground for a small experiment</Link>
        </>
      )}
    </Card>
  )
}

export function Programs() {
  const [program, setProgram] = useState<Program | null>(null)
  const [error, setError] = useState('')
  const [courseId, setCourseId] = useState('')
  const [sectionId, setSectionId] = useState('')
  const [paused, setPaused] = useState(false)
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
  return (
    <div className="grid gap-4">
      <h1 className="text-xl font-semibold">{program?.title ?? 'Degree projects'}</h1>
      <p>Understand the ideas, work through the code, and build one useful part of your project at a time.</p>
      {error && <p role="alert">{error} Local course content is separate from the application.</p>}
      {!program && !error && <p role="status">Loading local programme…</p>}
      {program && course && (
        <>
          <label>
            Course
            <select
              className="block w-full border rounded p-2 bg-card"
              value={course.id}
              onChange={(e) => {
                setCourseId(e.target.value)
                setSectionId('')
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
          <Card>
            <h2 className="font-semibold">What you are building</h2>
            <p>{course.project}</p>
            <p className="text-sm mt-2">Material coverage: {course.status}</p>
          </Card>
          {section ? (
            <>
              <label>
                Project step
                <select
                  className="block w-full border rounded p-2 bg-card"
                  value={section.id}
                  onChange={(e) => {
                    setSectionId(e.target.value)
                    setPaused(false)
                  }}
                >
                  {course.sections.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title}
                    </option>
                  ))}
                </select>
              </label>
              <Button variant="outline" onClick={() => setPaused(!paused)}>
                {paused ? 'Resume this step' : 'Pause study'}
              </Button>
              <div hidden={paused}>
                <SectionStudy key={course.id + ':' + section.id} section={section} course={course.id} />
              </div>
              {paused && (
                <p role="status">
                  Paused. Your notes stay available; you can resume or choose another course.
                </p>
              )}
            </>
          ) : (
            <p>No verified project guide is available for this course yet.</p>
          )}
        </>
      )}
      <NotebookReader
        key={course?.id ?? 'empty'}
        notebook={course?.notebook}
        explanations={course?.explanations}
      />
    </div>
  )
}
