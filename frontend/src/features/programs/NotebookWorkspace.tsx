import { useEffect, useRef, useState } from 'react'
import { Markdown } from '../../components/Markdown'
import { Button } from '../../components/ui/button'
import { CodeEditor } from '../code/CodeEditor'
import { createPyodideRunner, type Runner, type RunResult } from '../code/runner'
import type { NotebookCell } from './manifest'
import { StudyTutor } from './StudyTutor'
import { ReadAloud } from '../voice/ReadAloud'

type Props = {
  cells: NotebookCell[]
  identity: string
  explanations?: Record<string, string>
  runnerFactory?: () => Runner
}
type Draft = { sources: string[]; predictions: Record<string, string>; selected: number }
export function NotebookWorkspace(props: Props) {
  return <Workspace key={JSON.stringify([props.identity, props.cells])} {...props} />
}
function Workspace({ cells, identity, explanations, runnerFactory = createPyodideRunner }: Props) {
  const baseline = JSON.stringify(cells)
  let contentHash = 2166136261
  for (let i = 0; i < baseline.length; i += 1)
    contentHash = Math.imul(contentHash ^ baseline.charCodeAt(i), 16777619)
  const storageKey = `notebook-workspace:v1:${identity}:${(contentHash >>> 0).toString(16)}`
  const [restored] = useState(() => {
    const fresh: Draft = { sources: cells.map((c) => c.source), predictions: {}, selected: 0 }
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
  const [busy, setBusy] = useState(false)
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
  function stop() {
    if (deadline.current) clearTimeout(deadline.current)
    operation.current += 1
    runner.current?.dispose()
    runner.current = null
    setBusy(false)
    setStatus('Run stopped. Your edits are preserved.')
  }
  async function run() {
    if (busy) return
    const token = ++operation.current
    const selected = draft.selected
    setBusy(true)
    setResult(null)
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
      const code = cells
        .slice(0, selected + 1)
        .flatMap((c, i) =>
          c.cell_type === 'code' ? [`# Notebook cell ${i + 1}\n${draft.sources[i]}\n`] : [],
        )
        .join('\n')
      const output = await current.run(code, [], { timeoutMs: 30000, maxOutputChars: 20000, packages: [] })
      if (operation.current !== token) return
      setResult(output)
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
      cells: cells.map((c, i) => ({
        cell_type: c.cell_type,
        id: `cell-${i + 1}`,
        metadata: {},
        source: draft.sources[i],
        ...(c.cell_type === 'code' ? { execution_count: null, outputs: [] } : {}),
      })),
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
  const cell = cells[draft.selected]
  if (!cell) return <p>This notebook has no readable cells.</p>
  const context = cells
    .slice(0, draft.selected)
    .map((c, i) => ({ c, i }))
    .filter(({ c }) => c.cell_type === 'markdown')
    .at(-1)
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
        Your prediction or explanation
        <textarea
          className="block w-full border border-line rounded p-2"
          value={draft.predictions[String(draft.selected)] ?? ''}
          onChange={(e) =>
            update({
              ...draft,
              predictions: { ...draft.predictions, [String(draft.selected)]: e.target.value },
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
      <StudyTutor
        identity={`${storageKey}:${draft.selected}`}
        key={`${identity}:${draft.selected}`}
        context={`Notebook cell ${draft.selected + 1}. ${cell.cell_type !== 'code' ? cell.source : ''} ${explanations?.[String(draft.selected + 1)] ?? ''} ${context?.c.source ?? ''}`.slice(
          0,
          1000,
        )}
        code={
          cell.cell_type === 'code'
            ? cells
                .slice(0, draft.selected + 1)
                .flatMap((c, i) =>
                  c.cell_type === 'code' ? [`# Notebook cell ${i + 1}\n${draft.sources[i]}`] : [],
                )
                .join('\n\n')
            : undefined
        }
        output={
          result
            ? [
                result.stdout,
                result.error ? `Python error: ${result.error}` : '',
                result.truncated ? 'Output truncated.' : '',
              ]
                .filter(Boolean)
                .join('\n')
            : ''
        }
        answer={draft.predictions[String(draft.selected)] ?? ''}
      />
      <p>{saveStatus}</p>
      <Button onClick={download}>Export edited notebook</Button>
    </section>
  )
}
