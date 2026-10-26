import { useState } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import type { Schemas } from '../../lib/api'
import { ResearchTutorPanel } from './ResearchTutorPanel'

afterEach(cleanup)
const onTutor = vi.fn()
function Harness({ draftOnly = false, checked = false, reference = false, hosted = false }: { draftOnly?: boolean; checked?: boolean; reference?: boolean; hosted?: boolean }) {
  const research: Schemas['KnowledgeResearch'] = { passage: 'Sort and average the middle values.', topic: 'median', current: 0, questions: [] }
  const original = { id: 'q1', prompt: 'How?', findings: 'My findings', evidence: 'My source', unresolved: '', section: 'Existing paragraph', tutor_request: 'Help with the middle values', tutor_basis: '' }
  const [question, setQuestion] = useState<Schemas['ResearchQuestion']>({ ...original,
    tutor_basis: JSON.stringify({ passage: research.passage, topic: research.topic, question: original.prompt,
      findings: original.findings, evidence: original.evidence, unresolved: original.unresolved, section: original.section }),
    tutor_exchanges: [{ action: 'draft', request: 'Help with the middle values', model_call_id: checked || reference ? null : 'call1', ...(reference ? { reference: 'python.string-identity.v1' as const } : {}), ...(checked ? { calculation: 'python.string-repetition.v1' as const } : {}), answer: {
      discussion: draftOnly ? '' : 'Average the two middle values.', needs_check: 'External links have not been checked.', next_question: '',
      source_quotes: ['Sort and average the middle values.'], section: 'Proposed paragraph.' } }],
  })
  return <><ResearchTutorPanel hosted={hosted} research={research} question={question} disabled={false} sourceChanged={false} onChange={setQuestion} onTutor={onTutor} />
    <output aria-label="my section">{question.section}</output>
    <button onClick={() => setQuestion({ ...question, findings: 'Changed findings' })}>Change findings</button></>
}

it('keeps the proposed section separate until explicit replacement, without falsely marking its adoption as changed research', async () => {
  const view = render(<Harness />)
  expect(screen.getByLabelText('my section')).toHaveTextContent('Existing paragraph')
  expect(screen.getByText('Needs checking')).toBeInTheDocument()
  fireEvent.click(screen.getByText('Replace my section with tutor draft'))
  expect(screen.getByLabelText('my section')).toHaveTextContent('Proposed paragraph.')
  expect(screen.queryByText(/The research text has changed/)).not.toBeInTheDocument()
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
  fireEvent.click(screen.getByText('Sources (1)'))
  expect(screen.getByText('Sort and average the middle values.')).toBeInTheDocument()
})

it('offers an explicit fresh alternative instead of silently forcing regeneration', () => {
  render(<Harness />)
  fireEvent.click(screen.getByText('Ask for another reply'))
  expect(onTutor).toHaveBeenLastCalledWith('draft-section', true)
})

it('treats saved calculation labels as unverified history while retaining the answer', async () => {
  const view = render(<Harness draftOnly checked />)
  expect(screen.getByText(/Saved Python calculation — provenance not verified/)).toBeVisible()
  expect(screen.queryByText(/no model was used/)).not.toBeInTheDocument()
  expect(screen.queryByText('Ask for another reply')).not.toBeInTheDocument()
  expect(screen.queryByText(/Saved AI suggestion/)).not.toBeInTheDocument()
  fireEvent.click(screen.getByText('Sources (1)'))
  expect(screen.getByText('Sort and average the middle values.')).toBeVisible()
  expect(screen.getByLabelText('my section')).toHaveTextContent('Existing paragraph')
  expect(await axe(view.container)).toHaveNoViolations()
})

it('labels a saved reference answer accurately and keeps the explicit draft handoff', async () => {
  const view = render(<Harness draftOnly reference />)
  expect(screen.getByText(/Saved reference-based reply — provenance not verified/)).toBeVisible()
  expect(screen.queryByText(/no model was used/)).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Python language reference' })).toHaveAttribute('href', expect.stringContaining('docs.python.org/3.12/'))
  expect(screen.queryByText('Ask for another reply')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Replace my section with tutor draft' }))
  expect(screen.getByLabelText('my section')).toHaveTextContent('Proposed paragraph.')
  expect(await axe(view.container)).toHaveNoViolations()
})


it('names the hosted tutor truthfully for assistive technology', () => {
  render(<Harness hosted />)
  expect(screen.getByRole('region', { name: 'Discuss and build with your OpenAI authoring tutor' })).toBeVisible()
  expect(screen.queryByRole('region', { name: /local/i })).not.toBeInTheDocument()
})


it('offers exact reuse at capacity while keeping new-generation actions disabled', () => {
  const question: Schemas['ResearchQuestion'] = { id: 'q', prompt: 'What does the source mean?', findings: 'My finding', evidence: 'Source', unresolved: '', section: '', tutor_request: '', tutor_basis: '', tutor_exchanges: [] }
  const research: Schemas['KnowledgeResearch'] = { passage: 'Source', topic: 'Topic', current: 0, questions: [question] }
  question.tutor_basis = JSON.stringify({ passage: 'Source', topic: 'Topic', question: question.prompt, findings: question.findings, evidence: 'Source', unresolved: '', section: '' })
  question.tutor_exchanges = Array.from({ length: 12 }, () => ({ action: 'discuss', request: '', model_call_id: 'model', cache_token: 'signed-on-server', answer: { discussion: 'Saved answer', needs_check: '', next_question: '', section: '', source_quotes: ['Source'] } }))
  const request = vi.fn()
  const props = { research, question, disabled: false, sourceChanged: false, onChange: vi.fn(), onTutor: request }
  const view = render(<ResearchTutorPanel {...props} />)
  expect(screen.getByRole('button', { name: 'Discuss my findings locally' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Ask for another reply' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Reuse saved reply' }))
  expect(request).toHaveBeenCalledExactlyOnceWith('discuss')
  const adopted = { ...question, section: 'Proposed paragraph.', tutor_exchanges: question.tutor_exchanges.map(x => ({ ...x, answer: { ...x.answer, section: 'Proposed paragraph.' } })) }
  view.rerender(<ResearchTutorPanel {...props} question={adopted} />)
  expect(screen.queryByRole('button', { name: 'Reuse saved reply' })).not.toBeInTheDocument()
  view.rerender(<ResearchTutorPanel {...props} question={{ ...question, findings: 'Changed finding' }} />)
  expect(screen.queryByRole('button', { name: 'Reuse saved reply' })).not.toBeInTheDocument()
})
