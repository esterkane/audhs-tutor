import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { renderApp, jsonResponse } from '../../test/utils'
import { AnswerFeedback } from './AnswerFeedback'
const initial = { verdict: null, note: '', hidden: false, revision: 0 }
beforeEach(() => localStorage.clear())
afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})
it('saves explicitly and displays the saved warning without changing the answer', async () => {
  const fetcher = vi.fn(async (_url: string, init?: RequestInit) =>
    jsonResponse(init?.method === 'PUT' ? { ...JSON.parse(String(init.body)), revision: 1 } : initial),
  )
  vi.stubGlobal('fetch', fetcher)
  renderApp(<AnswerFeedback answerId="a" />)
  fireEvent.change(await screen.findByLabelText('How was this answer?'), { target: { value: 'incorrect' } })
  fireEvent.change(screen.getByLabelText('Why? (optional)'), { target: { value: 'Wrong totals' } })
  expect(fetcher).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }))
  expect(await screen.findByText('Feedback saved.')).toBeVisible()
  expect(screen.getByRole('alert')).toHaveTextContent('marked this answer incorrect')
})
it('keeps conflicting edits, shows latest saved state, and retries with its revision', async () => {
  let current = initial
  const writes: unknown[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_url: string, init?: RequestInit) => {
      if (init?.method !== 'PUT') return jsonResponse(current)
      const body = JSON.parse(String(init.body))
      writes.push(body)
      if (body.revision === 0)
        return jsonResponse({ error: { code: 'feedback_conflict', message: 'Conflict' } }, 409)
      return jsonResponse({ ...body, revision: 3 })
    }),
  )
  renderApp(<AnswerFeedback answerId="a" />)
  fireEvent.change(await screen.findByLabelText('Why? (optional)'), { target: { value: 'My reason' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }))
  expect(await screen.findByText(/Feedback changed in another tab/)).toBeVisible()
  current = { ...initial, note: 'Other tab reason', revision: 2 }
  fireEvent.click(screen.getByRole('button', { name: 'Review latest saved feedback' }))
  expect(await screen.findByRole('status')).toHaveTextContent('Other tab reason')
  expect(screen.getByLabelText('Why? (optional)')).toHaveValue('My reason')
  fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }))
  await waitFor(() => expect(writes[1]).toMatchObject({ note: 'My reason', revision: 2 }))
})
for (const action of ['save', 'load'] as const) {
  it(`times out ${action}, keeps edits and ignores late results`, async () => {
    let finish!: (response: Response) => void
    let calls = 0
    let signal: AbortSignal | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) => {
        if (++calls === 1) return Promise.resolve(jsonResponse(initial))
        signal = init?.signal as AbortSignal
        return new Promise<Response>((resolve) => {
          finish = resolve
        })
      }),
    )
    renderApp(<AnswerFeedback answerId="a" />)
    const input = await screen.findByLabelText('Why? (optional)')
    fireEvent.change(input, { target: { value: 'Keep draft' } })
    vi.useFakeTimers()
    fireEvent.click(
      screen.getByRole('button', {
        name: action === 'save' ? 'Save feedback' : 'Review latest saved feedback',
      }),
    )
    expect(input).toBeDisabled()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15000)
    })
    expect(signal?.aborted).toBe(true)
    expect(input).toBeEnabled()
    expect(input).toHaveValue('Keep draft')
    expect(screen.getByRole('alert')).toHaveTextContent('timed out')
    if (action === 'save') expect(screen.getByRole('alert')).toHaveTextContent('may have completed')
    fireEvent.change(input, { target: { value: 'Newer edit' } })
    await act(async () => {
      finish(jsonResponse({ ...initial, note: 'Late', revision: 8 }))
    })
    expect(input).toHaveValue('Newer edit')
    expect(screen.queryByText('Feedback saved.')).not.toBeInTheDocument()
    expect(JSON.parse(localStorage.getItem('answer-feedback-draft:v1:a')!).note).toBe('Newer edit')
  })
}
it('aborts on unmount and retains the draft after late completion', async () => {
  let finish!: (response: Response) => void
  let signal: AbortSignal | undefined
  vi.stubGlobal(
    'fetch',
    vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method !== 'PUT') return Promise.resolve(jsonResponse(initial))
      signal = init.signal as AbortSignal
      return new Promise<Response>((resolve) => {
        finish = resolve
      })
    }),
  )
  const view = renderApp(<AnswerFeedback answerId="a" />)
  fireEvent.change(await screen.findByLabelText('Why? (optional)'), { target: { value: 'Keep me' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }))
  view.unmount()
  expect(signal?.aborted).toBe(true)
  await act(async () => {
    finish(jsonResponse({ ...initial, revision: 1 }))
  })
  expect(JSON.parse(localStorage.getItem('answer-feedback-draft:v1:a')!).note).toBe('Keep me')
})
