import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { axe } from 'vitest-axe'
import { CorrectionComparison } from './CorrectionComparison'

it('shows changed answers, metadata and rubric, without hiding removed values', async () => {
  const { container } = render(<CorrectionComparison before={{ item: { question: 'Old?', answer: 0, source: 'kept' }, rubric: [{ criterion: 'Old rule' }] }} after={{ item: { question: 'New?', answer: 1 }, rubric: [{ criterion: 'New rule' }] }} beforeLabel="Original" afterLabel="Proposed" />)
  expect(screen.getByText('Old?')).toBeVisible()
  expect(screen.getByText('New?')).toBeVisible()
  expect(screen.getByText('Question metadata: source')).toBeVisible()
  expect(screen.getByText('Not present')).toBeVisible()
  expect(screen.getByText('Grading rubric')).toBeVisible()
  expect((await axe(container)).violations).toEqual([])
})
it('ignores object key order but detects ordered answer changes', () => {
  const { rerender } = render(<CorrectionComparison before={{ item: { a: 1, b: 2 } }} after={{ item: { b: 2, a: 1 } }} beforeLabel="Original" afterLabel="Proposed" />)
  expect(screen.getByText(/No question or rubric changes/)).toBeVisible()
  rerender(<CorrectionComparison before={{ item: { options: ['A', 'B'] } }} after={{ item: { options: ['B', 'A'] } }} beforeLabel="Original" afterLabel="Proposed" />)
  expect(screen.getByText('Answer options')).toBeVisible()
})
it('exposes malformed advanced payloads rather than claiming no changes', () => {
  render(<CorrectionComparison before={{ item: { question: 'Old?' } }} after={{ item: null }} beforeLabel="Original" afterLabel="Proposed" />)
  expect(screen.getByText('Question payload (incomplete or unstructured)')).toBeVisible()
  expect(screen.queryByText(/No question or rubric changes/)).not.toBeInTheDocument()
})
