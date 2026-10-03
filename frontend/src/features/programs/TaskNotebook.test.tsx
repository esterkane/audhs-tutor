import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp, jsonResponse } from '../../test/utils'
import { TaskNotebook } from './TaskNotebook'
import { GuidedSection } from './GuidedSection'
vi.mock('./NotebookWorkspace', () => ({
  NotebookWorkspace: ({ onFinish, prelude }: { onFinish: (s: string) => void; prelude: string }) => (
    <>
      <p>Loaded local starter</p>
      <output>{prelude.includes('DATA_CSV') ? 'Dataset ready' : 'No dataset'}</output>
      <button onClick={() => onFinish('Checked output: fixture')}>Return test results</button>
    </>
  ),
}))
vi.mock('../voice/ReadAloud', () => ({ ReadAloud: () => null }))
vi.mock('./StudyTutor', () => ({ StudyTutor: () => null }))
afterEach(() => {
  vi.useRealTimers()
  localStorage.clear()
  vi.unstubAllGlobals()
})
it('opens the linked starter and dataset, returns output without losing notes, and restores notes on remount', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) =>
      url.endsWith('.csv')
        ? new Response('age\n18')
        : jsonResponse({
            nbformat: 4,
            metadata: { practice_checks: [{ name: 'count', criterion: 'Count', code: 'assert True' }] },
            cells: [{ cell_type: 'code', source: 'print(1)' }],
          }),
    ),
  )
  const section = {
    id: 's',
    title: 'Prepare data',
    explanation: 'Inspect first',
    task: 'Count rows',
    question: 'Why?',
    hint: 'Look',
    criteria: 'Explain',
    source: 'Fixture',
    practice: { notebook: '/local-learning/task.ipynb', dataset: '/local-learning/data.csv' },
  }
  const view = renderApp(<GuidedSection section={section} course="c" paused={false} />)
  fireEvent.click(screen.getByRole('button', { name: 'Try' }))
  fireEvent.change(screen.getByLabelText('Project notes'), { target: { value: 'My prior notes' } })
  fireEvent.click(screen.getByRole('button', { name: 'Open task starter notebook' }))
  expect(await screen.findByText('Dataset ready')).toBeVisible()
  expect(screen.getByRole('heading', { name: 'Notebook: Prepare data' })).toHaveFocus()
  fireEvent.click(screen.getByRole('button', { name: 'Return test results' }))
  expect(screen.getByLabelText('Project notes')).toHaveValue('My prior notes\n\nChecked output: fixture')
  await waitFor(() => expect(screen.getByRole('heading', { name: 'Your next project task' })).toHaveFocus())
  view.unmount()
  renderApp(<GuidedSection section={section} course="c" paused={false} />)
  expect(screen.getByLabelText('Project notes')).toHaveValue('My prior notes\n\nChecked output: fixture')
})
const notebook = {
  nbformat: 4,
  metadata: { practice_checks: [{ name: 'x', criterion: 'x', code: 'assert True' }] },
  cells: [{ cell_type: 'code', source: 'x=1' }],
}
const props = { identity: 'fixture', title: 'Fixture', paused: false, onBack: vi.fn() }
for (const stalled of ['notebook', 'dataset']) {
  it(`times out stalled ${stalled}, retries and ignores late response`, async () => {
    let finish!: (response: Response) => void
    let signal: AbortSignal | undefined
    let retry = false
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (
          !retry &&
          ((stalled === 'notebook' && url.endsWith('ipynb')) ||
            (stalled === 'dataset' && url.endsWith('csv')))
        ) {
          signal = init?.signal as AbortSignal
          return new Promise<Response>((resolve) => {
            finish = resolve
          })
        }
        return Promise.resolve(url.endsWith('csv') ? new Response('x\n1') : jsonResponse(notebook))
      }),
    )
    vi.useFakeTimers()
    renderApp(<TaskNotebook {...props} practice={{ notebook: '/one.ipynb', dataset: '/one.csv' }} />)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15001)
    })
    expect(signal?.aborted).toBe(true)
    expect(screen.getByRole('alert')).toHaveTextContent('not changed')
    expect(screen.queryByText('Loaded local starter')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Back to task without results' })).toBeEnabled()
    retry = true
    fireEvent.click(screen.getByRole('button', { name: 'Retry loading starter' }))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1)
    })
    expect(screen.getByText('Dataset ready')).toBeVisible()
    await act(async () => {
      finish(stalled === 'dataset' ? new Response('old') : jsonResponse(notebook))
    })
    expect(screen.getAllByText('Loaded local starter')).toHaveLength(1)
  })
}
it('clears loaded workspace on source change and never retains an old dataset', async () => {
  let finish!: (response: Response) => void
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url === '/two.ipynb')
        return new Promise<Response>((resolve) => {
          finish = resolve
        })
      return Promise.resolve(url.endsWith('csv') ? new Response('x\n1') : jsonResponse(notebook))
    }),
  )
  const view = renderApp(
    <TaskNotebook {...props} practice={{ notebook: '/one.ipynb', dataset: '/one.csv' }} />,
  )
  await screen.findByText('Dataset ready')
  view.rerender(<TaskNotebook {...props} practice={{ notebook: '/two.ipynb' }} />)
  expect(screen.queryByText('Dataset ready')).not.toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('Loading')
  await act(async () => {
    finish(jsonResponse(notebook))
  })
  expect(screen.getByText('No dataset')).toBeVisible()
})
it('aborts on unmount and ignores a late notebook response', async () => {
  let signal: AbortSignal | undefined
  let finish!: (response: Response) => void
  vi.stubGlobal(
    'fetch',
    vi.fn((_url: string, init?: RequestInit) => {
      signal = init?.signal as AbortSignal
      return new Promise<Response>((resolve) => {
        finish = resolve
      })
    }),
  )
  const view = renderApp(<TaskNotebook {...props} practice={{ notebook: '/one.ipynb' }} />)
  view.unmount()
  expect(signal?.aborted).toBe(true)
  await act(async () => {
    finish(jsonResponse(notebook))
  })
  expect(screen.queryByText('Loaded local starter')).not.toBeInTheDocument()
})
