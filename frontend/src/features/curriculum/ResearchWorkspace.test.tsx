import { fireEvent, render, screen, cleanup, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { ResearchWorkspace } from './ResearchWorkspace'
import { validResearch } from './researchRecovery'
import type { Schemas } from '../../lib/api'

afterEach(cleanup)
function Harness() {
  const [form, setForm] = useState<Schemas['KnowledgeMaterialInput']>({ title: 'Median', workflow_step: 'source', domain: 'ai_ml', objective: '', worked_example: '', question: '', criteria: [], notes: 'The median is the middle value of sorted data.', explanation: 'Existing paragraph.' })
  return <><ResearchWorkspace form={form} onChange={setForm} disabled={false} /><output aria-label="explanation">{form.explanation}</output><button onClick={() => setForm({ ...form, notes: 'Revised source' })}>Change source</button></>
}
it('prepares source-linked questions, retains separate findings and appends a reviewed section once', async () => {
  const view = render(<Harness />)
  fireEvent.change(screen.getByLabelText('Topic to investigate'), { target: { value: 'the median' } })
  fireEvent.click(screen.getByText('Use notes as passage'))
  fireEvent.click(screen.getByText('Prepare research questions'))
  expect((screen.getByLabelText('Research question') as HTMLTextAreaElement).value).toContain('the median')
  fireEvent.change(screen.getByLabelText('My findings'), { target: { value: 'Sort before finding the middle.' } })
  fireEvent.change(screen.getByLabelText('Evidence and references'), { target: { value: 'Source: “sorted data”' } })
  fireEvent.change(screen.getByLabelText('My knowledge section'), { target: { value: 'First sort the values.' } })
  fireEvent.click(screen.getByText('Next research question'))
  expect(screen.getByLabelText('My findings')).toHaveValue('')
  fireEvent.click(screen.getByText('Previous research question'))
  expect(screen.getByLabelText('My findings')).toHaveValue('Sort before finding the middle.')
  fireEvent.click(screen.getByText('Add section to explanation'))
  expect(screen.getByLabelText('explanation')).toHaveTextContent('Existing paragraph. First sort the values.')
  expect(screen.getByText('Add section to explanation')).toBeDisabled()
  fireEvent.click(screen.getByText('Change source'))
  expect(screen.getByRole('alert')).toHaveTextContent('keeps its original passage')
  expect(screen.getByLabelText('Evidence and references')).toHaveValue('Source: “sorted data”')
  expect(screen.getByRole('button', { name: 'Add section to explanation' })).toHaveAccessibleDescription(/exact passage/)
  fireEvent.click(screen.getByRole('button', { name: 'Restore linked passage in source notes' }))
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(screen.getByLabelText('My findings')).toHaveValue('Sort before finding the middle.')
  expect(await axe(view.container)).toHaveNoViolations()
})
it('rejects invalid recovery position and malformed questions', () => {
  expect(validResearch({ passage: 'x', topic: 'x', current: 3, questions: [{ id: '1', prompt: 'why?' }] })).toBe(false)
  expect(validResearch(null)).toBe(false)
})


it('collapses duplicate tutor prose after using a draft, preserves history and restores summary focus', async () => {
  const onTutor = vi.fn()
  function DraftHarness() {
    const q = { id: 'q1', prompt: 'Explain this source', findings: 'My finding', evidence: 'Source', unresolved: '', section: '', tutor_request: 'Draft', tutor_basis: '', tutor_exchanges: [{ action: 'draft' as const, request: 'Draft', model_call_id: 'c1', answer: { discussion: '', needs_check: '', next_question: '', section: 'One complete paragraph.', source_quotes: ['Source'] } }] }
    q.tutor_basis = JSON.stringify({ passage: 'Source', topic: 'topic', question: q.prompt, findings: q.findings, evidence: q.evidence, unresolved: '', section: '' })
    const [form, setForm] = useState<Schemas['KnowledgeMaterialInput']>({ title: 'Draft', workflow_step: 'write', domain: 'ai_ml', notes: 'Source', objective: '', explanation: '', worked_example: '', question: '', criteria: [], research: { passage: 'Source', topic: 'topic', current: 0, questions: [q] } })
    return <><ResearchWorkspace phase="write" form={form} disabled={false} onChange={setForm} onTutor={onTutor} /><output aria-label="saved replies">{form.research?.questions[0].tutor_exchanges?.length}</output></>
  }
  const view = render(<DraftHarness />)
  const summary = screen.getByText('Ask the local tutor (optional)').closest('summary')!
  const details = summary.closest('details')!
  fireEvent.click(summary)
  await waitFor(() => expect(details).toHaveAttribute('open'))
  fireEvent.click(screen.getByText('Use tutor draft in my section'))
  await waitFor(() => expect(details).not.toHaveAttribute('open'))
  expect(summary).toHaveFocus()
  expect(screen.getByLabelText('My knowledge section')).toHaveValue('One complete paragraph.')
  expect(screen.getByLabelText('saved replies')).toHaveTextContent('1')
  expect(onTutor).not.toHaveBeenCalled()
  expect(screen.queryByText(/The research text has changed/)).not.toBeInTheDocument()
  fireEvent.click(summary)
  await waitFor(() => expect(details).toHaveAttribute('open'))
  expect(within(screen.getByRole('region', { name: 'Discuss and build with your local tutor' })).getByText('One complete paragraph.')).toBeVisible()
  expect(await axe(view.container)).toHaveNoViolations()
})
