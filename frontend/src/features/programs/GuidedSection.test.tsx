import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp } from '../../test/utils'
import { GuidedSection } from './GuidedSection'
vi.mock('../voice/ReadAloud', () => ({
  ReadAloud: (props: { text: string; label?: string }) => (
    <button aria-label={props.label}>{props.text}</button>
  ),
}))
vi.mock('./StudyTutor', () => ({
  StudyTutor: (props: { context: string; answer: string; reviewOnly?: boolean }) =>
    props.reviewOnly ? (
      <div>
        <output aria-label="Answer check context">{props.context}</output>
        <output aria-label="Answer to check">{props.answer}</output>
      </div>
    ) : (
      <div>
        <span>Contextual tutor</span>
        <output aria-label="Tutor context">{props.context}</output>
        <output aria-label="Tutor answer">{props.answer}</output>
      </div>
    ),
}))
const section = {
  id: 'split',
  title: 'Data split',
  explanation: 'Keep test data separate.',
  example: 'Train on A, evaluate on B.',
  task: 'Split the dataset.',
  question: 'Why hold out data?',
  hint: 'Think unseen.',
  criteria: 'Explain selection bias.',
  source: 'Synthetic fixture',
  challenges: [
    {
      id: 'tradeoff',
      question: 'What if the test set is too small?',
      hint: 'Think variance.',
      criteria: 'Explain uncertainty.',
    },
  ],
}
afterEach(() => localStorage.clear())
it('starts with explanation and example without an answer form, then focuses user-selected steps', () => {
  renderApp(<GuidedSection section={section} course="course" paused={false} />)
  expect(screen.getByText(section.explanation)).toBeVisible()
  expect(screen.getByText(section.example)).toBeVisible()
  expect(screen.queryByLabelText('Your explanation')).toBeNull()
  expect(screen.queryByText('Contextual tutor')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Try' }))
  expect(screen.getByRole('heading', { name: 'Your next project task' })).toHaveFocus()
  expect(screen.getByText(section.task, { selector: 'p' })).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Think deeper' }))
  expect(screen.getByLabelText('Your explanation')).toBeVisible()
})
it('preserves original legacy answers and independent challenge responses across phases and remount', () => {
  localStorage.setItem(
    'project-study:v1:course:split',
    JSON.stringify({ answer: 'Legacy answer', note: 'Legacy note', label: 'Clear' }),
  )
  const view = renderApp(<GuidedSection section={section} course="course" paused={false} />)
  fireEvent.click(screen.getByRole('button', { name: 'Think deeper' }))
  expect(screen.getByLabelText('Your explanation')).toHaveValue('Legacy answer')
  fireEvent.change(screen.getByLabelText('Question to explore'), { target: { value: 'challenge:tradeoff' } })
  expect(screen.getByLabelText('Your explanation')).toHaveValue('')
  fireEvent.change(screen.getByLabelText('Your explanation'), { target: { value: 'Small samples vary.' } })
  fireEvent.click(screen.getByRole('button', { name: 'Try' }))
  expect(screen.getByLabelText('Project notes')).toHaveValue('Legacy note')
  fireEvent.click(screen.getByRole('button', { name: 'Think deeper' }))
  expect(screen.getByLabelText('Your explanation')).toHaveValue('Small samples vary.')
  view.unmount()
  renderApp(<GuidedSection section={section} course="course" paused={false} />)
  expect(screen.getByLabelText('Your explanation')).toHaveValue('Small samples vary.')
  fireEvent.change(screen.getByLabelText('Question to explore'), { target: { value: 'original' } })
  expect(screen.getByLabelText('Your explanation')).toHaveValue('Legacy answer')
})
it('unmounts audio and tutor on pause while preserving phase and written work', () => {
  const view = renderApp(<GuidedSection section={section} course="course" paused={false} />)
  fireEvent.click(screen.getByRole('button', { name: 'Think deeper' }))
  fireEvent.change(screen.getByLabelText('Your explanation'), { target: { value: 'My work' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ask the tutor' }))
  expect(screen.getByText('Contextual tutor')).toBeVisible()
  view.rerender(<GuidedSection section={section} course="course" paused />)
  expect(screen.queryByText('Contextual tutor')).toBeNull()
  expect(screen.queryByRole('button', { name: 'Listen to question' })).toBeNull()
  view.rerender(<GuidedSection section={section} course="course" paused={false} />)
  expect(screen.getByLabelText('Your explanation')).toHaveValue('My work')
})

it('sends phase-specific complete questions, numerical examples and Try notes; closes old help on navigation', () => {
  const material = {
    ...section,
    example: 'Model A: 90% accuracy and 4% error gap. Model B: 88% accuracy and 8% error gap.',
    question: 'Which model would you choose and why?',
  }
  renderApp(<GuidedSection section={material} course="course" paused={false} />)
  fireEvent.click(screen.getByRole('button', { name: 'Ask the tutor' }))
  expect(screen.getByLabelText('Tutor context')).toHaveTextContent(material.explanation)
  expect(screen.getByLabelText('Tutor context')).toHaveTextContent(material.example)
  fireEvent.click(screen.getByRole('button', { name: 'Try' }))
  expect(screen.queryByText('Contextual tutor')).toBeNull()
  fireEvent.change(screen.getByLabelText('Project notes'), {
    target: { value: 'I compared the two models.' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Ask the tutor' }))
  expect(screen.getByLabelText('Tutor context')).toHaveTextContent(material.task)
  expect(screen.getByLabelText('Tutor answer')).toHaveTextContent('I compared the two models.')
  fireEvent.click(screen.getByRole('button', { name: 'Think deeper' }))
  expect(screen.queryByText('Contextual tutor')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Ask the tutor' }))
  expect(screen.getByLabelText('Tutor context')).toHaveTextContent(material.question)
  expect(screen.getByLabelText('Tutor context')).toHaveTextContent(material.example)
  expect(screen.getByLabelText('Tutor context')).toHaveTextContent(material.criteria)
})

it('pairs the selected question with its answer check and spoken question, hint and criteria', () => {
  renderApp(<GuidedSection section={section} course="course" paused={false} />)
  fireEvent.click(screen.getByRole('button', { name: 'Think deeper' }))
  fireEvent.change(screen.getByLabelText('Question to explore'), { target: { value: 'challenge:tradeoff' } })
  fireEvent.change(screen.getByLabelText('Your explanation'), {
    target: { value: 'The estimate is uncertain.' },
  })
  expect(screen.getByLabelText('Answer check context')).toHaveTextContent(
    'What if the test set is too small?',
  )
  expect(screen.getByLabelText('Answer to check')).toHaveTextContent('The estimate is uncertain.')
  expect(screen.getByLabelText('Answer check context')).toHaveTextContent(section.example)
  const audio = screen.getByRole('button', { name: 'Listen to question' })
  expect(audio).toHaveTextContent('What if the test set is too small?')
  fireEvent.click(screen.getByRole('button', { name: 'One hint' }))
  fireEvent.click(screen.getByRole('button', { name: 'Show self-check checklist' }))
  expect(audio).toHaveTextContent('Think variance.')
  expect(audio).toHaveTextContent('Explain uncertainty.')
})
