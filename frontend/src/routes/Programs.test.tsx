import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Programs } from './Programs'
import { parseNotebook, parseProgram } from '../features/programs/manifest'
import { jsonResponse, renderApp } from '../test/utils'
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  localStorage.clear()
})
const fixture = {
  title: 'Local programme',
  courses: [
    {
      id: 'example',
      title: 'Example course',
      project: 'Build a small model',
      status: 'Fixture',
      sections: [
        {
          id: 'split',
          title: 'Data split',
          explanation: 'Keep test data separate.',
          task: 'Split the data.',
          question: 'Why keep a test set?',
          hint: 'Think of unseen data.',
          criteria: 'Explain selection bias.',
          source: 'Synthetic fixture',
        },
      ],
    },
  ],
}
it('explains first, preserves notes through pause and remount, and makes checks explicit', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse(fixture)),
  )
  const page = renderApp(<Programs />)
  expect(await screen.findByText('Keep test data separate.')).toBeVisible()
  expect(screen.queryByText('Think of unseen data.')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Think deeper' }))
  fireEvent.click(screen.getByText('One hint'))
  expect(screen.getByText('Think of unseen data.')).toBeVisible()
  fireEvent.change(screen.getByLabelText('Your explanation'), {
    target: { value: 'Avoid using test labels for selection.' },
  })
  fireEvent.click(screen.getByText('Pause study'))
  expect(screen.queryByRole('button', { name: 'Listen to explanation' })).toBeNull()
  expect(screen.queryByRole('region', { name: 'Study tutor' })).toBeNull()
  expect(screen.getByLabelText('Your explanation')).not.toBeVisible()
  fireEvent.click(screen.getByText('Resume this step'))
  expect(screen.getByLabelText('Your explanation')).toHaveValue('Avoid using test labels for selection.')
  page.unmount()
  renderApp(<Programs />)
  await waitFor(() =>
    expect(screen.getByLabelText('Your explanation')).toHaveValue('Avoid using test labels for selection.'),
  )
})
it('rejects malformed content and never renders notebook outputs as executable HTML', () => {
  expect(() => parseProgram({})).toThrow()
  expect(() => parseNotebook({ nbformat: 4, cells: [{ cell_type: 'code', source: 42 }] })).toThrow()
  expect(
    parseNotebook({
      nbformat: 4,
      cells: [
        {
          cell_type: 'code',
          source: ['print(1)'],
          outputs: [{ data: { 'text/html': '<script>bad</script>' } }],
        },
      ],
    }),
  ).toEqual([{ cell_type: 'code', source: 'print(1)' }])
})

it('rejects invalid saved notebook paths', () => {
  for (const notebook of [{}, '/local-learning/../secret.ipynb', 'https://example.org/a.ipynb']) {
    expect(() => parseProgram({ ...fixture, courses: [{ ...fixture.courses[0], notebook }] })).toThrow()
  }
  expect(
    parseProgram({
      ...fixture,
      courses: [{ ...fixture.courses[0], notebook: '/local-learning/starter.ipynb' }],
    }).courses[0].notebook,
  ).toBe('/local-learning/starter.ipynb')
})

it('validates authored examples and distinct deeper questions', () => {
  const section = fixture.courses[0].sections[0]
  const parse = (extra: object) =>
    parseProgram({ ...fixture, courses: [{ ...fixture.courses[0], sections: [{ ...section, ...extra }] }] })
  expect(() => parse({ example: 42 })).toThrow()
  expect(() =>
    parse({
      challenges: [
        { id: 'same', question: 'Why?', hint: 'Look closer', criteria: 'Give evidence' },
        { id: 'same', question: 'Why?', hint: 'Look closer', criteria: 'Give evidence' },
      ],
    }),
  ).toThrow()
  expect(() => parse({ challenges: [{ id: 'missing', question: 'Why?' }] })).toThrow()
  expect(
    parse({
      example: 'A synthetic worked example.',
      challenges: [
        {
          id: 'transfer',
          question: 'What changes?',
          hint: 'Change one assumption.',
          criteria: 'Explain the effect.',
        },
      ],
    }).courses[0].sections[0].challenges,
  ).toHaveLength(1)
})

it('restores a selected non-first course and project step after reload', async () => {
  const original = fixture.courses[0]
  const second = {
    ...original,
    id: 'second',
    title: 'Second course',
    sections: [
      original.sections[0],
      {
        ...original.sections[0],
        id: 'evaluate',
        title: 'Evaluate results',
        explanation: 'Compare held-out predictions.',
      },
    ],
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse({ ...fixture, courses: [original, second] })),
  )
  const view = renderApp(<Programs />)
  await screen.findByText('Keep test data separate.')
  fireEvent.change(screen.getByLabelText('Course'), { target: { value: 'second' } })
  fireEvent.change(screen.getByLabelText('Project step'), { target: { value: 'evaluate' } })
  await screen.findByText('Compare held-out predictions.')
  view.unmount()
  renderApp(<Programs />)
  expect(await screen.findByText('Compare held-out predictions.')).toBeVisible()
  expect(screen.getByLabelText('Course')).toHaveValue('second')
})

it('keeps course switching secondary and returns from full notebook tools to the same notes', async () => {
  const fetcher = vi.fn(async (url: string) =>
    jsonResponse(
      url === '/api/notebooks/status'
        ? { status: 'idle', message: 'Ready to prepare', course_id: '' }
        : fixture,
    ),
  )
  vi.stubGlobal('fetch', fetcher)
  renderApp(<Programs />)
  await screen.findByText('Keep test data separate.')
  expect(screen.getByLabelText('Course')).not.toBeVisible()
  expect(fetcher.mock.calls.some(([url]) => url === '/api/notebooks/status')).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: 'Try' }))
  fireEvent.change(screen.getByLabelText('Project notes'), { target: { value: 'My observation' } })
  fireEvent.click(
    within(screen.getByRole('region', { name: 'Guided lesson' })).getByRole('button', {
      name: 'Open full course notebook tools',
    }),
  )
  await screen.findByText('Ready to prepare')
  expect(screen.getByRole('button', { name: 'Prepare and start notebook lab' })).toBeVisible()
  expect(screen.getByLabelText('Project notes')).not.toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Back to guided lesson' }))
  expect(screen.getByLabelText('Project notes')).toBeVisible()
  expect(screen.getByLabelText('Project notes')).toHaveValue('My observation')
  expect(screen.queryByRole('button', { name: 'Prepare and start notebook lab' })).toBeNull()
  expect(fetcher.mock.calls.some(([url]) => url === '/api/notebooks/start')).toBe(false)
})

it('discloses an unavailable saved location without deleting existing study notes', async () => {
  localStorage.setItem(
    'project-study-location:v1',
    JSON.stringify({ version: 1, courseId: 'removed', sectionId: 'gone', notebook: false }),
  )
  localStorage.setItem('project-study:v1:removed:gone', 'retained note')
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse(fixture)),
  )
  renderApp(<Programs />)
  await screen.findByText(/saved course or step is no longer available/)
  expect(localStorage.getItem('project-study:v1:removed:gone')).toBe('retained note')
  fireEvent.change(screen.getByLabelText('Project step'), { target: { value: 'split' } })
  expect(screen.queryByText(/saved course or step is no longer available/)).toBeNull()
})

it('keeps navigation usable while reporting location storage failure', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse(fixture)),
  )
  renderApp(<Programs />)
  await screen.findByText('Keep test data separate.')
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('quota')
  })
  fireEvent.change(screen.getByLabelText('Project step'), { target: { value: 'split' } })
  expect(screen.getByText(/place could not be saved/)).toBeVisible()
  expect(screen.getByText('Keep test data separate.')).toBeVisible()
})
