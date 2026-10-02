import { fireEvent, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { renderApp } from '../../test/utils'
import { AssessmentHistoryDetails } from './AssessmentHistoryDetails'

it('shows historical question, options and criterion evidence without claiming current mastery', () => {
  renderApp(
    <AssessmentHistoryDetails
      metadata={{
        assessment_question: { question: 'Which value?', options: ['Five', 'Six'] },
        assessment_result: {
          score: 0.5,
          grader_level: 'rubric',
          criterion_results: [{ criterion: 'Names the unit', passed: false, evidence: 'Unit missing' }],
        },
      }}
    />,
  )
  fireEvent.click(screen.getByText('Question and grading details at the time'))
  expect(screen.getByText('Which value?')).toBeVisible()
  expect(screen.getByText('Five')).toBeVisible()
  expect(screen.getByText('Score on this attempt: 50%')).toBeVisible()
  expect(screen.getByText('Unit missing')).toBeVisible()
  expect(screen.getByText(/Reopening does not grade again/)).toBeVisible()
  expect(screen.getByText(/Source passages were not captured/)).toBeVisible()
})
