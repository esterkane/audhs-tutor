import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Programs } from './Programs'
import { parseNotebook, parseProgram } from '../features/programs/manifest'
import { jsonResponse, renderApp } from '../test/utils'
afterEach(() => {
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
