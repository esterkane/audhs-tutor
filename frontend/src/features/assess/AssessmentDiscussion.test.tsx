import { fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { renderApp } from '../../test/utils'
import { AssessmentDiscussion } from './AssessmentDiscussion'

const unmount = vi.fn()
vi.mock('../../lib/api', () => ({
  apiFetch: vi.fn(async () => ({
    id: 'saved',
    surface: 'assessment',
    request: { text: 'Original question', learner_answer_display: 'Original selection' },
  })),
}))
vi.mock('../programs/AnswerFollowup', async () => {
  const { useEffect } = await import('react')
  return {
    AnswerFollowup: ({
      answerId,
      expectedSessionId,
      active,
    }: {
      answerId: string
      expectedSessionId: string
      active: boolean
    }) => {
      useEffect(() => () => unmount(), [])
      return (
        <div data-active={String(active)}>
          Discussion {answerId} in {expectedSessionId}
        </div>
      )
    },
  }
})
it('opens explicitly with immutable parent and deactivates without discarding mounted reply state', async () => {
  const view = renderApp(<AssessmentDiscussion answerId="saved" sessionId="original" active />)
  expect(screen.queryByText('Discussion saved in original')).not.toBeInTheDocument()
  const details = screen.getByText('Discuss this feedback').closest('details')!
  details.open = true
  fireEvent(details, new Event('toggle'))
  expect(await screen.findByText('Discussion saved in original')).toBeVisible()
  expect(await screen.findByText('Original selection')).toBeVisible()
  view.rerender(<AssessmentDiscussion answerId="saved" sessionId="original" active={false} />)
  expect(screen.getByText('Discussion saved in original')).toHaveAttribute('data-active', 'false')
  expect(unmount).not.toHaveBeenCalled()
  view.rerender(<AssessmentDiscussion answerId="saved" sessionId="original" active />)
  expect(screen.getByText('Discussion saved in original')).toBeVisible()
  details.open = false
  fireEvent(details, new Event('toggle'))
  await waitFor(() =>
    expect(screen.getByText('Discussion saved in original')).toHaveAttribute('data-active', 'false'),
  )
  expect(unmount).not.toHaveBeenCalled()
})
it('does not fabricate a discussion parent when history was not saved', () => {
  renderApp(<AssessmentDiscussion answerId={null} sessionId="original" active />)
  expect(screen.queryByText('Discuss this feedback')).not.toBeInTheDocument()
})

it('does not present a raw option index as the recorded answer', async () => {
  const { apiFetch } = await import('../../lib/api')
  vi.mocked(apiFetch).mockResolvedValueOnce({ id: 'saved', surface: 'assessment', request: { text: 'Question', learner_answer: '0' } })
  renderApp(<AssessmentDiscussion answerId="saved" sessionId="original" active />)
  const details = screen.getByText('Discuss this feedback').closest('details')!
  details.open = true
  fireEvent(details, new Event('toggle'))
  expect(await screen.findByText(/displayed answer was not saved/)).toBeVisible()
  expect(screen.queryByText('0', { exact: true })).not.toBeInTheDocument()
})

it('loads only after opening and retries a failed read without sending tutor work', async () => {
  const { apiFetch } = await import('../../lib/api')
  vi.mocked(apiFetch).mockClear()
  vi.mocked(apiFetch).mockRejectedValueOnce(new Error('Offline'))
  renderApp(<AssessmentDiscussion answerId="saved" sessionId="original" active />)
  expect(apiFetch).not.toHaveBeenCalled()
  const details = screen.getByText('Discuss this feedback').closest('details')!
  details.open = true
  fireEvent(details, new Event('toggle'))
  fireEvent.click(await screen.findByRole('button', { name: 'Retry recorded answer' }))
  expect(await screen.findByText('Original selection')).toBeVisible()
  expect(vi.mocked(apiFetch).mock.calls.every(([url, init]) => url === '/api/answers/saved' && !init?.method)).toBe(true)
})
