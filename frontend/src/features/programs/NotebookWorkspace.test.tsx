import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { NotebookWorkspace } from './NotebookWorkspace'
import type { Runner, RunResult } from '../code/runner'
import type { NotebookCell } from './manifest'
vi.mock('../code/CodeEditor', () => ({
  CodeEditor: ({ id, value, onChange }: { id: string; value: string; onChange: (s: string) => void }) => (
    <textarea id={id} value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}))
vi.mock('./StudyTutor', () => ({
  StudyTutor: ({ code, output, context }: { code?: string; output?: string; context?: string }) => (
    <div data-testid="tutor-context">{JSON.stringify({ code, output, context })}</div>
  ),
}))
vi.mock('../voice/ReadAloud', () => ({ ReadAloud: () => <button>Listen</button> }))
afterEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
})
const cells: NotebookCell[] = [
  { cell_type: 'markdown', source: '## Add one\nUse the existing variable.' },
  { cell_type: 'code', source: 'x = 1' },
  { cell_type: 'code', source: 'print(x + 1)' },
]
const result: RunResult = { stdout: '2', error: null, ms: 1, results: [], timedOut: false, truncated: false }

it('lets the tutor focus on a named step without moving or running the editor', () => {
  const runner = fake()
  render(
    <NotebookWorkspace
      identity="steps"
      runnerFactory={() => runner}
      cells={[
        { cell_type: 'markdown', source: '## Step 1: Explore\nInspect rows.' },
        { cell_type: 'code', source: 'rows = 10' },
        { cell_type: 'markdown', source: '## Step 2: Compare' },
        { cell_type: 'markdown', source: 'Compare groups before and after cleaning.' },
        { cell_type: 'code', source: 'print(rows)' },
        { cell_type: 'markdown', source: '## Step 3: Conclude\nWrite a summary.' },
      ]}
    />,
  )
  fireEvent.change(screen.getByLabelText('Tutor focus'), { target: { value: '2' } })
  expect(screen.getByLabelText('Notebook cell')).toHaveValue('0')
  const payload = JSON.parse(screen.getByTestId('tutor-context').textContent!)
  expect(payload.context).toContain('Compare groups before and after cleaning.')
  expect(payload.context).not.toContain('Inspect rows.')
  expect(payload.context).not.toContain('Write a summary.')
  expect(payload.code).toMatch(/^# Selected notebook cell 5\nprint\(rows\)/)
  expect(runner.run).not.toHaveBeenCalled()
})
function fake(run = vi.fn(async () => result)): Runner {
  return { load: vi.fn(), run, dispose: vi.fn() }
}
it('shows starter context, executes preceding edited cells, and recovers drafts', async () => {
  const runner = fake()
  const view = render(<NotebookWorkspace identity="one" cells={cells} runnerFactory={() => runner} />)
  fireEvent.change(screen.getByLabelText('Notebook cell'), { target: { value: '1' } })
  expect(screen.getByText('Use the existing variable.')).toBeVisible()
  fireEvent.change(screen.getByLabelText('Starter code — edit your working copy'), {
    target: { value: 'x = 7' },
  })
  fireEvent.change(screen.getByLabelText('Your prediction or explanation'), {
    target: { value: 'Expect eight.' },
  })
  fireEvent.change(screen.getByLabelText('Notebook cell'), { target: { value: '2' } })
  fireEvent.click(screen.getByRole('button', { name: 'Run through this cell' }))
  await screen.findByText('2')
  expect(screen.getByTestId('tutor-context')).toHaveTextContent('x = 7')
  expect(screen.getByTestId('tutor-context')).toHaveTextContent('"output":"2"')
  expect(runner.run).toHaveBeenCalledWith(
    expect.stringContaining('x = 7\n\n# Notebook cell 3\nprint(x + 1)'),
    [],
    expect.objectContaining({ packages: [] }),
  )
  view.unmount()
  render(<NotebookWorkspace identity="one" cells={cells} />)
  expect(screen.getByLabelText('Your prediction or explanation')).toHaveValue('')
  fireEvent.change(screen.getByLabelText('Notebook cell'), { target: { value: '1' } })
  expect(screen.getByLabelText('Starter code — edit your working copy')).toHaveValue('x = 7')
  expect(screen.getByLabelText('Your prediction or explanation')).toHaveValue('Expect eight.')
})
it('stops runs and ignores their late results across notebook changes', async () => {
  let resolve!: (v: RunResult) => void
  const runner = fake(
    vi.fn(
      () =>
        new Promise<RunResult>((r) => {
          resolve = r
        }),
    ),
  )
  const view = render(<NotebookWorkspace identity="one" cells={cells} runnerFactory={() => runner} />)
  fireEvent.change(screen.getByLabelText('Notebook cell'), { target: { value: '1' } })
  fireEvent.click(screen.getByRole('button', { name: 'Run through this cell' }))
  fireEvent.click(screen.getByRole('button', { name: 'Stop run' }))
  expect(runner.dispose).toHaveBeenCalled()
  view.rerender(<NotebookWorkspace identity="two" cells={[{ cell_type: 'code', source: 'print(9)' }]} />)
  await act(async () => resolve({ ...result, stdout: 'stale output' }))
  expect(screen.queryByText('stale output')).toBeNull()
  expect(screen.getByLabelText('Starter code — edit your working copy')).toHaveValue('print(9)')
})
it('keeps edits usable when browser storage fails and handles failed runtime startup', async () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('full')
  })
  const runner = fake(
    vi.fn(async () => {
      throw new Error('Runtime missing')
    }),
  )
  render(<NotebookWorkspace identity="one" cells={cells} runnerFactory={() => runner} />)
  fireEvent.change(screen.getByLabelText('Notebook cell'), { target: { value: '1' } })
  fireEvent.change(screen.getByLabelText('Starter code — edit your working copy'), {
    target: { value: 'print(42)' },
  })
  expect(screen.getByText(/Could not save in this browser/)).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Run through this cell' }))
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Runtime missing'))
  expect(screen.getByLabelText('Starter code — edit your working copy')).toHaveValue('print(42)')
})
it('keeps independent drafts for different uploads sharing the same identity', () => {
  const original: NotebookCell[] = [{ cell_type: 'code', source: 'print(1)' }]
  const other: NotebookCell[] = [{ cell_type: 'code', source: 'print(2)' }]
  const view = render(<NotebookWorkspace identity="uploaded" cells={original} />)
  fireEvent.change(screen.getByLabelText('Starter code — edit your working copy'), {
    target: { value: 'print(11)' },
  })
  view.rerender(<NotebookWorkspace identity="uploaded" cells={other} />)
  expect(screen.getByLabelText('Starter code — edit your working copy')).toHaveValue('print(2)')
  fireEvent.change(screen.getByLabelText('Starter code — edit your working copy'), {
    target: { value: 'print(22)' },
  })
  view.rerender(<NotebookWorkspace identity="uploaded" cells={original} />)
  expect(screen.getByLabelText('Starter code — edit your working copy')).toHaveValue('print(11)')
})
it('stops a runtime that never finishes loading and uses one-based cell explanations', () => {
  vi.useFakeTimers()
  try {
    const runner = fake(vi.fn(() => new Promise<RunResult>(() => {})))
    const view = render(
      <NotebookWorkspace
        identity="slow"
        cells={[{ cell_type: 'code', source: 'print(1)' }]}
        explanations={{ '1': 'This prints a number.' }}
        runnerFactory={() => runner}
      />,
    )
    expect(screen.getByText('This prints a number.')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Run through this cell' }))
    act(() => vi.advanceTimersByTime(45000))
    expect(runner.dispose).toHaveBeenCalled()
    expect(screen.getByRole('status')).toHaveTextContent('took too long')
    expect(screen.getByRole('button', { name: 'Run through this cell' })).toBeEnabled()
    view.unmount()
  } finally {
    vi.useRealTimers()
  }
})
it('exports edited source in a valid notebook without claiming to preserve old outputs', async () => {
  let exported!: Blob
  const originalURL = URL
  vi.stubGlobal('URL', {
    createObjectURL: vi.fn((blob: Blob) => {
      exported = blob
      return 'blob:export'
    }),
    revokeObjectURL: vi.fn(),
  })
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  try {
    render(<NotebookWorkspace identity="export" cells={[{ cell_type: 'code', source: 'print(1)' }]} />)
    fireEvent.change(screen.getByLabelText('Starter code — edit your working copy'), {
      target: { value: 'print(42)' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Export edited notebook' }))
    const text = await new Promise<string>((resolve) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result))
      reader.readAsText(exported)
    })
    expect(JSON.parse(text)).toMatchObject({
      nbformat: 4,
      cells: [{ source: 'print(42)', cell_type: 'code', outputs: [], execution_count: null }],
    })
  } finally {
    vi.stubGlobal('URL', originalURL)
  }
})

it('accepts answers to markdown questions and gives the tutor the current question first', () => {
  render(
    <NotebookWorkspace
      identity="questions"
      cells={[
        { cell_type: 'markdown', source: 'Prior context '.repeat(200) },
        { cell_type: 'markdown', source: 'Why hold out test data?' },
      ]}
    />,
  )
  fireEvent.change(screen.getByLabelText('Notebook cell'), { target: { value: '1' } })
  fireEvent.change(screen.getByLabelText('Your prediction or explanation'), {
    target: { value: 'To estimate generalization.' },
  })
  expect(screen.getByLabelText('Your prediction or explanation')).toHaveValue('To estimate generalization.')
  expect(screen.getByTestId('tutor-context')).toHaveTextContent('Why hold out test data?')
})

it('requires a clean full run before returning results and invalidates results after edits', async () => {
  const done = vi.fn()
  const runner = fake(
    vi.fn(async () => ({ ...result, results: [{ name: 'check', passed: true, detail: 'passed' }] })),
  )
  render(
    <NotebookWorkspace
      identity="task"
      checks={[{ name: 'check', criterion: 'Check x', code: 'assert x == 1' }]}
      cells={cells}
      prelude="DATA_CSV = 'fixture'\n"
      onFinish={done}
      runnerFactory={() => runner}
    />,
  )
  const finish = screen.getByRole('button', { name: 'Return to task with results' })
  expect(finish).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Run all and check' }))
  await waitFor(() => expect(finish).toBeEnabled())
  expect(runner.run).toHaveBeenCalledWith(
    expect.stringContaining("DATA_CSV = 'fixture'"),
    expect.arrayContaining([expect.objectContaining({ name: 'check' })]),
    expect.any(Object),
  )
  expect(runner.run).toHaveBeenCalledWith(
    expect.stringContaining('print(x + 1)'),
    expect.arrayContaining([expect.objectContaining({ name: 'check' })]),
    expect.any(Object),
  )
  fireEvent.click(finish)
  expect(done).toHaveBeenCalledWith(expect.stringContaining('2'))
  fireEvent.change(screen.getByLabelText('Notebook cell'), { target: { value: '1' } })
  fireEvent.change(screen.getByLabelText('Starter code — edit your working copy'), {
    target: { value: 'x = 9' },
  })
  expect(finish).toBeDisabled()
})

it('does not allow failed full runs to be returned as checked results', async () => {
  const runner = fake(vi.fn(async () => ({ ...result, error: 'AssertionError: fill in bins' })))
  render(
    <NotebookWorkspace
      identity="failed-task"
      cells={cells}
      onFinish={vi.fn()}
      runnerFactory={() => runner}
    />,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Run all and check' }))
  await screen.findByText('AssertionError: fill in bins')
  expect(screen.getByRole('button', { name: 'Return to task with results' })).toBeDisabled()
})

it('does not confuse successful execution with missing or failed separate checks', async () => {
  const runner = fake()
  render(
    <NotebookWorkspace
      identity="no-check-result"
      cells={[{ cell_type: 'code', source: '# assertion cell removed' }]}
      checks={[{ name: 'required', criterion: 'Real check', code: 'assert False' }]}
      onFinish={vi.fn()}
      runnerFactory={() => runner}
    />,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Run all and check' }))
  await waitFor(() => expect(runner.dispose).toHaveBeenCalled())
  expect(screen.getByRole('button', { name: 'Return to task with results' })).toBeDisabled()
})
