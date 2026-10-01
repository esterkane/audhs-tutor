import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { AnswerSourceStatus } from './AnswerSourceStatus'

afterEach(() => vi.unstubAllGlobals())
it('checks only on request and distinguishes matching text from newer versions', async () => {
  const fetcher = vi.fn(async () => jsonResponse({ sources: [
    { chunk_id: 'source-one', status: 'unchanged', newer_version: true },
    { chunk_id: 'source-two', status: 'missing', newer_version: false },
  ], omitted: 2 }))
  vi.stubGlobal('fetch', fetcher)
  renderApp(<AnswerSourceStatus answerId="saved" />)
  expect(fetcher).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Check saved source text' }))
  expect(await screen.findByText(/a newer local document version exists/)).toBeInTheDocument()
  expect(screen.getByText(/Source passage is no longer available/)).toBeInTheDocument()
  expect(screen.getByText(/2 additional references were not checked/)).toBeInTheDocument()
  expect(screen.getByText(/does not establish that the answer is correct/)).toBeInTheDocument()
})
it('does not claim verification for an answer without sources', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ sources: [], omitted: 0 })))
  renderApp(<AnswerSourceStatus answerId="empty" />)
  fireEvent.click(screen.getByRole('button', { name: 'Check saved source text' }))
  expect(await screen.findByText(/This answer has not been verified/)).toBeInTheDocument()
})
