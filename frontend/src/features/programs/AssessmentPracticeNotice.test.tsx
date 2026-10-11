import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { AssessmentPracticeNotice } from './AssessmentSaveStatus'

it('labels repeated practice without claiming independent evidence or new scheduling', () => {
  render(<AssessmentPracticeNotice result={{ revision_of_attempt_id: 'original' }} />)
  expect(screen.getByText(/Repeated practice on a previously checked question/)).toHaveTextContent('does not add independent learning evidence or change your review schedule')
})
it('does not label an ordinary or legacy result as revised', () => {
  const { container } = render(<AssessmentPracticeNotice result={{}} />)
  expect(container).toBeEmptyDOMElement()
})
