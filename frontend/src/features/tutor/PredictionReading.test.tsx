import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { PredictionReading } from './PredictionReading'
afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks() })
const reader = (identity = 'object:sha1') => <PredictionReading identity={identity} title="Row filtering"><p>Policies do not grant SQL privileges.</p></PredictionReading>
it('keeps the answer out of the DOM until an attempt or explicit skip, then restores original and correction', () => {
  let view = render(reader())
  expect(screen.queryByText('Policies do not grant SQL privileges.')).toBeNull()
  expect(screen.getByRole('button', { name: 'Save prediction and read' })).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Your prediction (optional)'), { target: { value: 'Maybe a policy grants UPDATE.' } })
  view.unmount(); view = render(reader())
  expect(screen.getByLabelText('Your prediction (optional)')).toHaveValue('Maybe a policy grants UPDATE.')
  fireEvent.click(screen.getByRole('button', { name: 'Save prediction and read' }))
  expect(screen.getByText('Policies do not grant SQL privileges.')).toBeVisible()
  fireEvent.change(screen.getByLabelText('How did your prediction compare?'), { target: { value: 'changed' } })
  fireEvent.change(screen.getByLabelText('What changed, and which passage helped? (optional)'), { target: { value: 'The first sentence distinguishes grants from filters.' } })
  view.unmount(); view = render(reader())
  expect(screen.getByText('Maybe a policy grants UPDATE.')).toBeVisible()
  expect(screen.getByLabelText('How did your prediction compare?')).toHaveValue('changed')
  expect(screen.getByLabelText('What changed, and which passage helped? (optional)')).toHaveValue('The first sentence distinguishes grants from filters.')
  view.rerender(reader('object:sha2'))
  expect(screen.getByLabelText('Your prediction (optional)')).toHaveValue('')
  expect(localStorage.getItem('reading-prediction:v1:object:sha1')).toContain('Maybe a policy grants UPDATE.')
})
it('never requires prediction or confidence and keeps explicit skip across reloads', () => {
  const view = render(reader())
  fireEvent.click(screen.getByRole('button', { name: 'Read without predicting' }))
  expect(screen.queryByRole('group', { name: 'Compare after reading' })).toBeNull()
  view.unmount(); render(reader())
  expect(screen.getByText('Policies do not grant SQL privileges.')).toBeVisible()
})
it('does not block reading on denied/corrupt storage and preserves in-memory attempts on quota failure', () => {
  localStorage.setItem('reading-prediction:v1:object:sha1', '{bad')
  const view = render(reader())
  expect(screen.getByText('Policies do not grant SQL privileges.')).toBeVisible()
  view.rerender(reader('object:new'))
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Full') })
  fireEvent.change(screen.getByLabelText('Your prediction (optional)'), { target: { value: 'Keep my attempt' } })
  expect(screen.getByLabelText('Your prediction (optional)')).toHaveValue('Keep my attempt')
  expect(screen.getByRole('status')).toHaveTextContent('Could not save')
  fireEvent.click(screen.getByRole('button', { name: 'Save prediction and read' }))
  expect(screen.getByText('Keep my attempt')).toBeVisible()
})
it('has accessible labels before and after reveal', async () => {
  const { container } = render(reader())
  expect((await axe(container)).violations).toEqual([])
  fireEvent.change(screen.getByLabelText('Your prediction (optional)'), { target: { value: 'A specific guess' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save prediction and read' }))
  expect((await axe(container)).violations).toEqual([])
})
it('does not put a new prediction gate in front of existing same-version reading progress', () => {
  localStorage.setItem('lesson-reader:v1:saved-lesson:object:sha1:hash', JSON.stringify({ reading: { selected: 1, notes: { '1': 'Keep this' } } }))
  render(<PredictionReading identity="object:sha1" title="Row filtering" resumeKeyPrefix="lesson-reader:v1:saved-lesson:object:sha1:"><p>Continue reading</p></PredictionReading>)
  expect(screen.getByText('Continue reading')).toBeVisible()
  expect(screen.queryByLabelText('Your prediction (optional)')).toBeNull()
  expect(localStorage.getItem('lesson-reader:v1:saved-lesson:object:sha1:hash')).toContain('Keep this')
})


it('shows the authored question, retains its original attempt and isolates another question identity', () => {
  const first = <PredictionReading identity="accepted:v1:explanation:q1" title="Explanation" question="Which values can be joined?"><p>Accepted passage</p></PredictionReading>
  const view = render(first)
  expect(screen.getByText(/Which values can be joined/)).toBeVisible()
  fireEvent.change(screen.getByLabelText('Your prediction (optional)'), { target: { value: 'Only strings.' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save prediction and read' }))
  expect(JSON.parse(localStorage.getItem('reading-prediction:v1:accepted:v1:explanation:q1')!).prompt).toBe('Which values can be joined?')
  view.rerender(<PredictionReading identity="accepted:v2:explanation:q2" title="Explanation" question="What changes after conversion?"><p>Accepted passage</p></PredictionReading>)
  expect(screen.getByLabelText('Your prediction (optional)')).toHaveValue('')
  expect(localStorage.getItem('reading-prediction:v1:accepted:v1:explanation:q1')).toContain('Only strings.')
})

it('existing reading bypasses a new section prompt without deleting an earlier attempt', () => {
  render(<PredictionReading identity="accepted:v1:example:q2" title="Worked example" question="What happens next?" resumeReading><p>Continue accepted reading</p></PredictionReading>)
  expect(screen.getByText('Continue accepted reading')).toBeVisible()
  expect(screen.queryByLabelText('Your prediction (optional)')).toBeNull()
})
