import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import type { Check } from '../code/runner'
import { NotebookWorkspace } from './NotebookWorkspace'
import { parseNotebook, type NotebookCell, type Section } from './manifest'

type Props = {
  courseId?: string
  sectionId?: string
  practice: NonNullable<Section['practice']>
  identity: string
  title: string
  paused: boolean
  onBack: (summary?: string) => void
}
export function TaskNotebook(props: Props) {
  return (
    <TaskNotebookLoad
      key={JSON.stringify([
        props.identity,
        props.courseId,
        props.sectionId,
        props.practice.notebook,
        props.practice.dataset,
      ])}
      {...props}
    />
  )
}
function TaskNotebookLoad({ courseId, sectionId, practice, identity, title, paused, onBack }: Props) {
  const [loaded, setLoaded] = useState<{ cells: NotebookCell[]; checks: Check[]; prelude: string } | null>(
    null,
  )
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    heading.current?.focus()
    const ctl = new AbortController()
    async function load() {
      const response = await fetch(practice.notebook, { signal: ctl.signal })
      if (!response.ok) throw new Error('The task starter is unavailable.')
      const notebook = await response.json()
      if (ctl.signal.aborted) throw new DOMException('Cancelled', 'AbortError')
      const next = parseNotebook(notebook)
      const validations = notebook.metadata?.practice_checks
      if (
        !Array.isArray(validations) ||
        !validations.length ||
        validations.length > 20 ||
        validations.some(
          (c: Check) =>
            !c || ['name', 'criterion', 'code'].some((k) => typeof c[k as keyof Check] !== 'string'),
        )
      )
        throw new Error('Task starter is missing valid calculation checks.')
      let prelude = ''
      if (practice.dataset) {
        const data = await fetch(practice.dataset, { signal: ctl.signal })
        if (!data.ok) throw new Error('The task dataset is unavailable.')
        const csv = await data.text()
        if (csv.length > 25 * 1024 * 1024) throw new Error('Dataset exceeds the browser practice limit.')
        // A Python string literal, never executable dataset content. The export is self-contained.
        prelude = `import json\nDATA_CSV = json.loads(${JSON.stringify(JSON.stringify(csv))})\n`
      }
      return { cells: next, checks: validations as Check[], prelude }
    }
    let timer: ReturnType<typeof setTimeout>
    const deadline = new Promise<never>((_, reject) => {
      timer = setTimeout(() => {
        reject(
          new Error(
            'Loading timed out. Existing project notes and saved notebook edits are not changed. Retry loading or return to the task.',
          ),
        )
      }, 15000)
    })
    void Promise.race([load(), deadline])
      .then((next) => {
        if (!ctl.signal.aborted) setLoaded(next)
      })
      .catch((err: unknown) => {
        if (!ctl.signal.aborted) {
          setError(err instanceof Error ? err.message : String(err))
          ctl.abort()
        }
      })
      .finally(() => clearTimeout(timer))
    return () => {
      clearTimeout(timer)
      ctl.abort()
    }
  }, [practice.notebook, practice.dataset, attempt])
  return (
    <section className="grid gap-4" aria-label="Task notebook">
      <h2 ref={heading} tabIndex={-1}>
        Notebook: {title}
      </h2>
      <Button onClick={() => onBack()}>Back to task without results</Button>
      <p>
        Your project notes stay in the task. Notebook edits are saved in this browser; you can return before
        finishing.
      </p>
      {error ? (
        <div role="alert">
          {error}{' '}
          <Button
            onClick={() => {
              setError('')
              setAttempt(attempt + 1)
            }}
          >
            Retry loading starter
          </Button>
        </div>
      ) : (
        !loaded && <p role="status">Loading starter and local dataset…</p>
      )}
      {loaded && (
        <NotebookWorkspace
          paused={paused}
          courseId={courseId}
          sectionId={sectionId}
          cells={loaded.cells}
          checks={loaded.checks}
          prelude={loaded.prelude}
          identity={`task:${identity}`}
          onFinish={onBack}
        />
      )}
    </section>
  )
}
