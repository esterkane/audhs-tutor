import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp } from '../../test/utils'
import { GuidedSection } from './GuidedSection'
vi.mock('../voice/ReadAloud', () => ({ ReadAloud: () => null }))
vi.mock('./StudyTutor', () => ({ StudyTutor: () => null }))
vi.mock('./TaskNotebook', () => ({
  TaskNotebook: ({ onBack }: { onBack: (summary?: string) => void }) => (
    <div>
      <h2>Restored notebook</h2>
      <button onClick={() => onBack()}>Return without results</button>
    </div>
  ),
}))
const section = {
  id: 'step',
  title: 'Count',
  explanation: 'Count rows.',
  task: 'Try counting.',
  question: 'Why?',
  hint: 'Rows.',
  criteria: 'Explain.',
  source: 'Fixture',
  practice: { notebook: '/local-learning/one.ipynb', dataset: '/local-learning/one.csv' },
}
afterEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
})
function open() {
  fireEvent.click(screen.getByRole('button', { name: 'Try' }))
  fireEvent.change(screen.getByLabelText('Project notes'), { target: { value: 'Keep my notes' } })
  fireEvent.click(screen.getByRole('button', { name: 'Open task starter notebook' }))
}
it('recovers the task notebook and clears the view on explicit return, preserving notes', () => {
  const first = renderApp(<GuidedSection section={section} course="course" paused={false} />)
  open()
  first.unmount()
  const next = renderApp(<GuidedSection section={section} course="course" paused={false} />)
  expect(screen.getByRole('heading', { name: 'Restored notebook' })).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Return without results' }))
  expect(screen.getByLabelText('Project notes')).toHaveValue('Keep my notes')
  next.unmount()
  renderApp(<GuidedSection section={section} course="course" paused={false} />)
  expect(screen.queryByRole('heading', { name: 'Restored notebook' })).toBeNull()
})
it('does not silently reopen changed dataset links', () => {
  const first = renderApp(<GuidedSection section={section} course="course" paused={false} />)
  open()
  first.unmount()
  renderApp(
    <GuidedSection
      section={{ ...section, practice: { ...section.practice, dataset: '/local-learning/two.csv' } }}
      course="course"
      paused={false}
    />,
  )
  expect(screen.queryByRole('heading', { name: 'Restored notebook' })).toBeNull()
  expect(screen.getByRole('status')).toHaveTextContent('link changed')
  expect(screen.getByLabelText('Project notes')).toHaveValue('Keep my notes')
})
it('keeps saving failures visible in the notebook view', () => {
  renderApp(<GuidedSection section={section} course="course" paused={false} />)
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('denied')
  })
  open()
  expect(screen.getByRole('heading', { name: 'Restored notebook' })).toBeVisible()
  expect(screen.getByRole('status')).toHaveTextContent('Could not save')
})
