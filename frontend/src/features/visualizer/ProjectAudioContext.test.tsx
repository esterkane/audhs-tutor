import { act, fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp, jsonResponse } from '../../test/utils'
import { parseProgram } from '../programs/manifest'
import { ProjectAudioContext } from './ProjectAudioContext'
const section = {
  id: 'one',
  title: 'Frequency task',
  explanation: 'Read.',
  task: 'Try.',
  question: 'Why?',
  hint: 'Think.',
  criteria: 'Explain.',
  source: 'Fixture',
  audioLab: { lesson: 'frequency', purpose: 'Compare the cycles.' },
}
const program = {
  title: 'Fixture',
  courses: [{ id: 'course', title: 'Signals', project: 'Test', status: 'Fixture', sections: [section] }],
}
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})
it('requires a known authored lesson and bounded purpose', () => {
  for (const audioLab of [
    null,
    {},
    { lesson: 'unknown', purpose: 'Try' },
    { lesson: 'frequency', purpose: ' ' },
    { lesson: 'frequency', purpose: 'x'.repeat(601) },
  ]) {
    expect(() =>
      parseProgram({
        ...program,
        courses: [{ ...program.courses[0], sections: [{ ...section, audioLab }] }],
      }),
    ).toThrow()
  }
  expect(parseProgram(program).courses[0].sections[0].audioLab?.lesson).toBe('frequency')
})
it('does not open a lesson until explicitly requested and recovers a failed load', async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(jsonResponse({}, 503))
    .mockResolvedValue(jsonResponse(program))
  vi.stubGlobal('fetch', fetcher)
  const onOpen = vi.fn()
  renderApp(
    <ProjectAudioContext
      courseId="course"
      sectionId="one"
      expectedLesson="frequency"
      disabled={false}
      onOpen={onOpen}
    />,
  )
  fireEvent.click(await screen.findByRole('button', { name: 'Retry project link' }))
  const open = await screen.findByRole('button', { name: 'Open linked lesson: Frequency' })
  expect(onOpen).not.toHaveBeenCalled()
  fireEvent.click(open)
  expect(onOpen).toHaveBeenCalledWith('frequency')
  expect(screen.getByRole('link')).toHaveAttribute('href', '/programs?course=course&step=one')
})
it('ignores late material after unmount and times out without opening anything', async () => {
  vi.useFakeTimers()
  let deliver!: (value: Response) => void
  vi.stubGlobal(
    'fetch',
    vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          deliver = resolve
        }),
    ),
  )
  const onOpen = vi.fn()
  const view = renderApp(
    <ProjectAudioContext
      courseId="course"
      sectionId="one"
      expectedLesson="frequency"
      disabled={false}
      onOpen={onOpen}
    />,
  )
  await act(async () => {
    vi.advanceTimersByTime(15001)
  })
  expect(screen.getByRole('status')).toHaveTextContent('took too long')
  await act(async () => {
    deliver(jsonResponse(program))
  })
  expect(screen.queryByRole('button', { name: /Open linked lesson/ })).toBeNull()
  view.unmount()
  expect(onOpen).not.toHaveBeenCalled()
})
