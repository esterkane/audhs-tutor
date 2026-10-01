import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { renderApp, jsonResponse } from '../../test/utils'
import { AnswerFeedback } from './AnswerFeedback'
const initial = { verdict: null, note: '', hidden: false, revision: 0 }
beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())
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
