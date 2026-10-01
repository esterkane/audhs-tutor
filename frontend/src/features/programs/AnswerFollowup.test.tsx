import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { AnswerFollowup } from './AnswerFollowup'
vi.mock('../session/api', () => ({ useCurrentSession: () => ({ data: { id: 'session' } }) }))
vi.mock('../../lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('../../lib/api')>()
  return {
    ...original,
    apiFetch: (url: string, init?: RequestInit) =>
      url.endsWith('/feedback')
        ? Promise.resolve({
            verdict: url.includes('/child/') ? 'incorrect' : null,
            note: '',
            hidden: false,
            revision: 0,
          })
        : original.apiFetch(url, init),
  }
})
vi.mock('../voice/ReadAloud', () => ({ ReadAloud: () => null }))
vi.mock('../voice/DictationButton', () => ({ DictationButton: () => null }))
beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())
it('sends explicitly, follows the newly saved parent and restores an unsent draft', async () => {
  const fetcher = vi.fn(async (url: string) =>
    jsonResponse({ text: `Reply from ${url}`, answer_id: 'child', source_note: 'Historical only' }),
  )
  vi.stubGlobal('fetch', fetcher)
  const view = renderApp(<AnswerFollowup answerId="parent" />)
  await waitFor(() => expect(screen.queryByText(/Checking feedback for/)).not.toBeInTheDocument())
  expect(fetcher).not.toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'Why?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await screen.findByRole('link', { name: 'Open saved follow-up' })
  expect(fetcher.mock.calls[0][0]).toBe('/api/answers/parent/followup')
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'An example?' } })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send follow-up' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await waitFor(() => expect(fetcher.mock.calls[1][0]).toBe('/api/answers/child/followup'))
  await waitFor(() => expect(screen.getByLabelText('Your follow-up question')).not.toBeDisabled())
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'Draft for later' } })
  view.unmount()
  renderApp(<AnswerFollowup answerId="parent" />)
  expect(screen.getByLabelText('Your follow-up question')).toHaveValue('Draft for later')
  expect(await screen.findByText(/reply you will continue from is marked incorrect/)).toBeVisible()
  expect(screen.getByRole('link', { name: 'latest saved follow-up' })).toHaveAttribute(
    'href',
    '/answers/child',
  )
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await waitFor(() => expect(fetcher.mock.calls[2][0]).toBe('/api/answers/child/followup'))
})
it('keeps the question after Stop and ignores a late response', async () => {
  let resolve!: (response: Response) => void
  vi.stubGlobal(
    'fetch',
    vi.fn(
      () =>
        new Promise<Response>((done) => {
          resolve = done
        }),
    ),
  )
  renderApp(<AnswerFollowup answerId="parent" />)
  await waitFor(() => expect(screen.queryByText(/Checking feedback for/)).not.toBeInTheDocument())
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'Explain' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
  await act(async () => resolve(jsonResponse({ text: 'Late response', answer_id: 'late' })))
  expect(screen.queryByText('Late response')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Your follow-up question')).toHaveValue('Explain')
  expect(screen.getByRole('alert')).toHaveTextContent('server may still finish')
})
it('retains a failed-save reply and pauses continuation rather than using the wrong parent', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      jsonResponse({ text: 'Keep this reply', answer_id: null, save_error: 'Storage unavailable' }),
    ),
  )
  renderApp(<AnswerFollowup answerId="parent" />)
  await waitFor(() => expect(screen.queryByText(/Checking feedback for/)).not.toBeInTheDocument())
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'Explain' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  expect(await screen.findByText('Keep this reply')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Send follow-up' })).toBeDisabled()
})

it('continues from a recovered saved reply without regenerating it', async () => {
  const fetcher = vi.fn(async (url: string) => url === '/api/answers/recover-save'
    ? jsonResponse({ answer_id: 'recovered' })
    : jsonResponse({ turn_id: 'reply-turn', text: 'Retained reply', save_error: 'Save failed', save_receipt: 'receipt' }))
  vi.stubGlobal('fetch', fetcher)
  renderApp(<AnswerFollowup answerId="parent" />)
  await waitFor(() => expect(screen.queryByText(/Checking feedback for/)).not.toBeInTheDocument())
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'Why?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await screen.findByRole('button', { name: 'Retry saving' })
  expect(screen.getByRole('button', { name: 'Send follow-up' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Retry saving' }))
  await screen.findByRole('link', { name: 'Open saved follow-up' })
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'An example?' } })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send follow-up' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await waitFor(() => expect(fetcher.mock.calls[2][0]).toBe('/api/answers/recovered/followup'))
  expect(fetcher.mock.calls[1][0]).toBe('/api/answers/recover-save')
})
