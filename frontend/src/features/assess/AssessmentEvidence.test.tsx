import { render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import { AssessmentEvidence } from './AssessmentEvidence'

const result = { feedback: 'Compare the retained proportions.', next_step: 'Reconsider the denominator.', misconception: null }
it('orders recorded strengths before gaps and preserves evidence exactly', () => {
  render(<AssessmentEvidence result={{ ...result, criterion_results: [
    { criterion: 'Compare proportions', passed: false, evidence: 'Only totals were compared.' },
    { criterion: 'Identify groups', passed: true, evidence: 'Both groups were named.' },
  ] }} />)
  expect(screen.getAllByRole('heading').map(h => h.textContent)).toEqual(['What was right', 'Not quite — what to reconsider', 'Why'])
  expect(within(screen.getByRole('region', { name: 'What was right' })).getByText('Both groups were named.', { exact: false })).toBeVisible()
  expect(within(screen.getByRole('region', { name: 'What to reconsider' })).getByText('Only totals were compared.', { exact: false })).toBeVisible()
})
it('does not invent strengths or gaps when criteria are absent', () => {
  render(<AssessmentEvidence result={{ ...result, criterion_results: [] }} />)
  expect(screen.getByText(/did not provide a criterion-by-criterion/)).toBeVisible()
  expect(screen.queryByRole('heading', { name: 'What was right' })).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Not quite — what to reconsider' })).not.toBeInTheDocument()
  expect(screen.getByText(result.feedback)).toBeVisible()
})
it('does not invent a failed criterion for a fully satisfied rubric', () => {
  render(<AssessmentEvidence result={{ ...result, criterion_results: [{ criterion: 'Identify groups', passed: true, evidence: '' }] }} />)
  expect(screen.getByRole('heading', { name: 'What was right' })).toBeVisible()
  expect(screen.queryByRole('heading', { name: 'Not quite — what to reconsider' })).not.toBeInTheDocument()
})

it('separates an unmet criterion from the chosen wrong option without rewriting either', () => {
  render(<AssessmentEvidence result={{ ...result, criterion_results: [
    { criterion: 'selects the correct option', passed: false, evidence: '9' },
  ] }} />)
  const gap = within(screen.getByRole('region', { name: 'What to reconsider' }))
  expect(gap.getByText('Criterion:')).toBeVisible()
  expect(gap.getByText('selects the correct option', { exact: false })).toHaveTextContent('Criterion: selects the correct option')
  expect(gap.getByText('Recorded evidence:')).toBeVisible()
  expect(gap.getByText('9', { exact: false })).toHaveTextContent('Recorded evidence: 9')
  expect(screen.queryByRole('heading', { name: 'What was right' })).not.toBeInTheDocument()
})
