import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import type { Check } from '../code/runner'
import { NotebookWorkspace } from './NotebookWorkspace'
import { parseNotebook, type NotebookCell, type Section } from './manifest'

export function TaskNotebook({
  courseId,
  sectionId,
  practice,
  identity,
  title,
  paused,
  onBack,
}: {
  courseId?: string
  sectionId?: string
  practice: NonNullable<Section['practice']>
  identity: string
  title: string
  paused: boolean
  onBack: (summary?: string) => void
}) {
  const [cells, setCells] = useState<NotebookCell[] | null>(null)
  const [checks, setChecks] = useState<Check[]>([])
  const [prelude, setPrelude] = useState('')
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
      if (!ctl.signal.aborted) setChecks(validations)
      if (practice.dataset) {
        const data = await fetch(practice.dataset, { signal: ctl.signal })
        if (!data.ok) throw new Error('The task dataset is unavailable.')
        const csv = await data.text()
        if (csv.length > 25 * 1024 * 1024) throw new Error('Dataset exceeds the browser practice limit.')
        // A Python string literal, never executable dataset content. The export is self-contained.
        if (!ctl.signal.aborted)
          setPrelude(`import json\nDATA_CSV = json.loads(${JSON.stringify(JSON.stringify(csv))})\n`)
      }
      if (!ctl.signal.aborted) setCells(next)
    }
    void load().catch((err: unknown) => {
      if (!ctl.signal.aborted) setError(err instanceof Error ? err.message : String(err))
    })
    return () => ctl.abort()
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
        !cells && <p role="status">Loading starter and local dataset…</p>
      )}
      {cells && !paused && (
        <NotebookWorkspace
          courseId={courseId}
          sectionId={sectionId}
          cells={cells}
          checks={checks}
          prelude={prelude}
          identity={`task:${identity}`}
          onFinish={onBack}
        />
      )}
    </section>
  )
}
