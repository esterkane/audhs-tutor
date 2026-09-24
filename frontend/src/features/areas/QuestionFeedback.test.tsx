import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { FeedbackPreferences, QuestionFeedback } from './QuestionFeedback'

afterEach(() => vi.unstubAllGlobals())
it('requires an intentional reason, saves the versioned target and supports undo', async () => {
  const writes: Array<{ method: string; body: unknown }> = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_url: string, init?: RequestInit) => {
      if (init?.method)
        writes.push({ method: init.method, body: init.body ? JSON.parse(String(init.body)) : null })
      return jsonResponse(
        init?.method === 'POST'
          ? { id: 'feedback-1' }
          : { feedback: [], label_counts: {}, suggestions: [], preferences: {} },
      )
    }),
  )
  renderApp(<QuestionFeedback target={{ draft_id: 'draft-1', draft_version: 3, question_index: 2 }} />)
  fireEvent.click(screen.getByText('Rate this question'))
  expect(screen.getByRole('button', { name: 'Save question feedback' })).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Quality'), { target: { value: 'bad' } })
  fireEvent.change(screen.getByLabelText('Why?'), { target: { value: 'too_vague' } })
  fireEvent.change(screen.getByLabelText('Your explanation (optional)'), {
    target: { value: 'Ask me to debug an example.' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Save question feedback' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Undo rating' }))
  await waitFor(() => expect(writes).toHaveLength(2))
  expect(writes[0].body).toEqual({
    draft_id: 'draft-1',
    draft_version: 3,
    question_index: 2,
    verdict: 'bad',
    labels: ['too_vague'],
    note: 'Ask me to debug an example.',
  })
  expect(writes[1].method).toBe('DELETE')
})
it('does not apply suggested adaptations until selected, and allows reversing them', async () => {
  const writes: unknown[] = []
  let enabled = false
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_url: string, init?: RequestInit) => {
      if (init?.method === 'PUT') {
        const body = JSON.parse(String(init.body))
        writes.push(body)
        enabled = body.enabled
      }
      return jsonResponse({
        feedback: [],
        label_counts: { too_vague: 1 },
        preferences: { 'questions.applied': enabled },
        suggestions: enabled
          ? []
          : [
              {
                key: 'questions.applied',
                description: 'Use concrete applications',
                reason: 'Suggested from your rating',
              },
            ],
      })
    }),
  )
  renderApp(<FeedbackPreferences />)
  fireEvent.click(screen.getByText('Your feedback and question preferences'))
  const apply = await screen.findByRole('button', { name: 'Apply this preference' })
  expect(writes).toEqual([])
  fireEvent.click(apply)
  const checkbox = screen.getByRole('checkbox', { name: 'More concrete application and debugging questions' })
  await waitFor(() => expect(checkbox).toBeChecked())
  fireEvent.click(checkbox)
  await waitFor(() => expect(checkbox).not.toBeChecked())
  expect(writes).toEqual([
    { key: 'questions.applied', enabled: true },
    { key: 'questions.applied', enabled: false },
  ])
})
