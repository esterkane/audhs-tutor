import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { AnswerFollowup } from './AnswerFollowup'

function completedReply(reply: Record<string, unknown>) {
  return new Response(`event: done\ndata: ${JSON.stringify({ turn_id: 'turn', ...reply })}\n\n`, {
    headers: { 'Content-Type': 'text/event-stream' },
  })
}

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
vi.mock('../voice/ReadAloud', () => ({ ReadAloud: () => <span>Reading control mounted</span> }))
vi.mock('../voice/DictationButton', () => ({ DictationButton: () => <span>Dictation control mounted</span> }))
beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
})
afterEach(() => vi.unstubAllGlobals())
it('sends explicitly, follows the newly saved parent and restores an unsent draft', async () => {
  const fetcher = vi.fn(async (url: string) =>
    completedReply({ text: `Reply from ${url}`, answer_id: 'child', source_note: 'Historical only' }),
  )
  vi.stubGlobal('fetch', fetcher)
  const view = renderApp(<AnswerFollowup answerId="parent" />)
  await waitFor(() => expect(screen.queryByText(/Checking feedback for/)).not.toBeInTheDocument())
  expect(fetcher).not.toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'Why?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await screen.findByRole('link', { name: 'Open saved follow-up' })
  expect(fetcher.mock.calls[0][0]).toBe('/api/answers/parent/followup/stream')
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'An example?' } })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send follow-up' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await waitFor(() => expect(fetcher.mock.calls[1][0]).toBe('/api/answers/child/followup/stream'))
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
  await waitFor(() => expect(fetcher.mock.calls[2][0]).toBe('/api/answers/child/followup/stream'))
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
  await act(async () => resolve(completedReply({ text: 'Late response', answer_id: 'late' })))
  expect(screen.queryByText('Late response')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Your follow-up question')).toHaveValue('Explain')
  expect(screen.getByRole('alert')).toHaveTextContent('server may still finish')
})
it('retains a failed-save reply and pauses continuation rather than using the wrong parent', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      completedReply({ text: 'Keep this reply', answer_id: null, save_error: 'Storage unavailable' }),
    ),
  )
  const view = renderApp(<AnswerFollowup answerId="parent" />)
  await waitFor(() => expect(screen.queryByText(/Checking feedback for/)).not.toBeInTheDocument())
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'Explain' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  expect(await screen.findByText('Keep this reply')).toBeVisible()
  expect(screen.getByText('Reading control mounted')).toBeInTheDocument()
  view.rerender(<AnswerFollowup answerId="parent" active={false} />)
  expect(screen.queryByText('Reading control mounted')).not.toBeInTheDocument()
  expect(screen.queryByText('Dictation control mounted')).not.toBeInTheDocument()
  view.rerender(<AnswerFollowup answerId="parent" active />)
  expect(screen.getByText('Keep this reply')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Send follow-up' })).toBeDisabled()
})

it('continues from a recovered saved reply without regenerating it', async () => {
  const fetcher = vi.fn(async (url: string) =>
    url === '/api/answers/recover-save'
      ? jsonResponse({ answer_id: 'recovered' })
      : completedReply({
          turn_id: 'reply-turn',
          text: 'Retained reply',
          save_error: 'Save failed',
          save_receipt: 'receipt',
        }),
  )
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
  await waitFor(() => expect(fetcher.mock.calls[2][0]).toBe('/api/answers/recovered/followup/stream'))
  expect(fetcher.mock.calls[1][0]).toBe('/api/answers/recover-save')
})

it('retries the original parent and question after reload while preserving a new draft', async () => {
  const fetcher = vi
    .fn()
    .mockRejectedValueOnce(new Error('Lost response'))
    .mockResolvedValue(completedReply({ text: 'Recovered reply', answer_id: 'child', turn_id: 'turn' }))
  vi.stubGlobal('fetch', fetcher)
  const first = renderApp(<AnswerFollowup answerId="parent" />)
  fireEvent.change(screen.getByLabelText('Your follow-up question'), {
    target: { value: 'Original question' },
  })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send follow-up' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await screen.findByText(/Lost response/)
  const original = fetcher.mock.calls[0]
  first.unmount()
  renderApp(<AnswerFollowup answerId="parent" />)
  fireEvent.change(screen.getByLabelText('Your follow-up question'), {
    target: { value: 'My next question' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Retry previous request' }))
  await screen.findByText('Recovered reply')
  expect(fetcher.mock.calls[1][0]).toBe(original[0])
  expect(fetcher.mock.calls[1][1].body).toBe(original[1].body)
  expect(fetcher.mock.calls[1][1].headers['Idempotency-Key']).toBe(original[1].headers['Idempotency-Key'])
  expect(screen.getByLabelText('Your follow-up question')).toHaveValue('My next question')
  expect(screen.getByRole('link', { name: 'latest saved follow-up' })).toHaveAttribute(
    'href',
    '/answers/child',
  )
})

it('prepares a correction without sending, preserves drafts and persists its purpose across reload', async () => {
  const fetcher = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(async () =>
    completedReply({ text: 'Proposed revised reasoning', answer_id: 'child' }),
  )
  vi.stubGlobal('fetch', fetcher)
  const view = renderApp(<AnswerFollowup answerId="parent" />)
  await waitFor(() => expect(screen.queryByText(/Checking feedback for/)).not.toBeInTheDocument())
  fireEvent.change(screen.getByLabelText('Your follow-up question'), {
    target: { value: 'My specific objection' },
  })
  expect(screen.getByRole('button', { name: 'Prepare correction request' })).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Request type'), { target: { value: 'correction' } })
  expect(screen.getByLabelText('Your follow-up question')).toHaveValue('My specific objection')
  expect(fetcher).not.toHaveBeenCalled()
  view.unmount()
  renderApp(<AnswerFollowup answerId="parent" />)
  expect(screen.getByLabelText('Request type')).toHaveValue('correction')
  expect(screen.getByLabelText('Your follow-up question')).toHaveValue('My specific objection')
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send follow-up' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  expect(await screen.findByText('Proposed correction — review before relying on it')).toBeVisible()
  expect(JSON.parse(String(fetcher.mock.calls[0][1]?.body))).toMatchObject({
    purpose: 'correction',
    question: 'My specific objection',
  })
  expect(screen.getByLabelText('Request type')).toHaveValue('followup')
})

it('shows unfinished text before completion and retains it after Stop and reload', async () => {
  let stream!: ReadableStreamDefaultController<Uint8Array>
  const fetcher = vi.fn(
    async () =>
      new Response(
        new ReadableStream({
          start(c) {
            stream = c
          },
        }),
      ),
  )
  vi.stubGlobal('fetch', fetcher)
  const view = renderApp(<AnswerFollowup answerId="parent" />)
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'Why this step?' } })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send follow-up' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await act(async () =>
    stream.enqueue(new TextEncoder().encode('event: token\ndata: {"text":"First compare the groups."}\n\n')),
  )
  expect(await screen.findByRole('region', { name: 'Unfinished follow-up' })).toHaveTextContent(
    'First compare the groups.',
  )
  expect(screen.queryByRole('link', { name: 'Open saved follow-up' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
  await act(async () =>
    stream.enqueue(
      new TextEncoder().encode(
        'event: done\ndata: {"text":"Late final", "turn_id":"late", "answer_id":"late"}\n\n',
      ),
    ),
  )
  expect(screen.queryByText('Late final')).not.toBeInTheDocument()
  view.unmount()
  renderApp(<AnswerFollowup answerId="parent" />)
  expect(screen.getByRole('region', { name: 'Unfinished follow-up' })).toHaveTextContent(
    'First compare the groups.',
  )
  expect(screen.getByLabelText('Your follow-up question')).toHaveValue('Why this step?')
  expect(fetcher).toHaveBeenCalledTimes(1)
})

it('keeps interrupted previews separate from a recovered final answer and makes no automatic retry', async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(new Response('event: token\ndata: {"text":"Unfinished first thought"}\n\n'))
    .mockResolvedValueOnce(completedReply({ text: 'Authoritative final answer', answer_id: 'child' }))
  vi.stubGlobal('fetch', fetcher)
  renderApp(<AnswerFollowup answerId="parent" />)
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'Why?' } })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send follow-up' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await screen.findByText(/ended before completion/)
  expect(fetcher).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('region', { name: 'Unfinished follow-up' })).toHaveTextContent(
    'Unfinished first thought',
  )
  fireEvent.click(screen.getByRole('button', { name: 'Retry previous request' }))
  expect(await screen.findByText('Authoritative final answer')).toBeVisible()
  expect(screen.queryByRole('region', { name: 'Unfinished follow-up' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByText('Earlier unfinished follow-ups · questions may have changed'))
  expect(screen.getByText('Unfinished first thought')).toBeInTheDocument()
  expect(fetcher.mock.calls[1][1].body).toBe(fetcher.mock.calls[0][1].body)
  expect(fetcher.mock.calls[1][1].headers['Idempotency-Key']).toBe(
    fetcher.mock.calls[0][1].headers['Idempotency-Key'],
  )
})

it('retains visible partial text and reports preview storage denial', async () => {
  const original = Storage.prototype.setItem
  const storage = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (
    this: Storage,
    key,
    value,
  ) {
    if (key.includes('answer-followup-preview:')) throw new Error('Quota')
    return original.call(this, key, value)
  })
  try {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('event: token\ndata: {"text":"Keep this partial"}\n\n')),
    )
    renderApp(<AnswerFollowup answerId="parent" />)
    fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'Explain' } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Send follow-up' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
    await screen.findByText(/ended before completion/)
    expect(screen.getByRole('region', { name: 'Unfinished follow-up' })).toHaveTextContent(
      'Keep this partial',
    )
    expect(screen.getByText(/Unfinished text could not be saved/)).toBeVisible()
  } finally {
    storage.mockRestore()
  }
})

it('does not attach an assessment discussion to a different current session', () => {
  const fetcher = vi.fn()
  vi.stubGlobal('fetch', fetcher)
  renderApp(<AnswerFollowup answerId="parent" expectedSessionId="original-session" />)
  expect(screen.getByText(/no longer the current session/)).toBeVisible()
  expect(screen.queryByLabelText('Your follow-up question')).not.toBeInTheDocument()
  expect(fetcher).not.toHaveBeenCalled()
})

it('stops on deactivation and ignores a late completed reply', async () => {
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
  const view = renderApp(<AnswerFollowup answerId="parent" active />)
  await waitFor(() => expect(screen.queryByText(/Checking feedback for/)).not.toBeInTheDocument())
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'Explain' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  view.rerender(<AnswerFollowup answerId="parent" active={false} />)
  await act(async () => resolve(completedReply({ text: 'Late response', answer_id: 'late' })))
  view.rerender(<AnswerFollowup answerId="parent" active />)
  expect(screen.queryByText('Late response')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Your follow-up question')).toHaveValue('Explain')
  expect(screen.getByRole('alert')).toHaveTextContent('Stopped waiting')
})

it('retains the original retry identity across reload after a completed reply fails to save', async () => {
  const fetcher = vi.fn(async (url: string) =>
    url.endsWith('/recover-save')
      ? jsonResponse({ answer_id: 'recovered' })
      : completedReply({
          text: 'Completed but unsaved',
          answer_id: null,
          save_error: 'Save unavailable',
          save_receipt: 'receipt',
        }),
  )
  vi.stubGlobal('fetch', fetcher)
  const view = renderApp(<AnswerFollowup answerId="parent" />)
  await waitFor(() => expect(screen.queryByText(/Checking feedback for/)).not.toBeInTheDocument())
  fireEvent.change(screen.getByLabelText('Your follow-up question'), { target: { value: 'Why?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await screen.findByText('Completed but unsaved')
  const identity = (fetcher.mock.calls[0] as unknown as [string, RequestInit])[1].headers
  expect(screen.queryByRole('button', { name: 'Discard retry and start new' })).not.toBeInTheDocument()
  view.unmount()
  renderApp(<AnswerFollowup answerId="parent" />)
  fireEvent.click(await screen.findByRole('button', { name: 'Retry previous request' }))
  await screen.findByText('Completed but unsaved')
  expect((fetcher.mock.calls[1] as unknown as [string, RequestInit])[1].headers).toEqual(identity)
  expect(screen.getByRole('button', { name: 'Send follow-up' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Retry saving' }))
  await screen.findByRole('link', { name: 'Open saved follow-up' })
  expect(sessionStorage.getItem('tutor-request:v1:saved-answer-followup:v1:parent:session')).toBeNull()
})
