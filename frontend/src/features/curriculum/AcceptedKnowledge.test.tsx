import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp, jsonResponse } from '../../test/utils'
import { AcceptedKnowledge, OptionalKnowledgeTutor } from './AcceptedKnowledge'
import { useAcceptedKnowledge } from './acceptedKnowledgeApi'
import { axe } from 'vitest-axe'
const onCheck = vi.fn()
function Harness() {
  const reading = useAcceptedKnowledge('skill')
  return <main><h1>Learning session</h1><AcceptedKnowledge reading={reading} onCheck={onCheck} />
    <OptionalKnowledgeTutor authored={!!reading.data}><p>Unverified generated help</p></OptionalKnowledgeTutor></main>
}
afterEach(() => { vi.unstubAllGlobals(); onCheck.mockReset() })
it('shows the accepted text verbatim without generating and keeps optional AI help separate', async () => {
  const fetcher = vi.fn(async () => jsonResponse({ draft_id:'d1', title:'My material', objective:'Fit training only',
    explanation:'Split before fitting. Fit only training values.', worked_example:'Training median is reused.',
    question:'Which values fit the parameter?', notes:'My saved note', sources:[], learning_object_version:2 }))
  vi.stubGlobal('fetch',fetcher)
  const view = renderApp(<Harness />)
  expect(await screen.findByText('Split before fitting. Fit only training values.')).toBeVisible()
  expect(screen.getByText('Unverified generated help')).not.toBeVisible()
  fireEvent.click(screen.getByRole('button',{name:'Try this lesson'}))
  expect(onCheck).toHaveBeenCalledTimes(1)
  expect(fetcher).toHaveBeenCalledTimes(1)
  expect(await axe(view.container)).toHaveNoViolations()
})
it('exposes a read failure without substituting generated material', async () => {
  vi.stubGlobal('fetch',vi.fn(async () => { throw new Error('Connection lost') }))
  renderApp(<Harness />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load your accepted knowledge material')
  expect(screen.getByRole('button',{name:'Retry accepted material'})).toBeEnabled()
})
