import { useState } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import type { Schemas } from '../../lib/api'
import { ResearchTutorPanel } from './ResearchTutorPanel'

afterEach(cleanup)
const onTutor = vi.fn()
function Harness({ draftOnly = false, checked = false }: { draftOnly?: boolean; checked?: boolean }) {
  const research: Schemas['KnowledgeResearch'] = { passage: 'Sort and average the middle values.', topic: 'median', current: 0, questions: [] }
  const original = { id: 'q1', prompt: 'How?', findings: 'My findings', evidence: 'My source', unresolved: '', section: 'Existing paragraph', tutor_request: 'Help with the middle values', tutor_basis: '' }
  const [question, setQuestion] = useState<Schemas['ResearchQuestion']>({ ...original,
    tutor_basis: JSON.stringify({ passage: research.passage, topic: research.topic, question: original.prompt,
      findings: original.findings, evidence: original.evidence, unresolved: original.unresolved, section: original.section }),
    tutor_exchanges: [{ action: 'draft', request: 'Help with the middle values', model_call_id: checked ? null : 'call1', ...(checked ? { calculation: 'python.string-repetition.v1' as const } : {}), answer: {
      discussion: draftOnly ? '' : 'Average the two middle values.', needs_check: 'External links have not been checked.', next_question: '',
      source_quotes: ['Sort and average the middle values.'], section: 'Proposed paragraph.' } }],
  })
  return <><ResearchTutorPanel research={research} question={question} disabled={false} sourceChanged={false} onChange={setQuestion} onTutor={onTutor} />
    <output aria-label="my section">{question.section}</output>
    <button onClick={() => setQuestion({ ...question, findings: 'Changed findings' })}>Change findings</button></>
}

it('keeps the proposed section separate until explicit replacement, then marks it as earlier context', async () => {
  const view = render(<Harness />)
  expect(screen.getByLabelText('my section')).toHaveTextContent('Existing paragraph')
  expect(screen.getByText('Needs checking')).toBeInTheDocument()
  fireEvent.click(screen.getByText('Replace my section with tutor draft'))
  expect(screen.getByLabelText('my section')).toHaveTextContent('Proposed paragraph.')
  expect(screen.getByText(/The research text has changed/)).toBeInTheDocument()
  expect(screen.getByText('Replace my section with tutor draft')).toBeDisabled()
  expect(await axe(view.container)).toHaveNoViolations()
})

it('refuses to apply an old draft after findings change but allows asking again', () => {
  render(<Harness />)
  fireEvent.click(screen.getByText('Change findings'))
  expect(screen.getByText('Replace my section with tutor draft')).toBeDisabled()
  expect(screen.getByText('Discuss my findings locally')).toBeEnabled()
  fireEvent.click(screen.getByText('Discuss my findings locally'))
  expect(onTutor).toHaveBeenCalledWith('discuss')
})

it('renders a section-only proposal without a second explanatory paragraph', () => {
  render(<Harness draftOnly />)
  expect(screen.queryByText('Average the two middle values.')).not.toBeInTheDocument()
  expect(screen.getByText('Proposed paragraph.')).toBeInTheDocument()
  expect(screen.getByText('Needs checking')).toBeInTheDocument()
  expect(screen.getByText('Replace my section with tutor draft')).toBeEnabled()
  fireEvent.click(screen.getByText('Source evidence'))
  expect(screen.getByText('Sort and average the middle values.')).toBeInTheDocument()
})

it('offers an explicit fresh alternative instead of silently forcing regeneration', () => {
  render(<Harness />)
  fireEvent.click(screen.getByText('Ask for another reply'))
  expect(onTutor).toHaveBeenLastCalledWith('draft-section', true)
})

it('identifies checked calculations without pretending a model ran or offering duplicate alternatives', async () => {
  const view = render(<Harness draftOnly checked />)
  expect(screen.getByText(/Checked Python calculation; no model was used/)).toBeVisible()
  expect(screen.queryByText('Ask for another reply')).not.toBeInTheDocument()
  expect(screen.queryByText(/Saved AI suggestion/)).not.toBeInTheDocument()
  fireEvent.click(screen.getByText('Calculation input'))
  expect(screen.getByText('Sort and average the middle values.')).toBeVisible()
  expect(screen.getByLabelText('my section')).toHaveTextContent('Existing paragraph')
  expect(await axe(view.container)).toHaveNoViolations()
})
