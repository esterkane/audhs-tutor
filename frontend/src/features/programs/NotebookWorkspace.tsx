import { useCallback, useEffect, useRef, useState } from 'react'
import { Markdown } from '../../components/Markdown'
import { Button } from '../../components/ui/button'
import { CodeEditor } from '../code/CodeEditor'
import { createPyodideRunner, type Runner, type RunResult, type Check } from '../code/runner'
import type { NotebookCell } from './manifest'
import { StudyTutor } from './StudyTutor'
import { ReadAloud } from '../voice/ReadAloud'

type Props = {
  courseId?: string
  sectionId?: string
  cells: NotebookCell[]
  identity: string
  explanations?: Record<string, string>
  checks?: Check[]
  prelude?: string
  onFinish?: (summary: string) => void
  paused?: boolean
  runnerFactory?: () => Runner
}
type Draft = { sources: string[]; predictions: Record<string, string>; selected: number }
export function NotebookWorkspace(props: Props) {
  return <Workspace key={JSON.stringify([props.identity, props.cells])} {...props} />
}
function Workspace({
  courseId,
  sectionId,
  cells,
  identity,
  explanations,
  prelude = '',
  checks = [],
  onFinish,
  runnerFactory = createPyodideRunner,
  paused = false,
}: Props) {
  const baseline = JSON.stringify(cells)
  let contentHash = 2166136261
  for (let i = 0; i < baseline.length; i += 1)
    contentHash = Math.imul(contentHash ^ baseline.charCodeAt(i), 16777619)
  const storageKey = `notebook-workspace:v1:${identity}:${(contentHash >>> 0).toString(16)}`
  const [restored] = useState(() => {
    const fresh: Draft = {
      sources: cells.map((c) => c.source),
      predictions: {},
      selected: onFinish
        ? Math.max(
            0,
            cells.findIndex((c) => c.cell_type === 'markdown'),
          )
        : 0,
    }
    try {
      const raw = localStorage.getItem(storageKey)
      if (!raw) return { draft: fresh, status: 'Edits stay in this browser.' }
      const saved = JSON.parse(raw)
      if (saved.baseline !== baseline)
        return { draft: fresh, status: 'Source changed. Starting from the new notebook.' }
      const d = saved.draft
      if (d && !d.predictions && typeof d.prediction === 'string')
        d.predictions = { [String(d.selected)]: d.prediction }
      if (
        !Array.isArray(d.sources) ||
        d.sources.length !== cells.length ||
        !d.sources.every((s: unknown) => typeof s === 'string') ||
        !d.predictions ||
        typeof d.predictions !== 'object' ||
        Array.isArray(d.predictions) ||
        !Object.values(d.predictions).every((v) => typeof v === 'string') ||
        !Number.isInteger(d.selected) ||
        d.selected < 0 ||
        d.selected >= cells.length
      )
        throw new Error('Invalid draft')
      return { draft: d as Draft, status: 'Saved edits restored.' }
    } catch {
      return { draft: fresh, status: 'Saved edits could not be restored. Export your work before leaving.' }
    }
  })
  const [draft, setDraft] = useState(restored.draft)
  const [saveStatus, setSaveStatus] = useState(restored.status)
  const [plain, setPlain] = useState(false)
  const [tutorTarget, setTutorTarget] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [checkedRun, setCheckedRun] = useState<RunResult | null>(null)
  const [result, setResult] = useState<RunResult | null>(null)
  const [status, setStatus] = useState(
    'Read the instructions, select a code cell, then predict what it will produce.',
  )
  const operation = useRef(0)
  const deadline = useRef<ReturnType<typeof setTimeout> | null>(null)
  const runner = useRef<Runner | null>(null)
  useEffect(
    () => () => {
      operation.current += 1
      if (deadline.current) clearTimeout(deadline.current)
      runner.current?.dispose()
    },
    [],
  )
  function update(next: Draft) {
    setDraft(next)
    try {
      localStorage.setItem(storageKey, JSON.stringify({ baseline, draft: next }))
      setSaveStatus('Edits saved in this browser.')
    } catch {
      setSaveStatus('Could not save in this browser. Your edits are still here; export before leaving.')
    }
  }
  const stop = useCallback(() => {
    if (deadline.current) clearTimeout(deadline.current)
    operation.current += 1
    runner.current?.dispose()
    runner.current = null
    setBusy(false)
    setCheckedRun(null)
    setStatus('Run stopped. Your edits are preserved.')
  }, [])
  useEffect(() => {
    // Mirror termination of the external worker in its run/status state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (paused && busy) stop()
  }, [paused, busy, stop])
  async function run(all = false) {
    if (busy) return
    const token = ++operation.current
    const selected = all ? cells.length - 1 : draft.selected
    setBusy(true)
    setResult(null)
    setCheckedRun(null)
    setStatus(`Running code through cell ${selected + 1} in a fresh Python sandbox…`)
    let current: Runner | null = null
    const timer = setTimeout(() => {
      if (operation.current !== token) return
      stop()
      setStatus(
        'Runtime loading or execution took too long and was stopped. Your edits are preserved; retry when the local runtime is ready.',
      )
    }, 45000)
    deadline.current = timer
    try {
      current = runnerFactory()
      runner.current = current
      const code =
        prelude +
        cells
          .slice(0, selected + 1)
          .flatMap((c, i) =>
            c.cell_type === 'code' ? [`# Notebook cell ${i + 1}\n${draft.sources[i]}\n`] : [],
          )
          .join('\n')
      const output = await current.run(code, all ? checks : [], {
        timeoutMs: 30000,
        maxOutputChars: 20000,
        packages: [],
      })
      if (operation.current !== token) return
      setResult(output)
      setCheckedRun(
        all &&
          !output.error &&
          !output.timedOut &&
          checks.length > 0 &&
          output.results.length === checks.length &&
          checks.every((c, i) => output.results[i]?.name === c.name && output.results[i]?.passed)
          ? output
          : null,
      )
      setStatus(
        output.error
          ? 'Python reported an error. Compare it with the code and prerequisites.'
          : `Code through cell ${selected + 1} finished. Compare the output with your prediction; this is not a correctness grade.`,
      )
    } catch (error) {
      if (operation.current === token)
        setStatus(`Could not run: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      clearTimeout(timer)
      current?.dispose()
      if (operation.current === token) {
        runner.current = null
        setBusy(false)
      }
    }
  }
  function download() {
    const notebook = {
      nbformat: 4,
      nbformat_minor: 5,
      metadata: { kernelspec: { display_name: 'Python 3', language: 'python', name: 'python3' } },
      cells: [
        ...(prelude
          ? [
              {
                cell_type: 'code',
                id: 'local-data',
                metadata: {},
                source: prelude,
                execution_count: null,
                outputs: [],
              },
            ]
          : []),
        ...cells.map((c, i) => ({
          cell_type: c.cell_type,
          id: `cell-${i + 1}`,
          metadata: {},
          source: draft.sources[i],
          ...(c.cell_type === 'code' ? { execution_count: null, outputs: [] } : {}),
        })),
        ...checks.map((c, i) => ({
          cell_type: 'code',
          id: `check-${i}`,
          metadata: {},
          source: `# ${c.criterion}\n${c.code}`,
          execution_count: null,
          outputs: [],
        })),
      ],
    }
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(notebook, null, 2)], { type: 'application/x-ipynb+json' }),
    )
    const a = document.createElement('a')
    a.href = url
    a.download = 'edited-notebook.ipynb'
    a.click()
    const revoke = URL.revokeObjectURL.bind(URL)
    setTimeout(() => revoke(url), 1000)
  }
  const answerIndex = tutorTarget ?? draft.selected
  const cell = cells[draft.selected]
  if (!cell) return <p>This notebook has no readable cells.</p>
  const context = cells
    .slice(0, draft.selected)
    .map((c, i) => ({ c, i }))
    .filter(({ c }) => c.cell_type === 'markdown')
    .at(-1)
  if (paused) return null
  return (
    <section aria-label="Notebook workspace" className="space-y-4 border border-line rounded-lg p-4">
      <h3 className="text-xl font-semibold">Read → predict → run → explain</h3>
      <p>
        The original notebook is your starter. Edit its code below. Each run starts fresh and reruns every
        code cell up to your selection, in order.
      </p>
      <details>
        <summary>What can run here?</summary>
        <p>
          Local browser Python supports the standard library. This is not a complete Jupyter kernel: course
          packages, datasets on your disk, notebook magics, widgets and plot displays are not supported here.
          Use print(...) to inspect values. Export edited source for a local Jupyter environment; original
          outputs, attachments and metadata are not included in this edited copy. The original file is
          unchanged.
        </p>
      </details>
      <label className="block">
        Notebook cell
        <select
          className="block w-full"
          value={draft.selected}
          disabled={busy}
          onChange={(e) => {
            update({ ...draft, selected: Number(e.target.value) })
            setResult(null)
          }}
        >
          {cells.map((c, i) => (
            <option key={i} value={i}>
              {i + 1}. {c.cell_type} — {c.source.slice(0, 75).replace(/\n/g, ' ') || '(empty)'}
            </option>
          ))}
        </select>
      </label>
      {cell.cell_type === 'code' && context && (
        <details open>
          <summary>Instructions before this code</summary>
          <Markdown text={draft.sources[context.i]} />
          <ReadAloud text={draft.sources[context.i]} />
        </details>
      )}
      {explanations?.[String(draft.selected + 1)] && (
        <div>
          <h4>Why this step</h4>
          <Markdown text={explanations[String(draft.selected + 1)]} />
        </div>
      )}
      {cell.cell_type === 'code' ? (
        <>
          <label id="notebook-code-label" htmlFor="notebook-code">
            Starter code — edit your working copy
          </label>
          <Button onClick={() => setPlain(!plain)}>{plain ? 'Use code editor' : 'Use plain editor'}</Button>
          <CodeEditor
            id="notebook-code"
            plain={plain}
            onPlainFallback={() => setPlain(true)}
            value={draft.sources[draft.selected]}
            onChange={(source) => {
              if (busy) stop()
              setCheckedRun(null)
              const sources = [...draft.sources]
              sources[draft.selected] = source
              update({ ...draft, sources })
              setResult(null)
            }}
          />
          <p className="text-sm">
            Browser practice runs standard-library Python only. Package installs (!pip), disk datasets and
            plot displays need the{' '}
            <a href="#complete-notebook-guide" className="underline">
              complete local notebook guide below
            </a>
            .
          </p>
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" disabled={busy} onClick={() => void run()}>
              Run through this cell
            </Button>
            {busy && <Button onClick={stop}>Stop run</Button>}
          </div>
        </>
      ) : cell.cell_type === 'markdown' ? (
        <>
          <Markdown text={draft.sources[draft.selected]} />
          <ReadAloud text={draft.sources[draft.selected]} />
        </>
      ) : (
        <pre className="whitespace-pre-wrap">{draft.sources[draft.selected]}</pre>
      )}
      <label className="block">
        Tutor focus
        <select
          className="block w-full border rounded p-2 bg-surface"
          value={tutorTarget ?? 'current'}
          onChange={(event) =>
            setTutorTarget(event.target.value === 'current' ? null : Number(event.target.value))
          }
        >
          <option value="current">Follow the selected notebook cell</option>
          {cells.map((entry, index) => {
            const title =
              entry.cell_type === 'markdown' ? draft.sources[index].match(/^#{1,3}\s+(.+)$/m)?.[1] : null
            return title ? (
              <option key={index} value={index}>
                Cell {index + 1}: {title}
              </option>
            ) : null
          })}
        </select>
      </label>
      <p className="text-sm text-muted">
        Choose a step to discuss, or select any notebook cell above. This does not run or change your code.
      </p>
      <p className="text-sm" id="notebook-answer-target">
        Answering {tutorTarget === null ? 'notebook cell' : 'step at cell'} {answerIndex + 1}:{' '}
        {draft.sources[answerIndex]
          .split('\n')
          .find((line) => line.trim())
          ?.replace(/^#+\s*/, '')
          .slice(0, 100) || '(empty cell)'}
      </p>
      <label className="block">
        Your prediction or explanation
        <textarea
          className="block w-full border border-line rounded p-2"
          aria-describedby="notebook-answer-target"
          value={draft.predictions[String(answerIndex)] ?? ''}
          onChange={(e) =>
            update({
              ...draft,
              predictions: { ...draft.predictions, [String(answerIndex)]: e.target.value },
            })
          }
          placeholder="Answer the selected question, predict the result, or explain what is unclear."
        />
      </label>
      <p role="status">{status}</p>
      {result && (
        <div>
          <h4>Python output</h4>
          <pre className="whitespace-pre-wrap break-words">
            {result.stdout || '(No printed output. Add print(...) to inspect a value.)'}
          </pre>
          {result.error && (
            <pre role="alert" className="whitespace-pre-wrap">
              {result.error}
            </pre>
          )}
          {result.truncated && <p>Output was shortened.</p>}
        </div>
      )}
      <NotebookTutor
        courseId={courseId}
        sectionId={sectionId}
        cells={cells}
        sources={draft.sources}
        index={tutorTarget ?? draft.selected}
        sectionFocus={tutorTarget !== null}
        identity={storageKey}
        explanations={explanations}
        answer={draft.predictions[String(tutorTarget ?? draft.selected)] ?? ''}
        output={tutorTarget === null || tutorTarget === draft.selected ? result : null}
      />
      {result?.results.map((c, i) => (
        <p key={i} role={c.passed ? 'status' : 'alert'}>
          {c.passed ? 'Passed' : 'Needs work'}: {c.name} — {c.detail}
        </p>
      ))}
      {onFinish && (
        <div className="grid gap-2">
          <details>
            <summary>What the checks verify</summary>
            {checks.map((c) => (
              <div key={c.name}>
                <p>{c.criterion}</p>
                <pre className="whitespace-pre-wrap break-words">{c.code}</pre>
              </div>
            ))}
          </details>
          <p>
            Run every cell and the separate calculation checks before returning results. A clean run verifies
            those checks only, not your interpretation or course completion.
          </p>
          {checkedRun && (
            <p role="status">
              Calculation checks passed for this unchanged notebook code. Your explanation has not been graded
              by these checks.
            </p>
          )}
          <Button disabled={busy} onClick={() => void run(true)}>
            Run all and check
          </Button>
          <Button
            disabled={!checkedRun || busy}
            onClick={() =>
              onFinish(
                `Notebook run and checks completed.\n${checkedRun?.stdout ?? ''}${checkedRun?.truncated ? '\n(Output shortened.)' : ''}`,
              )
            }
          >
            Return to task with results
          </Button>
        </div>
      )}
      <p>{saveStatus}</p>
      <Button onClick={download}>Export edited notebook</Button>
    </section>
  )
}

function NotebookTutor({
  courseId,
  sectionId,
  cells,
  sources,
  index,
  sectionFocus,
  identity,
  explanations,
  answer,
  output,
}: {
  courseId?: string
  sectionId?: string
  cells: NotebookCell[]
  sources: string[]
  index: number
  sectionFocus: boolean
  identity: string
  explanations?: Record<string, string>
  answer: string
  output: RunResult | null
}) {
  const cell = cells[index]
  const level = sources[index].match(/^(#{1,3})\s+.+$/m)?.[1].length
  let end = index + 1
  if (sectionFocus && level) {
    const next = cells.findIndex(
      (entry, i) =>
        i > index &&
        entry.cell_type === 'markdown' &&
        (sources[i].match(/^(#{1,3})\s+.+$/m)?.[1].length ?? 99) <= level,
    )
    end = next < 0 ? cells.length : next
  }
  const focused = cells.slice(index, end).map((entry, offset) => ({ entry, i: index + offset }))
  const focusedCode = focused
    .filter(({ entry }) => entry.cell_type === 'code')
    .map(({ i }) => `# Selected notebook cell ${i + 1}\n${sources[i]}`)
    .join('\n\n')
  const previous = cells
    .slice(0, index)
    .map((c, i) => ({ c, i }))
    .filter(({ c }) => c.cell_type === 'markdown')
    .at(-1)
  const title =
    sources[index]
      .split('\n')
      .find((line) => line.trim())
      ?.replace(/^#+\s*/, '')
      .slice(0, 100) || '(empty cell)'
  return (
    <StudyTutor
      courseId={courseId}
      sectionId={sectionId}
      targetLabel={`${sectionFocus ? 'Step' : 'Notebook cell ' + (index + 1)} — ${title}`}
      identity={`${identity}:${index}${sectionFocus ? ':step' : ''}`}
      key={`${identity}:${index}${sectionFocus ? ':step' : ''}`}
      context={`Notebook cell ${index + 1}. ${focused
        .filter(({ entry }) => entry.cell_type !== 'code')
        .map(({ i }) => sources[i])
        .join(
          '\n\n',
        )} ${explanations?.[String(index + 1)] ?? ''} ${cell.cell_type === 'code' && previous ? sources[previous.i] : ''}`}
      checkCode={focusedCode}
      code={
        focusedCode
          ? focusedCode +
            `\n\n# Earlier cells for context only\n` +
            cells
              .slice(0, index)
              .flatMap((c, i) => (c.cell_type === 'code' ? [`# Notebook cell ${i + 1}\n${sources[i]}`] : []))
              .join('\n\n')
          : undefined
      }
      output={
        output
          ? [
              output.stdout,
              output.error ? `Python error: ${output.error}` : '',
              output.truncated ? 'Output truncated.' : '',
            ]
              .filter(Boolean)
              .join('\n')
          : ''
      }
      answer={answer}
    />
  )
}
