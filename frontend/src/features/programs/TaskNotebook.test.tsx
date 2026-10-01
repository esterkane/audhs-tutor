import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp, jsonResponse } from '../../test/utils'
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
