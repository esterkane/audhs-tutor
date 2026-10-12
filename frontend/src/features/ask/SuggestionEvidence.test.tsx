import { screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { renderApp } from '../../test/utils'
import type { Schemas } from '../../lib/api'
import { SuggestionEvidence } from './SuggestionEvidence'

const answer: Schemas['AnswerSummary'] = {
  id: 'a', turn_id: 't', session_id: null, surface: 'ask', created_at: '2026-10-12T10:00:00Z',
  request_text: 'Example', preview: 'Example', skill_id: null, area_id: null, context_dependent: false,
}
it('distinguishes a missing status from unchanged text without certifying accuracy', () => {
  const view = renderApp(<SuggestionEvidence answer={answer} matching />)
  expect(screen.getByText(/Source status unavailable/)).toHaveTextContent('Not fact-checked')
  view.rerender(<SuggestionEvidence answer={{ ...answer, source_check: { sources: [{ chunk_id: 'c', status: 'unchanged', newer_version: false }], omitted: 0 } }} matching />)
  expect(screen.getByText(/Recorded source text unchanged locally/)).toHaveTextContent('Not fact-checked')
})
it('flags newer versions and historical context even when the direct text is unchanged', () => {
  renderApp(<SuggestionEvidence answer={{ ...answer, context_dependent: true, source_check: { sources: [{ chunk_id: 'c', status: 'unchanged', newer_version: true }], omitted: 0 } }} matching={false} />)
  expect(screen.getByText(/Source review needed/)).toBeInTheDocument()
  expect(screen.getByText(/Uses earlier conversation/)).toBeInTheDocument()
  expect(screen.getByText(/Recent saved question/)).toHaveTextContent('Saved')
})
